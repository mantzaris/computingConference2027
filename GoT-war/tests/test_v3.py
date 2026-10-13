"""Behavioral tests for partial mechanisms, not tests of literary validity."""
import copy
import itertools as it
import json
import pytest
from got_war.v3.core import (build_family, check_claims, display_gate, fingerprint,
    informative, local_family, locate, predicate, query, revision_record, solve,
    validate_representation)
from got_war.v3.core import verify_reported_result


def fixture():
    text='The switch is on and the device runs. No other configurations are specified.'
    p={'segments':[{'id':'s1','text':text,'url':'test://s1','episode':'test','start':0,'end':len(text)}], 'packet_sha256':'test'}
    ref={'passage_id':'s1','quote':'The switch is on','supports':'Establishes the factual input, not a universal rule.'}
    def node(k, boundary, factual):
        return {'id':k,'label':k+' state','definition':k+' equals one when present','actor':'test device','domain':[0,1],
            'factual':factual,'kind':'narrative_fact','event_time':0 if k=='S' else 1,'statement_time':1,'time_note':'test stages',
            'event_status':'explicit','boundary':boundary,'boundary_reason':'Declared test scope','evidence':[ref]}
    edge={'id':'e1','parent':'S','child':'Y','label':'Supplies operating current','process':'The switch supplies current that may permit device operation.',
        'participants':['switch','current'],'conditions':[],'qualifications':['Unknown operation when off'],
        'evidence':[ref],'contradictions':[],'gaps':['Off behavior missing'],'status':'hypothetical',
        'endpoint_support':{'parent':'observed','child':'observed'},'temporal_status':'consistent','information_status':'consistent',
        'structural_implications':[],'alternatives':[]}
    rep={'outcome':'Y','variables':[node('S','fixed_context',1),node('Y','endogenous',1)],'edges':[edge],
        'mechanisms':[{'id':'mY','child':'Y','parents':['S'],'description':'Operation may depend on switching, with off behavior unresolved.',
            'joint_description':'','evidence':[ref],'assumptions':[],'gaps':['Unknown off row']}],'gaps':[]}
    rep=validate_representation(rep,p)
    functional={'functions':[{'child':'Y','background':[],'scope_status':'declared_family','scope_assumptions':['Finite deterministic scope for test'],
        'constraints':[{'id':'f1','kind':'row','when':{'S':1},'allowed':[1],'basis':'evidence','rationale':'Observed local row','evidence':[ref]}]}]}
    return rep,functional,p


def test_unknown_row_survives_and_modularity():
    r,f,p=fixture();fam=build_family(r,f,p)
    assert fam['local']['Y']['tables']==[[0,1],[1,1]]
    signature=fingerprint(fam)
    assert query(r,fam,{'S':0})['values']==[0,1]
    assert not query(r,fam,{'S':0})['identified']
    assert query(r,fam,{'Y':0})['values']==[0]
    assert query(r,fam,{})['values']==[1]
    assert fingerprint(fam)==signature


def test_no_active_parent_requirement():
    r,f,p=fixture();fam=build_family(r,f,p)
    assert [1,1] in fam['local']['Y']['tables']


def test_omitted_known_factual_constraint_is_rejected_not_silently_completed():
    r,f,p=fixture();f['functions'][0]['constraints']=[]
    with pytest.raises(ValueError,match='Known factual row not enforced'):build_family(r,f,p)
    # With no established child observation, all four functions remain possible.
    r['variables'][1]['factual']=None
    assert len(build_family(r,f,p)['models'])==4


def test_multiple_missing_intermediate_functions():
    r,f,p=fixture();z=copy.deepcopy(r['variables'][-1]);z.update(id='Z',event_time=2)
    r['variables'].append(z);r['outcome']='Z';e=copy.deepcopy(r['edges'][0]);e.update(id='e2',parent='Y',child='Z');r['edges'].append(e)
    m=copy.deepcopy(r['mechanisms'][0]);m.update(id='mZ',child='Z',parents=['Y']);r['mechanisms'].append(m)
    r=validate_representation(r,p)
    fn=copy.deepcopy(f['functions'][0]);fn['child']='Z';fn['constraints'][0]['when']={'Y':1};f['functions'].append(fn)
    fam=build_family(r,f,p);assert len(fam['models'])==4
    assert query(r,fam,{'S':0})['values']==[0,1]
    assert query(r,fam,{'Z':0})['values']==[0]


