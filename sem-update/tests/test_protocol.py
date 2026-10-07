import json
import numpy as np
import pandas as pd
import pytest
import torch
from sem_update.data import prepare_synthetic,load_learner
from sem_update.flows import GenerativeSCM,Mechanism
from sem_update.graphs import DAG
from sem_update.llm import metadata,make_prompt,validate_graph
from sem_update.runtime import Ledger
from sem_update.search import repair
from sem_update.evaluation import cluster_interval

def test_prompts_exclude_truth_and_future_fields():
    nodes=metadata('semantic','coherent',42)
    for row in nodes:
        row['true_parents']='SECRET_TRUTH'
        row['test_outcomes']='SECRET_OUTCOME'
    prompt=make_prompt(nodes,[0,1,2])
    assert 'SECRET' not in prompt and 'true_parents' not in prompt
    anonymous=metadata('semantic','anonymous',42)
    assert all('light' not in row['description'].lower() for row in anonymous)
    shuffled=metadata('semantic','shuffled',42)
    assert sorted(r['description'] for r in shuffled)==sorted(r['description'] for r in nodes)

def test_llm_invalid_cycles_names_and_root_constraints():
    nodes=metadata('semantic','coherent',1)
    value={'nodes':[r['id'] for r in nodes], 'edges':[{'source':'V0','target':'V3','rationale':'hypothesis'}]}
    assert validate_graph(value,nodes,[0,1,2]).edges==((0,3),)
    value['edges'].append({'source':'V3','target':'V0','rationale':'bad'})
    with pytest.raises(ValueError):
        validate_graph(value,nodes,[0,1,2])

def test_budget_pairs_share_data_starts_and_verifier(tmp_path,monkeypatch):
    import sem_update.search as search
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    torch.set_num_threads(2)
    data=load_learner(prepare_synthetic(5,'linear',504,100,True),'cpu')
    graph=DAG(5,((0,1),(1,2),(2,3),(3,4)))
    def fake_fit(data,g,config,kind):
        model=GenerativeSCM(g,[Mechanism(g.parents(j),width=8) for j in range(g.d)])
        return model,[{'key':str(j)+str(g.parents(j)),'cache_hit':True,'actual_updates':0} for j in range(g.d)]
    monkeypatch.setattr(search,'fit_graph',fake_fit)
    monkeypatch.setattr(search,'score',lambda m,e,c,role='search':{'nll':1.,'sw1':.1,'total':1.+.01*len(m.graph.edges),'edge_penalty':0.})
    monkeypatch.setattr(search,'disturbances',lambda *a,**kw:[{'node':j,'priority':float(j)} for j in range(5)])
    a=repair(data,[graph],'proposed','diagnostic')
    b=repair(data,[graph],'random','random')
    assert a['identity']['data']==b['identity']['data']
    assert a['identity']['starts']==b['identity']['starts']
    assert a['identity']['search']==b['identity']['search']
    assert a['candidate_count']<=12 and b['candidate_count']<=12
    assert repair(data,[graph],'proposed','diagnostic')==json.loads(json.dumps(a))

def test_resume_dead_owner_preserves_dedup_and_intervals(tmp_path):
    ledger=Ledger(tmp_path/'ledger')
    ledger.claim('interrupted',{'config':1})
    ledger.db.execute("UPDATE jobs SET owner='99999999:0' WHERE id='interrupted'")
    ledger.db.commit()
    assert ledger.claim('interrupted',{'config':1})
    ledger.finish('interrupted')
    assert not ledger.claim('interrupted',{'config':1})
    row=ledger.db.execute("SELECT attempts FROM jobs WHERE id='interrupted'").fetchone()
    assert row[0]==2

def test_cluster_bootstrap_does_not_count_conditions_as_scms():
    rows=[]
    for seed in range(5):
        for budget in (100,400):
            rows.append({'family':'linear','d':5,'seed':seed,'budget':budget,'delta':seed-2.})
    result=cluster_interval(pd.DataFrame(rows),replicates=200)
    assert result['independent_scms']==5
    assert result['mean']==0.
    assert result['low']<0<result['high']

