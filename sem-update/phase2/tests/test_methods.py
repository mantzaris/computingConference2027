import math
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from sem_update.graphs import DAG
from sem_update.data import Environment
from sem_update.flows import GenerativeSCM,balanced_nll
from sem_update.phase2.models import EmpiricalMarginals,RidgeMechanism,ridge_fit,Ensemble,sample,joint_nll
from sem_update.phase2.objectives import score,select,energy_matrices,fit_weights,weight_objective

def normal_graph(means=(0.,0.),scale=1.):
    graph=DAG(len(means))
    return GenerativeSCM(graph,[RidgeMechanism((),torch.tensor(v),torch.empty(0),torch.tensor(scale)) for v in means])

def environment(x,name='obs',target=None):
    law={} if target is None else {target:{'kind':'fixed','value':1.}}
    return Environment(name,x,law,tuple(f'{name}:{i}' for i in range(len(x))))

def test_empirical_independent_control_and_intervention():
    torch.manual_seed(782)
    x=torch.arange(1000).float().view(-1,1).repeat(1,2)
    model=EmpiricalMarginals(x)
    y=sample(model,{},100000,44,'cpu')
    assert abs(torch.corrcoef(y.T)[0,1])<.015
    assert y.min()>=0 and y.max()<=999
    z=sample(model,{0:{'kind':'fixed','value':5.}},100000,44,'cpu')
    assert torch.all(z[:,0]==5.)
    torch.testing.assert_close(z[:,1],y[:,1],rtol=0,atol=0)
    assert joint_nll(model,[environment(x)]) is None

def test_ridge_excludes_target_mechanism_and_preserves_do_semantics():
    torch.manual_seed(88);x=torch.randn(20000,2);x[:,1]=2*x[:,0]+.1*x[:,1]
    altered=x.clone();altered[:,1]=999
    envs=[environment(x),environment(altered,'do1',1)]
    data=SimpleNamespace(d=2,get=lambda role:envs)
    fitted=ridge_fit(data,DAG(2,((0,1),)),alpha=.00001)
    assert fitted.mechanisms[1].coefficients.item()==pytest.approx(2.,abs=.003)
    assert fitted.mechanisms[1].scale.item()==pytest.approx(.1,abs=.003)
    y=sample(fitted,{0:{'kind':'fixed','value':3.}},20000,89,'cpu')
    assert y[:,1].mean()==pytest.approx(6.,abs=.01)
    assert fitted.mechanisms[1].scale>0

def test_mixture_chooses_one_component_for_whole_observation():
    models=[normal_graph((-10.,-10.),.001),normal_graph((10.,10.),.001)]
    model=Ensemble(models,[.3,.7]);y=sample(model,{},30000,721,'cpu')
    assert torch.all((y[:,0]>0)==(y[:,1]>0))
    assert (y[:,0]>0).float().mean()==pytest.approx(.7,abs=.01)
    z=sample(model,{0:{'kind':'fixed','value':4.}},30000,721,'cpu')
    assert torch.all(z[:,0]==4.)

def test_mixture_joint_likelihood_mixes_products_not_nodes():
    a,b=normal_graph((-3.,-3.)),normal_graph((3.,3.));model=Ensemble([a,b],[.4,.6])
    x=torch.tensor([[-3.,3.],[3.,3.]])
    expected=torch.logsumexp(torch.stack([a.log_probability(x).sum(1)+math.log(.4),b.log_probability(x).sum(1)+math.log(.6)],1),1)
    torch.testing.assert_close(model.joint_log_probability(x),expected)
    wrong=torch.logsumexp(torch.stack([a.log_probability(x)+math.log(.4),b.log_probability(x)+math.log(.6)],2),2).sum(1)
    assert abs(wrong[0]-expected[0])>10
    torch.testing.assert_close(joint_nll(model,[environment(x)]),-expected.mean()/2)
    target=model.joint_log_probability(x,(0,))
    desired=torch.logsumexp(torch.stack([a.log_probability(x,(0,)).sum(1)+math.log(.4),b.log_probability(x,(0,)).sum(1)+math.log(.6)],1),1)
    torch.testing.assert_close(target,desired)

def test_serialized_mixture_preserves_tiny_positive_tail_components():
    from sem_update.phase2.selection import mixture_spec
    bank={'candidates':{'a':{'graph':DAG(2).json()},'b':{'graph':DAG(2,((0,1),)).json()}}}
    weights=[1.-1e-12,1e-12]
    spec=mixture_spec(['a','b'],weights,bank)
    assert spec['kind']=='ensemble' and len(spec['components'])==2
    assert spec['weights'][1]==pytest.approx(1e-12,rel=1e-12,abs=0.)
    a,b=normal_graph(),normal_graph((30.,30.))
    mixture=Ensemble([a,b],weights);x=torch.full((1,2),30.)
    assert (mixture.joint_log_probability(x)-a.log_probability(x).sum(1)).item()>800

def test_per_environment_score_reconstructs_balanced_objective():
    torch.manual_seed(42);model=normal_graph((0.,0.,0.))
    envs=[environment(torch.randn(n,3),str(i),None if i==0 else i-1) for i,n in enumerate([130,10,25])]
    row=score(model,envs,{'samples':64,'projections':8})
    assert np.mean(row['environment_scores'])==pytest.approx(row['total'],abs=2e-6)
    assert row['nll']==pytest.approx(balanced_nll(model,envs).item())