def test_sampling_never_certifies_identification():
    r,f,p=fixture();fam=build_family(r,f,p,max_tables=1,max_models=1)
    assert not fam['exhaustive']
    assert query(r,fam,{})['status']=='observed_sample'
    assert not query(r,fam,{})['identified']


def test_empty_sample_not_inconsistency_certificate():
    r,f,p=fixture();nodes={v['id']:v for v in r['variables']};m=dict(f['functions'][0],parents=['S'])
    m['constraints'].append({'id':'a','kind':'changes','parent':'S','low':0,'high':1,'when':{},'sign':'negative','basis':'assumption','rationale':'deliberately incompatible','evidence':[]})
    x=local_family(m,nodes,max_tables=0,sample_draws=0)
    assert not x['tables'] and x['coverage']=='sampled'
    assert 'not an impossibility proof' in x['empty_means']


def test_certified_inconsistent_constraints():
    r,f,p=fixture();f['functions'][0]['constraints'].append({'id':'bad','kind':'row','when':{'S':1},'allowed':[0],
        'basis':'assumption','rationale':'conflicting test assumption','evidence':[]})
    fam=build_family(r,f,p);assert fam['coverage']=='inconsistent' and not fam['models']


def test_description_counterexample_is_concrete():
    r,f,p=fixture();fam=build_family(r,f,p)
    claim={'record_id':'e1','child':'Y','text':'The switch is necessary',
        'predicate':{'kind':'necessary','when':{'S':1},'output':1}}
    check=check_claims(r,fam,[claim])[0]
    assert check['status']=='contradicted_by_candidate'
    assert check['counterexamples'][0]['counterexample']=={'inputs':{'S':0},'output':1}


def test_and_function_does_not_make_each_input_sufficient():
    names=['A','B'];rows=list(it.product([0,1],repeat=2));vals=[0,0,0,1]
    ok,w=predicate({'kind':'row','when':{'A':1},'allowed':[1]},names,rows,vals)
    assert not ok and w['inputs']=={'A':1,'B':0} and w['output']==0
    assert predicate({'kind':'necessary','when':{'A':1},'output':1},names,rows,vals)[0]


def test_existential_help_is_not_monotonicity():
    names=['A','B'];rows=list(it.product([0,1],repeat=2));vals=[0,1,1,0]
    c={'kind':'changes','parent':'A','low':0,'high':1,'when':{},'sign':'positive'}
    assert predicate(c,names,rows,vals)[0]
    assert not predicate(dict(c,kind='monotone'),names,rows,vals)[0]


def test_provenance_never_normalizes_a_fabricated_quote():
    r,f,p=fixture();ps={x['id']:x for x in p['segments']}
    with pytest.raises(ValueError):locate({'passage_id':'s1','quote':'The switch caused the outcome','supports':'invented'},ps)
    got=locate({'passage_id':'s1','quote':'The switch is on','supports':'factual'},ps)
    assert p['segments'][0]['text'][got['start']:got['end']]=='The switch is on'
    assert got['entailment']=='not certified by literal matching'


@pytest.mark.parametrize('label',['and','if','or','','influences','causes'])
def test_generic_edge_phrases_rejected(label):
    assert not informative(label)


def test_reviewer_cannot_audit_invented_ids_or_prose():
    r,f,p=fixture();fam=build_family(r,f,p)
    assert not display_gate(r,fam,{'records':[{'id':'instructions'}]})['review_valid']
    audit={'records':[{'id':k,'source_to_description':'unresolved','description_to_function':'consistent','formal_claims_complete':True,'label_specific':True} for k in ['e1','mY']],
        'claims':[{'record_id':'e1','child':'Y','text':'not an actual sentence','predicate':{'kind':'row','when':{},'allowed':[1]}}]}
    assert not display_gate(r,fam,audit)['review_valid']


def test_known_discrepancy_withholds_edge_without_rewriting():
    r,f,p=fixture();original=fingerprint(r);fam=build_family(r,f,p)
    audit={'records':[{'id':k,'source_to_description':'unresolved','description_to_function':'contradicted' if k=='mY' else 'consistent','formal_claims_complete':True,'label_specific':True} for k in ['e1','mY']], 'claims':[]}
    assert display_gate(r,fam,audit)['displayed_edges']==[]
    assert fingerprint(r)==original