def test_conditioning_is_not_intervention_in_confounding_toy():
    from test_semantics import Linear
    scm=GenerativeSCM(DAG(3,((0,1),(0,2))),[Linear((),[]),Linear((0,),[2.]),Linear((0,),[3.])])
    torch.manual_seed(913)
    u=torch.randn(100000,3,dtype=torch.float64)
    obs=scm.sample_observational(u)
    conditional=obs[(obs[:,1]>1.8)&(obs[:,1]<2.2),2].mean()
    intervention=scm.sample_intervention(u,{1:2.})[:,2].mean()
    assert abs(conditional-2.4)<.2
    assert abs(intervention)<.04

def test_completed_partial_checkpoint_resumes_without_extra_updates(tmp_path,monkeypatch):
    from sem_update.training import fit_node,DEFAULT_TRAIN
    from sem_update.runtime import artifact_root
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path/'artifacts'))
    data=load_learner(prepare_synthetic(5,'linear',505,100,True),'cpu')
    cfg={**DEFAULT_TRAIN,'steps':4,'check_every':2,'width':8,'batch_size':16}
    a,stats=fit_node(data,1,(0,),cfg)
    final=artifact_root()/'checkpoints'/stats['key'][:2]/(stats['key']+'.pt')
    final.rename(final.with_suffix('.original.pt'))
    b,resumed=fit_node(data,1,(0,),cfg)
    assert resumed['actual_updates']==0
    for k,v in a.state_dict().items():
        torch.testing.assert_close(v,b.state_dict()[k],rtol=0,atol=0)

def test_real_bootstrap_preserves_blocks_and_distance_axes():
    from sem_update.real_uncertainty import resample_blocks,projected_bootstrap
    generator=torch.Generator().manual_seed(73)
    indices=resample_blocks(30,10,17,generator,'cpu')
    blocks=indices.reshape(17,3,10)
    assert torch.all(blocks.diff(dim=2)==1)
    assert torch.all(blocks[:,:,0]%10==0)
    observed=torch.zeros(30,2)
    prediction=torch.stack([torch.zeros(512,2),torch.ones(512,2)*2])
    draws=projected_bootstrap(observed,prediction,indices)
    assert draws.shape==(17,2)
    torch.testing.assert_close(draws[:,0],torch.zeros(17))
    torch.testing.assert_close(draws[:,1],torch.full((17,),2.))

def test_orphan_execution_interval_does_not_accumulate_forever(tmp_path):
    import time
    ledger=Ledger(tmp_path/'ledger')
    ledger.claim('old-wrapper',{})
    ledger.db.execute("UPDATE jobs SET owner='99999999:0' WHERE id='old-wrapper'")
    start=time.time()-100
    ledger.db.execute('INSERT INTO intervals (token,job,start,end,heartbeat) VALUES (?,?,?,NULL,?)',
                      ('old-token','old-wrapper',start,start+20))
    ledger.db.commit()
    recovered=Ledger(tmp_path/'ledger')
    assert recovered.used_seconds()==pytest.approx(30.)
    assert recovered.snapshot()['jobs'][0]['status']=='failed'

def test_llm_feedback_prompt_is_stable_after_json_checkpoint_roundtrip():
    nodes=metadata('semantic','coherent',42)
    feedback={'incumbent':{'d':5,'edges':[[0,3]]},'history':[],
              'evaluated':[{'graph':{'d':5,'edges':[[0,3]]},'score':{'nll':1.,'sw1':.2,'total':1.2}}]}
    restored=json.loads(json.dumps(feedback,sort_keys=True))
    assert make_prompt(nodes,[0,1,2],feedback)==make_prompt(nodes,[0,1,2],restored)
