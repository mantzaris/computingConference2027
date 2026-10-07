import json
import pytest
import torch
from sem_update.graphs import DAG
from sem_update.phase2.llm import parse_menu,render
from sem_update.llm import metadata
from sem_update.phase2.bank import prefix_keys

def test_menu_parsing_complete_graph_path_and_counts():
    initial=DAG(3,((0,1),));options=list(initial.valid_edits())
    menu=[{'id':f'E{i:03d}','graph':g.json(),'operation':e['operation'],'source':f'V{e["source"]}','target':f'V{e["target"]}'} for i,(e,g) in enumerate(options)]
    graphs,counts,valid=parse_menu('{"edit_ids":["E000","E000","UNKNOWN"]}',menu)
    assert not valid and len(graphs)==1
    assert counts['duplicate_graphs']==1 and counts['invalid_nodes']==1 and counts['valid_new_edits']==1
    assert graphs[0].key in {g.key for _,g in initial.valid_edits()}
    assert parse_menu('not json',menu)[1]['malformed_output']==1
    assert parse_menu('{"edit_ids":[]}',menu)[1]['valid_no_change']==1

def test_prompt_whitelist_and_unambiguous_node_ids():
    nodes=metadata('semantic','coherent',871)
    for r in nodes:r['true_graph']='SECRET';r['final_outcomes']='SECRET'
    request={'kind':'edit','nodes':nodes,'roots':[0,1,2],'current':DAG(5,((0,3),)).json(),
        'feedback':[{'score':1.2}], 'menu':[{'id':'E000','operation':'add','source':'V1','target':'V3','graph':DAG(5,((0,3),(1,3))).json()}]}
    text=render(request)
    assert 'SECRET' not in text and 'final_outcomes' not in text
    assert '["V0", "V3"]' in text and 'edit_ids' in text
    assert text==render(json.loads(json.dumps(request)))

def test_compute_checkpoint_requires_complete_prefix_and_initial():
    bank={'initial':'b','candidates':{'a':{'ordinal':1,'prefix_cost':{'fitting_updates':100}},
        'b':{'ordinal':2,'prefix_cost':{'fitting_updates':200}},'c':{'ordinal':3,'prefix_cost':{'fitting_updates':250}}}}
    assert prefix_keys(bank,'fitting_updates',150)==[]
    assert prefix_keys(bank,'fitting_updates',220)==['a','b']

def test_fresh_data_nested_budget_views_and_partition_denial(tmp_path,monkeypatch):
    from sem_update.phase2.data import prepare,load
    monkeypatch.setenv('SEM_UPDATE_ARTIFACT_ROOT',str(tmp_path))
    a=load(prepare(5,'linear',298801,100,True))
    b=load(prepare(5,'linear',298801,400,True))
    for role in ('fit','early','search','calibration','audit'):
        for x,y in zip(a.get(role),b.get(role)):torch.testing.assert_close(x.x,y.x[:len(x.x)],rtol=0,atol=0)
    assert a.manifest['non_test_intervention_rows']==300
    restricted=load(prepare(5,'linear',298801,100,True),allowed=('fit','early','search'))
    with pytest.raises(ValueError):restricted.get('calibration')
    with pytest.raises(ValueError):restricted.get('audit')

def test_bank_rejects_unrestricted_data_and_changed_bank():
    from types import SimpleNamespace
    from sem_update.phase2.bank import build,load_models
    with pytest.raises(ValueError):build(SimpleNamespace(allowed=('fit','calibration')),[], 'x',{})
    with pytest.raises(ValueError):load_models({'bank_hash':'wrong','candidates':{}},None,{})

def test_fit_identity_does_not_hash_calibration_or_audit_outcomes():
    import copy
    import numpy as np
    from sem_update.phase2.data import partition_hashes,training_identity
    roles=['fit','early','search','calibration','audit']
    arrays={r:np.zeros((3,2),dtype='float32') for r in roles}
    manifest={'id':'fixture','d':2,'standardization':{'mean':[0,0],'std':[1,1]},
        'splits':{r:[{'name':r,'array':r,'assignments':{},'row_ids':[r+str(i) for i in range(3)]}] for r in roles}}
    manifest['partition_hashes']=partition_hashes(manifest,arrays);first=training_identity(manifest)
    changed=copy.deepcopy(manifest);arrays['calibration'][:]=100.;arrays['audit'][:]=-100.
    changed['partition_hashes']=partition_hashes(changed,arrays)
    assert first==training_identity(changed)
    assert changed['partition_hashes']['calibration']!=manifest['partition_hashes']['calibration']
    arrays['fit'][:]=1.;changed['partition_hashes']=partition_hashes(changed,arrays)
    assert first!=training_identity(changed)