def test_unknown_scope_keeps_partial_model_unexecutable():
    r,f,p=fixture();f['functions'][0]['scope_status']='unavailable'
    fam=build_family(r,f,p)
    assert fam['coverage']=='unavailable'
    assert fam['local']['Y']['unknown_rows']==[0]
    assert query(r,fam,{'S':0})['status']=='unavailable'


def test_revision_cannot_move_outcome_or_invent_evidence():
    r,f,p=fixture();new=copy.deepcopy(r);new['variables'][-1]['event_time']=3
    with pytest.raises(ValueError):revision_record(r,new,[],[],p)
    with pytest.raises(ValueError):revision_record(r,r,[{'kind':'mediator','reason':'because','evidence':[]}],[],p)


def test_chronology_is_not_support_and_future_edges_fail():
    r,f,p=fixture();r['variables'][0]['event_time']=2
    with pytest.raises(ValueError,match='Temporal counterexample'):validate_representation(r,p)


def test_evidence_constraint_requires_actual_reference():
    r,f,p=fixture();f['functions'][0]['constraints'][0]['evidence']=[]
    with pytest.raises(ValueError):build_family(r,f,p)


def test_result_check_rejects_wrong_numbers_and_sampling_claims():
    r,f,p=fixture();fam=build_family(r,f,p);answer=query(r,fam,{'S':0})
    assert verify_reported_result(r,fam,{'S':0},answer)['passed']
    wrong=dict(answer,values=[1],identified=True)
    assert not verify_reported_result(r,fam,{'S':0},wrong)['passed']
    sampled=build_family(r,f,p,max_tables=1,max_models=1);value=query(r,sampled,{})
    assert not verify_reported_result(r,sampled,{},dict(value,status='exhaustive_set',identified=True))['passed']


def test_unresolved_source_review_cannot_display_explicit_support():
    r,f,p=fixture();r['edges'][0]['status']='explicit';fam=build_family(r,f,p)
    audit={'records':[{'id':k,'source_to_description':'unresolved','description_to_function':'consistent','formal_claims_complete':True,'label_specific':True} for k in ['e1','mY']], 'claims':[]}
    gate=display_gate(r,fam,audit)
    assert gate['displayed_edges']==['e1'] and gate['display_status']['e1']=='unresolved'
    assert r['edges'][0]['status']=='explicit'


def test_fixed_background_is_reused_across_interventions():
    r,f,p=fixture();u=copy.deepcopy(r['variables'][0]);u.update(id='U',label='Background context',event_time=0)
    r['variables'].append(u);r=validate_representation(r,p)
    m=f['functions'][0];m['background']=['U']
    m['constraints']=[{'id':str(i),'kind':'row','when':when,'allowed':[out],
        'basis':'assumption','rationale':'Declared test equation','evidence':[]} for i,(when,out) in enumerate([
            ({'S':0},0),({'U':0},0),({'S':1,'U':1},1)])]
    fam=build_family(r,f,p);answer=query(r,fam,{'S':0})
    assert answer['values']==[0]
    assert all(w['factual']['U']==w['counterfactual']['U']==1 for w in answer['worlds'])
    with pytest.raises(ValueError,match='background parameters stay fixed'):query(r,fam,{'U':0})


def test_missing_root_is_not_automatically_factual_carry_forward():
    r,f,p=fixture();r['variables'][0]['boundary']='unresolved';r['variables'][0]['factual']=None
    r['variables'][1]['factual']=None
    r['mechanisms'].append({'id':'mS','child':'S','parents':[],'description':'Missing upstream process',
        'joint_description':'','evidence':[],'assumptions':[],'gaps':['upstream unknown']})
    r=validate_representation(r,p)
    f['functions'].append({'child':'S','background':[],'scope_status':'declared_family',
        'scope_assumptions':['Two possible fixed upstream states within this test scope'],'constraints':[]})
    fam=build_family(r,f,p)
    assert len(fam['local']['S']['tables'])==2 and query(r,fam,{})['factual_values']==[0,1]


