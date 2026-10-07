import math
from pathlib import Path
import numpy as np
import pytest
import torch
from torch import nn
from sem_update.flows import Mechanism,GenerativeSCM,balanced_nll
from sem_update.graphs import DAG,structural_metrics,corrupt
from sem_update.data import Environment,prepare_synthetic,load_learner,validate_splits
from sem_update.training import fit_node,cache_key,DEFAULT_TRAIN
from sem_update.runtime import Ledger,digest
from sem_update.search import audit_pass,DEFAULT_SEARCH

@pytest.fixture(autouse=True)
def artifact_directory(tmp_path,monkeypatch):
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    torch.set_num_threads(2)

@pytest.mark.parametrize('parents',[(),(0,2)])
def test_spline_inverse_jacobian_boundaries(parents):
    torch.manual_seed(18)
    m=Mechanism(parents).double()
    with torch.no_grad():
        for p in m.parameters():
            p.add_(torch.randn_like(p)*.15)
    u=torch.tensor([-9.,-5.,-4.999,-2.3,-.1,0.,1.7,4.999,5.,9.],dtype=torch.float64,requires_grad=True)
    x=torch.randn(len(u),4,dtype=torch.float64)
    y,ld=m.forward_noise(u,x)
    inverse,ild=m.inverse_noise(y,x)
    derivative=torch.autograd.grad(y.sum(),u)[0]
    assert torch.all(derivative>0)
    torch.testing.assert_close(inverse,u,rtol=1e-7,atol=1e-7)
    torch.testing.assert_close(ld,derivative.log(),rtol=1e-7,atol=1e-7)
    torch.testing.assert_close(ld+ild,torch.zeros_like(ld),rtol=1e-7,atol=1e-7)

def test_nonparents_have_exactly_zero_influence():
    m=Mechanism((1,)).double()
    with torch.no_grad():
        m.conditioner[-1].weight.normal_(0,.05)
    x=torch.randn(11,4,dtype=torch.float64,requires_grad=True)
    y=m.forward_noise(torch.randn(11,dtype=torch.float64),x)[0]
    gradient=torch.autograd.grad(y.sum(),x)[0]
    assert torch.equal(gradient[:,[0,2,3]],torch.zeros(11,3,dtype=torch.float64))
    assert gradient[:,1].abs().sum()>0

class Linear(nn.Module):
    def __init__(self,parents,weights,scale=1.):
        super().__init__()
        self.parents=parents
        self.weights=nn.Parameter(torch.tensor(weights,dtype=torch.float64))
        self.scale=scale
    def forward_noise(self,u,x):
        mean=x[:,self.parents]@self.weights if self.parents else torch.zeros_like(u)
        return mean+self.scale*u,torch.ones_like(u)*math.log(self.scale)
    def inverse_noise(self,y,x):
        mean=x[:,self.parents]@self.weights if self.parents else torch.zeros_like(y)
        return (y-mean)/self.scale,torch.ones_like(y)*-math.log(self.scale)
    def log_probability(self,y,x):
        u,ld=self.inverse_noise(y,x)
        return -.5*(u*u+math.log(2*math.pi))+ld

def toy():
    return GenerativeSCM(DAG(4,((0,1),(1,2))),[Linear((),[]),Linear((0,),[2.]),Linear((1,),[3.]),Linear((),[])])

def test_perfect_intervention_covariance_nondescendants_and_stochastic_target():
    torch.manual_seed(98)
    u=torch.randn(100000,4,dtype=torch.float64)
    scm=toy()
    obs=scm.sample_observational(u)
    do=scm.sample_intervention(u,{1:1.5})
    torch.testing.assert_close(do[:,[0,3]],obs[:,[0,3]])
    assert torch.all(do[:,1]==1.5)
    assert abs(do[:,2].mean().item()-4.5)<.02
    torch.testing.assert_close(torch.cov(do[:,[0,2,3]].T),torch.eye(3,dtype=torch.float64),atol=.02,rtol=.02)
    assigned=torch.randn(len(u),dtype=torch.float64)
    stochastic=scm.sample_intervention(u,{1:assigned})
    assert abs(torch.corrcoef(stochastic[:,:2].T)[0,1])<.02
    assert abs(torch.cov(obs[:,:2].T)[0,1])>1.9

def test_target_has_no_likelihood_or_gradient_contribution():
    scm=toy()
    x=torch.randn(100,4,dtype=torch.float64)
    nll=-scm.log_probability(x,targets=(1,)).mean()
    nll.backward()
    assert scm.mechanisms[1].weights.grad is None
    assert scm.mechanisms[2].weights.grad is not None

