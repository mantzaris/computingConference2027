"""V4 behavioral protections; fixtures are tests, not application evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

from test_v3 import fixture
from got_war.v3.core import fingerprint, query, validate_representation
from got_war.v3.study import packet
from got_war.v4.application import compile_families, compile_attempt, expression
from got_war.v4.corpus import episode_time, parse_page, search
from got_war.v4.figures import graph, model_hash, render_case

ROOT=Path(__file__).resolve().parents[1]


def scenario():
    rep,_,pkt=fixture();rep['mechanisms'][0]['id']='M_Y'
    draft={'scope_status':'declared_family','scope_assumptions':['Restricted fixture scope'],
        'scenarios':[{'id':'s','label':'switch-controlled','interpretation':'The switch is required.',
        'equations':{'Y':'S'},'assumptions':{'Y':'The switch is required.'},
        'claims':[{'record_id':'M_Y','child':'Y','text':'The switch is required.',
                   'predicate':{'kind':'row','when':{'S':0},'allowed':[0]}}]}]}
    return rep,draft,pkt


def test_expanded_retrieval_can_escape_existing_packet(tmp_path):
    p=tmp_path/'.private/v4';p.mkdir(parents=True)
    scenes=[{'id':'old','text':'The switch is on.','episode':'s01e01','source_id':'one','start':0,'end':17},
            {'id':'new','text':'The unavailable ferry route cancels access.','episode':'s06e09','source_id':'six','start':0,'end':42}]
    (p/'corpus.json').write_text(json.dumps({'segments':scenes}));folder=p/'case';folder.mkdir()
    (folder/'packet.json').write_text(json.dumps(packet(scenes[:1])))
    got=search(tmp_path,{'id':'case','episodes':['s01e01','s06e09']},'unavailable ferry route',context_scenes=0)
    assert 'new' in {s['id'] for s in got}
    h=json.loads((folder/'retrieval.json').read_text())[-1]
    assert h['searched_scenes']==2 and 'new' in h['new_ids']


def test_cross_season_time_and_retrospective_information():
    assert episode_time('s06e09',.2)>episode_time('s01e10',.9)
    rep,_,pkt=fixture();rep['variables'][0].update(event_time=609.1,statement_time=610.1)
    rep['variables'][1].update(event_time=609.2,statement_time=609.2)
    assert validate_representation(rep,pkt)['variables'][0]['statement_time']==610.1
    rep['variables'][0]['event_time']=610.1
    with pytest.raises(ValueError,match='Temporal counterexample'):validate_representation(rep,pkt)


def test_parser_preserves_full_context_and_stable_line_ids():
    page='<div class="scene-container" id="S2"><p id="S2L1">First event</p><p id="S2L2">A later report<button>copy</button></p></div>'
    s=parse_page(page,'https://example.test/episode','s06e10')[0]
    assert s['text']=='First event\nA later report' and s['line_ids']==['S2L1','S2L2']
    assert s['url'].endswith('#S2L1') and s['end']==len(s['text'])


def test_scenario_assumptions_do_not_complete_partial_family():
    r,d,p=scenario();partial,sc=compile_families(r,d,p)
    assert query(r,partial,{'S':0})['values']==[0,1]
    assert query(r,sc[0]['family'],{'S':0})['values']==[0]
    old=fingerprint(sc[0]['family']);query(r,sc[0]['family'],{'S':1})
    assert fingerprint(sc[0]['family'])==old


def test_factual_disagreement_rejects_scenario_and_preserves_observation():
    r,d,p=scenario();d['scenarios'][0]['equations']['Y']='not S'
    with pytest.raises(ValueError,match='conflicts with established'):compile_families(r,d,p)
    assert r['variables'][-1]['factual']==1


def test_prose_contradiction_provides_concrete_counterexample():
    r,d,p=scenario();d['scenarios'][0]['equations']['Y']='1'
    with pytest.raises(ValueError,match='counterexample.*inputs.*S.*0'):compile_families(r,d,p)
    d['scenarios'][0]['claims'][0]['text']='Invented review instructions'
    with pytest.raises(ValueError,match='quote actual'):compile_families(r,d,p)


def test_compilation_failure_retained_with_actionable_bounded_repair(tmp_path):
    bad={'evidence':[],'representation':{'variables':[],'edges':[],'mechanisms':[]}}
    with pytest.raises(ValueError):compile_attempt(tmp_path,{'id':'bad'},bad,{'segments':[]},0)
    report=json.loads((tmp_path/'runs/application_v4_20261013/bad/compilation_failed_0.json').read_text())
    assert report['draft']==bad and 'Established factual rows cannot be relaxed' in report['repair_instruction']
    with pytest.raises(ValueError,match='maximum'):compile_attempt(tmp_path,{'id':'bad'},bad,{},3)


def test_no_arbitrary_python_in_equations():
    for text in ['__import__("os")','S + 1','S.attr','unknown','S if S else 0']:
        with pytest.raises(ValueError):expression(text,['S'])


@pytest.fixture(scope='module')
def archive():
    spec=importlib.util.spec_from_file_location('v4_repro',ROOT/'scripts/v4_reproduce.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod,mod.load()


def test_all_six_application_records_reproduce(archive):
    mod,data=archive;records,counts=mod.verify(data)
    assert counts['cases']==6 and counts['queries']==18 and counts['scenario_queries']==36
    assert all(q['partial_result']['values']==[0,1] and not q['partial_result']['identified'] for r in records for q in r['queries'])
    assert all(set(r['operative_edge_ids'])=={e['id'] for e in r['representation']['edges']} for r in records)


def test_inhibition_factual_zero_and_frozen_background(archive):
    mod,data=archive;r=mod.restore_models(next(r for r in data['records'] if r['case']=='bolton'))
    sc=r['scenarios'][0];ans=query(r['representation'],sc['family'],{'R':0})
    assert ans['worlds'][0]['factual']['H']==0 and ans['worlds'][0]['counterfactual']['H']==1
    for v in r['representation']['variables']:
        if v['boundary']=='fixed_context':assert ans['worlds'][0]['factual'][v['id']]==ans['worlds'][0]['counterfactual'][v['id']]


def test_renderer_refuses_hidden_operative_edge_and_false_answer(archive,tmp_path):
    mod,data=archive;r=mod.restore_models(data['records'][0]);r['displayed_edge_ids'].pop()
    with pytest.raises(ValueError,match='silently withheld'):graph(r,tmp_path/'bad',1)
    r=mod.restore_models(data['records'][0]);r['queries'][0]['conditional'][0]['result']['values']=[7]
    with pytest.raises(ValueError,match='disagrees'):render_case(tmp_path,r,0)


def test_display_hash_covers_functions_and_questions(archive):
    mod,data=archive;r=mod.restore_models(data['records'][0]);old=model_hash(r)
    r['scenarios'][0]['typed_expressions']['Y']={'op':'const','value':0}
    assert old!=model_hash(r)