def test_bounded_revision_loop_retains_original_and_counterexample(tmp_path):
    from got_war.v3.pipeline import MechanismFirst
    r,f,p=fixture();r['edges'][0]['process']='The switch is necessary for successful device operation.'
    repaired=copy.deepcopy(r)
    repaired['edges'][0]['process']='The switch may supply current, while operation without it remains unresolved.'
    records=[{'id':k,'source_to_description':'unresolved','description_to_function':'consistent',
              'formal_claims_complete':True,'label_specific':True,'reason':'Scripted test reviewer, not an LLM judgment'} for k in ['e1','mY']]
    bad_audit={'records':records,'claims':[{'record_id':'e1','child':'Y',
        'text':r['edges'][0]['process'],'predicate':{'kind':'necessary','when':{'S':1},'output':1}}]}
    responses={'propositions':r,'diagnosis':{'issues':[],'retrieval_questions':['device switch operation'],'revision_needed':False},
        'functions':f,'audit':bad_audit,'consistency_repair':{'representation':repaired,'functions':f['functions'],
            'operations':[{'kind':'clarify','reason':'Only the factual row is given; the claim of necessity overstates it.',
                           'evidence':[r['edges'][0]['evidence'][0]]}]},
        'audit_after_repair':{'records':records,'claims':[]}}
    class Scripted:
        def __init__(self):self.calls=[]
        def call(self,stage,prompt,limit,**kwargs):
            self.calls.append(stage)
            if stage=='consistency_repair':assert 'counterexample' in prompt and 'candidate' in prompt
            return copy.deepcopy(responses[stage])
    gen=Scripted();case={'id':'test','outcome':r['variables'][1]['definition']}
    result=MechanismFirst(gen,case,p,tmp_path).run()
    assert gen.calls.count('consistency_repair')==1
    assert result['display_gate']['displayed_edges']==['e1']
    assert len(result['family']['models'])==2
    assert json.loads((tmp_path/'propositions.json').read_text())['accepted']['edges'][0]['process']==r['edges'][0]['process']
    assert json.loads((tmp_path/'gate_initial.json').read_text())['formal_claims'][0]['status']=='contradicted_by_candidate'
    assert result['revisions'][0]['before_sha256']!=result['revisions'][0]['after_sha256']


def test_compiler_does_not_accept_unsigned_monotonicity():
    r,f,p=fixture();f['functions'][0]['constraints'].append({'id':'bad','kind':'monotone','parent':'S',
        'low':0,'high':1,'when':{},'sign':'different','basis':'assumption','rationale':'invalid formal claim','evidence':[]})
    with pytest.raises(ValueError,match='Monotonicity'):build_family(r,f,p)


def test_explicit_bounds_certificate_does_not_depend_on_sample_agreement():
    r,f,p=fixture();fam=build_family(r,f,p);fam['exhaustive']=False
    all_values=query(r,fam,{'S':0})
    assert all_values['status']=='certified_set' and all_values['values']==[0,1]
    assert not all_values['identified'] and all_values['bounds']['outer']==[0,1]
    one_model=copy.deepcopy(fam);one_model['models']=one_model['models'][:1]
    assert query(r,one_model,{})['status']=='observed_sample'
    direct=query(r,one_model,{'Y':0})
    assert direct['status']=='certified_set' and direct['identified']
    assert 'replaces the target equation' in direct['certificate']


def test_failed_cases_stay_in_denominator_but_unrun_is_not_zero_accuracy():
    from got_war.v3.study import component_scores
    cfg={'cases':[{'id':'x','queries':[{'id':'q','gold':[0],'changing':True}]}]}
    results=component_scores(cfg,[{'case':'x','arm':'A','status':'failed'}])['cells']
    assert results[0]['set_accuracy']==0 and results[0]['synthesis_failed']==1
    assert results[1]['set_accuracy'] is None and results[1]['synthesis_failed'] is None


def test_confident_identification_is_separate_from_a_conditional_singleton():
    from got_war.v3.study import component_scores
    cfg={'cases':[{'id':'x','queries':[{'id':'q','gold':[0,1],'changing':None}]}]}
    rec={'case':'x','arm':'C','status':'executable','queries':[{'id':'q','result':{'status':'observed_sample','values':[1],'identified':False}}]}
    scores=component_scores(cfg,[rec])['cells'][2]
    assert scores['set_accuracy']==0 and scores['unsupported_identification_rate']==0 and scores['answer_coverage']==1
    rec['queries'][0]['result']['identified']=True
    assert component_scores(cfg,[rec])['cells'][2]['unsupported_identification_rate']==1
