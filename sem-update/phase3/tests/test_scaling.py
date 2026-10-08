import copy
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from sem_update.graphs import DAG
from sem_update.data import Environment
from sem_update.flows import Mechanism,GenerativeSCM,balanced_nll
from sem_update.phase2.models import sample
from sem_update.phase3.flows import Group,FastSCM
from sem_update.phase3.graphs import edit_descriptors,apply,corrupt
from sem_update.phase3.data import System,graph_stats,seed_for
from sem_update.phase3.objectives import score,sample_many,distance_mean

def test_lazy_edits_match_historical_legal_set():
    for d in (3,7):
        g=System(d,'nonlinear','sparse',831).graph
        for cap in (2,3,8):
            expected={x.key for _,x in g.valid_edits(max_indegree=cap)}
            actual={apply(g,e).key for e in edit_descriptors(g,cap)}
            assert actual==expected

def test_connected_profiles_and_hidden_order():
    for d in (20,50,100):
        for profile in ('sparse','hub','deep','dense'):
            s=System(d,'heteroscedastic',profile,seed_for(971,d,profile));stats=graph_stats(s.graph)
            assert stats['weak_components']==1 and stats['largest_component']==d
            assert any(a>b for a,b in s.graph.edges)
            assert stats['max_indegree']<= (8 if profile=='dense' else 6 if profile=='hub' else 3)
            if profile!='dense':assert stats['edges']==2*d-3
            if profile=='deep':assert stats['depth']==d-1

def test_fresh_streams_no_large_dimension_seed_collisions():
    values=[seed_for(811,r,j) for r in ('fit','early','search','calibration','audit','T1','T2','T3') for j in range(100)]
    assert len(set(values))==len(values)

@pytest.mark.parametrize('parents',[(),(0,2),(0,1,2,3,4,5,6),(0,1,2,3,4,5,6,7)])
def test_grouped_density_gradients_and_inverse_match_scalar(parents):
    torch.manual_seed(771);models=[Mechanism(parents,16,8,2).double() for _ in range(3)]
    for m in models:
        with torch.no_grad():
            for p in m.parameters():p.add_(torch.randn_like(p)*.02)
    group=Group(models).double();x=torch.randn(37,9,dtype=torch.float64);y=torch.randn(3,37,dtype=torch.float64)*3
    expected=torch.stack([m.log_probability(y[i],x) for i,m in enumerate(models)])
    actual=group.logp(y,group.context(x));torch.testing.assert_close(actual,expected,rtol=1e-8,atol=1e-8)
    actual.sum().backward();expected.sum().backward()
    if parents:
        for p,w in zip(group.weights,(0,2,4)):
            torch.testing.assert_close(p.grad,torch.stack([m.conditioner[w].weight.grad for m in models]),rtol=1e-7,atol=1e-7)
    else:torch.testing.assert_close(group.constant.grad,torch.stack([m.constant.grad for m in models]))
    out,ld=group.transform(y,group.context(x),False);back,ild=group.transform(out,group.context(x),True)
    torch.testing.assert_close(back,y,rtol=1e-7,atol=1e-7);torch.testing.assert_close(ld,-ild,rtol=1e-7,atol=1e-7)

def test_fast_topological_sampling_likelihood_and_exact_masks():
    torch.manual_seed(41);graph=System(20,'nonlinear','sparse',38).graph
    models=[Mechanism(graph.parents(j),16) for j in range(graph.d)];fast=FastSCM(graph,models);old=GenerativeSCM(graph,models)
    u=torch.randn(101,20);target=graph.order()[3];law={target:torch.randn(101)}
    torch.testing.assert_close(fast.sample_intervention(u,law),old.sample_intervention(u,law),rtol=3e-5,atol=3e-5)
    torch.testing.assert_close(fast.log_probability(u,(target,)),old.log_probability(u,(target,)),rtol=3e-5,atol=3e-5)
    retained_groups=len(fast._groups)
    for mask in range(graph.d):fast.log_probability(u,(mask,));fast.infer_disturbances(u,(mask,))
    assert len(fast._groups)==retained_groups
    assert torch.equal(fast.sample_intervention(u,law)[:,target],law[target])
    for j,m in enumerate(models):
        other=[a for a in range(20) if a not in m.parents];xx=u.clone();xx[:,other]+=19
        torch.testing.assert_close(m.parameters_for(u),m.parameters_for(xx),rtol=0,atol=0)