def test_environment_and_node_balance():
    scm=toy()
    obs=Environment('obs',torch.zeros(200,4,dtype=torch.float64),{},tuple(range(200)))
    intervention=Environment('do',torch.ones(2,4,dtype=torch.float64),{1:{'kind':'fixed','value':1.}},(201,202))
    explicit=[]
    for j,m in enumerate(scm.mechanisms):
        a=-m.log_probability(obs.x[:,j],obs.x).mean()
        if j!=1:
            a=(a-m.log_probability(intervention.x[:,j],intervention.x).mean())/2
        explicit.append(a)
    torch.testing.assert_close(balanced_nll(scm,[obs,intervention]),torch.stack(explicit).mean())

def test_counterfactual_reuses_noise():
    scm=toy()
    u=torch.randn(50,4,dtype=torch.float64)
    factual=scm.sample_observational(u)
    counter=scm.sample_counterfactual(factual,{1:4.})
    torch.testing.assert_close(counter[:,2],12.+u[:,2])
    torch.testing.assert_close(counter[:,[0,3]],factual[:,[0,3]])

def test_graph_validity_canonical_hash_and_reversal_shd():
    a=DAG(3,((1,2),(0,1)))
    assert a.key==DAG(3,((0,1),(1,2))).key
    with pytest.raises(ValueError):
        DAG(3,((0,1),(1,0)))
    for _,g in a.valid_edits():
        assert len(g.order())==3
    assert structural_metrics(DAG(3,((1,0),(1,2))),a)['shd']==1
    assert not any(0 in g.parents(0) for _,g in a.valid_edits())

def test_split_roles_nested_budgets_and_test_denial():
    a=load_learner(prepare_synthetic(5,'linear',501,100,True),'cpu')
    b=load_learner(prepare_synthetic(5,'linear',501,400,True),'cpu')
    for role in ('fit','early','search','audit'):
        for ea,eb in zip(a.get(role),b.get(role)):
            torch.testing.assert_close(ea.x,eb.x[:len(ea.x)])
    with pytest.raises(ValueError):
        a.get('test')
    assert a.manifest['non_test_intervention_rows']==300
    bad={'splits':{'fit':[{'name':'a','row_ids':[1,2]}],'audit':[{'name':'b','row_ids':[2,3]}]}}
    with pytest.raises(ValueError):
        validate_splits(bad)

def test_cache_matches_canonical_uncached_fit_and_keys_change():
    data=load_learner(prepare_synthetic(5,'linear',502,100,True),'cpu')
    config={**DEFAULT_TRAIN,'steps':4,'check_every':2,'width':8,'batch_size':16}
    a,sa=fit_node(data,1,(0,),config,use_cache=True)
    b,sb=fit_node(data,1,(0,),config,use_cache=True)
    c,sc=fit_node(data,1,(0,),config,use_cache=False)
    assert sb['cache_hit'] and not sa['cache_hit'] and not sc['cache_hit']
    for k,v in a.state_dict().items():
        torch.testing.assert_close(v,b.state_dict()[k],rtol=0,atol=0)
        torch.testing.assert_close(v,c.state_dict()[k],rtol=0,atol=0)
    first=cache_key(data,1,(0,),config,'flow')
    data.preprocessing_hash='changed'
    assert cache_key(data,1,(0,),config,'flow')!=first

def test_budget_deduplication_and_incompatible_resume(tmp_path):
    ledger=Ledger(tmp_path/'ledger',cap_hours=.01)
    assert ledger.claim('job',{'a':1})
    with ledger.device_interval('job'):
        pass
    ledger.finish('job')
    assert not ledger.claim('job',{'a':1})
    with pytest.raises(ValueError):
        ledger.claim('job',{'a':2})
    with pytest.raises(RuntimeError):
        ledger.claim('large',{},expected_seconds=100)

def test_audit_rule_and_no_forced_method_win():
    assert audit_pass({'sw1':1.,'nll':1.},{'sw1':1.04,'nll':1.04},DEFAULT_SEARCH)
    assert not audit_pass({'sw1':1.,'nll':1.},{'sw1':1.2,'nll':.9},DEFAULT_SEARCH)

@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA unavailable: not a GPU experiment')
def test_cuda_flow_gradients_and_checkpoint_restart(tmp_path):
    from sem_update.training import atomic_torch
    model=Mechanism((0,)).cuda()
    x=torch.randn(128,3,device='cuda')
    loss=-model.log_probability(x[:,1],x).mean()
    loss.backward()
    assert torch.isfinite(loss)
    assert all(p.grad is None or (p.grad.is_cuda and torch.isfinite(p.grad).all()) for p in model.parameters())
    path=tmp_path/'check.pt'
    atomic_torch(path,model.state_dict())
    restart=Mechanism((0,)).cuda()
    restart.load_state_dict(torch.load(path,weights_only=True))
    torch.testing.assert_close(model.log_probability(x[:,1],x),restart.log_probability(x[:,1],x))