def test_robust_selection_rho_zero_and_initial_retention():
    scores={'a':{'environment_scores':[1.,1.]},'b':{'environment_scores':[.1,1.5]},'c':{'environment_scores':[.8,.8]}}
    assert select(scores,'a',0)[0]=='b'
    assert select(scores,'a',.5)[0]=='c'
    assert select({'a':scores['a'],'b':{'environment_scores':[.999,1.]}},'a',.5)[0]=='a'

def test_fixed_sample_energy_quadratic_matches_explicit_distribution():
    z=np.array([-2.,1.,4.]);actual=np.array([0.,1.5]);w=np.array([.2,.3,.5])
    a=np.abs(z[:,None]-actual).mean(1);b=np.abs(z[:,None]-z[None,:])
    expected=sum(w[i]*abs(z[i]-y)/len(actual) for i in range(3) for y in actual)-.5*sum(w[i]*w[j]*abs(z[i]-z[j]) for i in range(3) for j in range(3))
    assert weight_objective(w,a,b,0)==pytest.approx(expected)
    for tau in [0.,.01]:
        weights,result=fit_weights(a,b,tau,True)
        assert weights.sum()==pytest.approx(1.) and weights.min()>=0
        assert result['grid_gap']<=1e-8

def test_component_weight_optimizer_anchor_and_environment_balance():
    models=[normal_graph(),normal_graph((1.,1.)),normal_graph((-1.,-1.))]
    envs=[environment(torch.ones(20,2),'one',0),environment(torch.ones(30,2),'two',1)]
    a,b,_=energy_matrices(models,envs,64,311)
    again=energy_matrices(models,envs,64,311)
    np.testing.assert_array_equal(a,again[0]);np.testing.assert_array_equal(b,again[1])
    unanchored,_=fit_weights(a,b,0,True);anchored,_=fit_weights(a,b,1.,True)
    assert anchored[0]>=unanchored[0]-1e-6

def test_cuda_dsf_density_and_gradients_match_cpu():
    from sem_update.phase2.runtime import setup,require_cuda
    from sem_update.phase2.discovery import official_dsf
    from sem_update.dcdi import DEFAULT
    setup();require_cuda();torch.manual_seed(291)
    model=official_dsf(3,{**DEFAULT,'width':8,'layers':1,'flow_layers':2,'flow_width':4})
    x=torch.randn(19,3,device='cuda')
    params=[torch.randn(19,model.flow_n_cond_params_per_var,device='cuda',requires_grad=True) for _ in range(3)]
    actual=model._log_likelihood(x,params);gradient=torch.autograd.grad(actual.sum(),params)
    cp=[v.detach().cpu().requires_grad_() for v in params];model.cpu()
    expected=model._log_likelihood(x.cpu(),cp);eg=torch.autograd.grad(expected.sum(),cp)
    torch.testing.assert_close(actual.cpu(),expected,rtol=2e-5,atol=2e-5)
    for a,b in zip(gradient,eg):torch.testing.assert_close(a.cpu(),b,rtol=3e-4,atol=2e-5)
    model.cuda();model.adjacency=model.adjacency.cuda()
    loss=-model.compute_log_likelihood(x,*model.get_parameters()).mean();loss.backward()
    assert torch.isfinite(loss) and any(p.grad is not None and p.grad.is_cuda and p.grad.abs().sum()>0 for p in model.parameters())

def test_selected_candidate_is_audited_once_and_rejection_returns_initial(tmp_path,monkeypatch):
    import sem_update.phase2.selection as module
    from sem_update.search import DEFAULT_SEARCH
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path))
    a=normal_graph();g=DAG(2,((0,1),))
    b=GenerativeSCM(g,[RidgeMechanism((),torch.tensor(0.),torch.empty(0),torch.tensor(1.)),
        RidgeMechanism((0,),torch.tensor(0.),torch.zeros(1),torch.tensor(1.))])
    models={a.graph.key:a,b.graph.key:b};initial=a.graph.key
    bank={'bank_hash':'immutable-development-fixture','initial':initial,'identity':{'policy':'diagnostic'},
        'cost':{'fit_seconds':1.,'fitting_updates':100,'parent_sets':3},'logical_seconds':1.,
        'candidates':{k:{'graph':m.graph.json(),'search':{'total':1. if m is a else .1}} for k,m in models.items()}}
    monkeypatch.setattr(module,'load_models',lambda *args:models)
    monkeypatch.setattr(module,'score',lambda m,*args:{'environment_scores':[1.,1.] if m is a else [.1,.1]})
    audited=[]
    def audit(model,*args):
        audited.append(model)
        return {'sw1':1. if model is a else 2.,'nll':1.}
    monkeypatch.setattr(module,'audit_score',audit)
    env=environment(torch.ones(20,2),'do0',0)
    data=SimpleNamespace(get=lambda role:[env])
    cfg={'search':{**DEFAULT_SEARCH,'samples':32},'rho':.5,'tau':.01,'checkpoints':{}}
    result=module.choose(bank,data,cfg,'fixture',True,False)
    for name in ('M3','M4','rho0'):
        row=result['methods'][name]
        assert row['before_audit']['graph']==g.json()
        assert not row['audit_pass'] and row['selected']['graph']==a.graph.json()
    assert sum(model is b for model in audited)==1
    assert bank['bank_hash']=='immutable-development-fixture'