def test_multi_environment_sampling_and_score_decomposition():
    graph=DAG(3,((2,0),(0,1)));model=FastSCM(graph,[Mechanism(graph.parents(j),16) for j in range(3)])
    envs=[Environment('obs',torch.randn(40,3),{},())]+[Environment(str(j),torch.randn(21+j,3),{str(j):{'kind':'normal','mean':1.,'scale':.25}},()) for j in (0,2)]
    ys=sample_many(model,envs,50,331)
    for i,e in enumerate(envs):torch.testing.assert_close(ys[i],sample(model,e.assignments,50,331+(i+1)*19,'cpu'),rtol=2e-5,atol=2e-5)
    scored=score(model,envs,{'samples':32,'projections':8})
    assert scored['nll']==pytest.approx(float(balanced_nll(model,envs)),abs=2e-6)
    assert np.mean(scored['environment_scores'])==pytest.approx(scored['total'])
    a=torch.randn(29,4);b=torch.randn(61,4)
    assert float(distance_mean(a,b,13))==pytest.approx(float(torch.cdist(a,b).mean()),abs=1e-6)

def test_generator_common_noise_invariance_and_stability():
    import networkx as nx
    for profile in ('sparse','dense','hub','deep'):
        s=System(100,'heteroscedastic',profile,932);u=torch.randn(1200,100);x=s.sample(1200,21,device='cpu',noises=u)
        target=s.graph.order()[2];y=s.sample(1200,21,{target:{'kind':'fixed','value':3.}},device='cpu',noises=u)
        unchanged=sorted(set(range(100))-nx.descendants(s.graph.networkx(),target)-{target})
        assert torch.equal(x[:,unchanged],y[:,unchanged]);assert x.abs().max()<20 and x.std(0).min()>.05

@pytest.mark.parametrize('dimension',[20,50,100])
def test_dcdi_batched_conditioner_density_gradient_equivalence(dimension):
    from sem_update.phase3.discovery import batched_forward
    from sem_update.phase2.discovery import official_dsf
    from sem_update.dcdi import DEFAULT
    import types
    cfg={**DEFAULT,'flow_layers':2,'flow_width':8};model=official_dsf(dimension,cfg);x=torch.randn(33,dimension,device='cuda')
    rng=torch.cuda.get_rng_state();old=model.compute_log_likelihood(x,*model.get_parameters());old.sum().backward()
    grads=[p.grad.detach().clone() if p.grad is not None else None for p in model.parameters()];model.zero_grad()
    torch.cuda.set_rng_state(rng);model.forward_given_params=types.MethodType(batched_forward,model)
    new=model.compute_log_likelihood(x,*model.get_parameters());new.sum().backward()
    torch.testing.assert_close(old,new,rtol=5e-5,atol=5e-5)
    for a,p in zip(grads,model.parameters()):
        if a is not None:torch.testing.assert_close(a,p.grad,rtol=3e-4,atol=5e-5)

def test_grouped_fit_cache_and_canonical_independence(tmp_path,monkeypatch):
    from sem_update.phase3.data import prepare,load
    from sem_update.phase3.flows import fit_graph,mechanism_key
    from sem_update.training import DEFAULT_TRAIN
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path))
    task={'d':5,'seed':399901,'family':'linear','profile':'sparse','development':True}
    folder=prepare(task,{'budget_per_target':100});data=load(folder,allowed=('fit','early'))
    graph=System(5,'linear','sparse',399901).graph;cfg={**DEFAULT_TRAIN,'steps':50,'check_every':25,'width':16,'group_size':32}
    fitted,stats=fit_graph(data,graph,cfg);cached,again=fit_graph(data,graph,cfg,False)
    assert all(r['cache_hit'] for r in again);x=data.get('fit')[0].x[:32]
    torch.testing.assert_close(fitted.log_probability(x),cached.log_probability(x),rtol=0,atol=0)
    # A different graph reuses every unchanged mechanism; no graph-wide seed.
    edit=next(g for _,g in graph.valid_edits() if len(g.edges)==len(graph.edges)-1)
    changed,records=fit_graph(data,edit,cfg)
    for j in range(5):
        if graph.parents(j)==edit.parents(j):assert records[j]['cache_hit'] and records[j]['key']==stats[j]['key']
    assert mechanism_key(data,0,(),cfg)!=mechanism_key(data,0,(),{**cfg,'steps':75})
    with pytest.raises(ValueError):data.get('calibration')

def test_grouped_optimizer_and_rng_resume_exactly(tmp_path,monkeypatch):
    import sem_update.phase3.flows as module
    from sem_update.phase3.data import prepare,load
    from sem_update.training import DEFAULT_TRAIN
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path/'uninterrupted'))
    task={'d':3,'seed':399902,'family':'nonlinear','profile':'sparse','development':True}
    data=load(prepare(task,{'budget_per_target':100}),allowed=('fit','early'));graph=DAG(3,((2,0),(0,1)))
    cfg={**DEFAULT_TRAIN,'steps':50,'check_every':25,'width':16,'group_size':32}
    expected,_=module.fit_graph(data,graph,cfg)
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path/'resumed'))
    original=module.check_budget;calls=[]
    def interrupt():
        calls.append(1)
        if len(calls)==2:raise RuntimeError('Controlled interruption after an atomic checkpoint')
    monkeypatch.setattr(module,'check_budget',interrupt)
    with pytest.raises(RuntimeError,match='Controlled interruption'):module.fit_graph(data,graph,cfg)
    monkeypatch.setattr(module,'check_budget',original)
    actual,_=module.fit_graph(data,graph,cfg)
    for x,y in zip(expected.parameters(),actual.parameters()):torch.testing.assert_close(x,y,rtol=0,atol=0)

def test_budget_sensitivity_is_nested_and_roles_remain_disjoint(tmp_path,monkeypatch):
    from sem_update.phase3.data import prepare,load,ROLES
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path))
    task={'d':20,'seed':399903,'family':'heteroscedastic','profile':'sparse','development':True}
    small=load(prepare({**task,'budget':100},{'budget_per_target':400}))
    large=load(prepare(task,{'budget_per_target':400}))
    ids=[]
    for role in ROLES:
        for a,b in zip(small.get(role),large.get(role)):
            torch.testing.assert_close(a.x,b.x[:len(a.x)],rtol=0,atol=0);ids.extend(a.row_ids)
    assert len(ids)==len(set(ids));assert small.manifest['non_test_intervention_rows']==400
    assert not(set(small.manifest['seen_targets'])&set(small.manifest['withheld_targets']))

def test_completed_prefix_cost_counts_search_and_keeps_original_incumbent():
    from sem_update.phase3.bank import cost,subbank,prefix_keys
    from sem_update.phase3.runtime import digest
    def fit(key,updates,seconds):return {'key':key,'updates':updates,'fit_seconds':seconds,'parents':[0]}
    candidates={
        'g0':{'ordinal':1,'fits':[fit('a',100,3)],'score_seconds':1.,'peak_vram_bytes':100,
              'prefix_cost':{'fitting_updates':100,'gpu_job_seconds':4}},
        'g1':{'ordinal':2,'fits':[fit('a',100,3),fit('b',50,2)],'score_seconds':1.,'peak_vram_bytes':150,
              'prefix_cost':{'fitting_updates':150,'gpu_job_seconds':9}},
        'g2':{'ordinal':3,'fits':[fit('a',100,3),fit('c',200,6)],'score_seconds':1.,'peak_vram_bytes':300,
              'prefix_cost':{'fitting_updates':350,'gpu_job_seconds':19}}}
    value={'initial':'g0','incumbent':'g2','candidates':candidates,'edits':[
        {'evaluated':['g1'],'after':'g0','accepted':False,'overhead_seconds':2.},
        {'evaluated':['g2'],'after':'g2','accepted':True,'overhead_seconds':3.}]}
    value['bank_hash']=digest(value)
    assert prefix_keys(value,'fitting_updates',99)==[]
    assert prefix_keys(value,'fitting_updates',160)==['g0','g1']
    assert prefix_keys(value,'gpu_job_seconds',8)==['g0']
    assert cost(candidates)['fitting_updates']==350
    limited=subbank(value,['g0','g1'])
    assert limited['incumbent']=='g0' and limited['logical_seconds']==9
    assert limited['peak_vram_bytes']==150 and len(limited['edits'])==1
    assert digest({k:v for k,v in limited.items() if k!='bank_hash'})==limited['bank_hash']

def test_resume_preserves_sealed_incomplete_selection_boundary(tmp_path,monkeypatch):
    import sem_update.phase3.runner as runner
    from sem_update.phase3.runtime import atomic_json,file_hash
    monkeypatch.setattr(runner,'RESULTS',tmp_path);monkeypatch.setattr(runner,'root',lambda:tmp_path)
    monkeypatch.setattr(runner,'scientific_hash',lambda:'verified-source')
    monkeypatch.setattr(runner,'freeze_guard',lambda:{'tasks':[]})
    atomic_json(tmp_path/'protocol.json',{'frozen':True});atomic_json(tmp_path/'model.json',{'frozen_model':True})
    frozen={'source_hash':'verified-source','protocol_sha256':file_hash(tmp_path/'protocol.json'),
        'records':{'model.json':file_hash(tmp_path/'model.json')},'incomplete_tasks':[{'seed':999}],
        'frozen_utc':'immutable'}
    atomic_json(tmp_path/'frozen_selections.json',frozen)
    before=(tmp_path/'frozen_selections.json').read_bytes();runner.run()
    assert (tmp_path/'frozen_selections.json').read_bytes()==before
