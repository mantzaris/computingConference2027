import copy
import itertools
from got_war.structural_programs import SCM
from got_war.v2.benchmark import generate
from got_war.v2.mechanisms import compatible_family, inspect_mechanism, outcome_sets
from got_war.v2.explanations import deterministic_check, review, assign_sentence_ids
from got_war.v2.paths import game_report, edge_support


def toy(kind='and'):
    return {'outcome':'W','background':{'UA':{'type':'bool','observed':1},'UB':{'type':'bool','observed':1}},
        'nodes':[{'id':x,'label':x,'type':'bool','parents':[],'noise':['U'+x],'expr':{'noise':'U'+x},'observed':1,'reference':0,'time':0} for x in ('A','B')]+[
        {'id':'W','label':'outcome','type':'bool','parents':['A','B'],'noise':[],'expr':{'op':kind,'args':[{'ref':'A'},{'ref':'B'}]},'observed':1,'reference':0,'time':1}]}


def test_behavior_distinguishes_necessity_from_redundancy():
    conjunction=inspect_mechanism(SCM(toy()),'W')
    redundancy=inspect_mechanism(SCM(toy('or')),'W')
    assert conjunction['necessary_for_one']==[{'A':1},{'B':1}]
    assert conjunction['sufficient_for_one']==[]
    assert redundancy['necessary_for_one']==[]
    assert redundancy['sufficient_for_one']==[{'A':1},{'B':1}]
    assert conjunction['joint_enabling'] and redundancy['substitution']


def test_multiple_unknown_rules_jointly_include_true_interventions():
    model,hidden,family,_=generate(12,282306,'multiple_missing')
    assert len(hidden)==2 and family['summary']['exhaustive']
    assert family['summary']['retained_functionally_distinct']>1
    for alternative in family['models']:
        compiled=SCM(alternative)
        assert all(n['description']==inspect_mechanism(compiled,n['id'])['derived_description'] for n in alternative['nodes'])
    true=SCM(model)
    for node in model['nodes'][:-1]:
        intervention={node['id']:1-node['observed']}
        query={'id':'q','do':intervention,'target':model['outcome']}
        values=outcome_sets(family['models'],[query])[0]['values']
        assert true.solve(interventions=intervention)[model['outcome']] in values


def test_incomplete_intermediate_and_outcome_are_different_families():
    a,ha,_,_=generate(8,278100,'missing_intermediate')
    b,hb,_,_=generate(8,278200,'missing_outcome')
    assert a['outcome'] not in ha and hb==[b['outcome']]


def test_coalition_diagnostic_exposes_unanimity_and_substitution():
    paths=[['A','W'],['B','W']]
    conjunction=game_report(SCM(toy()),paths)
    redundancy=game_report(SCM(toy('or')),paths)
    assert conjunction['coalition_values']==[0,0,0,1]
    assert conjunction['all_paths_required']
    assert redundancy['coalition_values']==[0,1,1,1]
    assert redundancy['substitute_path_sets'] and not redundancy['all_paths_required']
    assert conjunction['phi']==redundancy['phi']==[.5,.5]  # Equal shares alone do not identify the game.


def test_supported_direction_survives_unknown_function_but_not_missing_time():
    model=toy()
    for node in model['nodes']:
        node.update(event_status='established',function_identification='unidentified',
                    event_audit={'event_time':'consistent','information_time':'consistent'})
    model['nodes'][-1]['influences']=[{'parent':p,'direction_status':'explicit','segments':['passage'],
        'temporal_status':'consistent','information_status':'consistent','contradictions':[]} for p in ('A','B')]
    assert edge_support(model)['A>W']['score']==1
    model['nodes'][0]['time']=None
    assert edge_support(model)['A>W']['score']==0
    assert edge_support(model)['B>W']['score']==1
    model['nodes'][-1]['influences'][1]['direction_status']='unsupported'
    assert edge_support(model)['B>W']['score']==0


def test_reviewer_cannot_pass_by_reviewing_instructions():
    class Fake:
        def call(self,*args,**kwargs):
            return {'reviews':[{'sentence_id':'INSTRUCTION','verdict':'supported','reason':'not an explanation sentence'}]}
    result=review(Fake(),[{'id':'S01','text':'An actual explanation sentence.'}],{})
    assert not result['reviewer_valid'] and len(result['failed_attempts'])==2


def test_sentence_ids_follow_actual_prose_not_model_supplied_chunks():
    sentences=assign_sentence_ids([{'text':'Path p1 contributes 0.5. The shares are tied.','numeric_claims':[]}])
    assert [s['id'] for s in sentences]==['S01','S02']
    assert sentences[0]['text']=='Path p1 contributes 0.5.'


def test_nonmonotone_game_minimal_coalitions_check_all_strict_subsets():
    model=toy('xor')
    model['background']['UC']={'type':'bool','observed':1}
    model['nodes'].insert(2,{'id':'C','label':'C','type':'bool','parents':[],'noise':['UC'],'expr':{'noise':'UC'},'observed':1,'reference':0,'time':0})
    target=model['nodes'][-1];target['parents'].append('C')
    target['expr']={'op':'xor','args':[{'op':'xor','args':[{'ref':'A'},{'ref':'B'}]},{'ref':'C'}]}
    report=game_report(SCM(model),[['A','W'],['B','W'],['C','W']])
    assert report['minimal_full_outcome_coalitions']==[[1],[2],[3]]
    assert report['negative_marginals']>0


def test_deterministic_explanation_rejects_wrong_number_and_unique_tie():
    record={'numbers':{'factual_outcome':1,'path_p1':.5,'path_p2':.5},'possible_outcomes':[0,1],
            'factual_states':{'A':1,'W':1},'paths':[{'path_id':'p1'},{'path_id':'p2'}],'largest_absolute_ties':['p1','p2']}
    result=deterministic_check([{'id':'S01','text':'The strongest path p1 contributes 0.9.'}],record)
    assert {e['type'] for e in result['errors']}=={'number_not_in_record','unqualified_largest_among_ties'}


def test_a_number_elsewhere_in_trace_does_not_validate_false_factual_claim():
    record={'numbers':{'factual_outcome':1,'single_model_counterfactual_outcome':0},'possible_outcomes':[0,1],
            'factual_states':{'V00':1,'V07':1},'paths':[],'largest_absolute_ties':[],
            'query':{'target':'V07'},'outcome_label':'Station V07'}
    result=deterministic_check([{'id':'S01','text':'The factual outcome is 0 after V99 acts.'}],record)
    assert {e['type'] for e in result['errors']}=={'unknown_variable','outcome_value_mismatch'}


def test_generated_categorical_table_compilation_and_review_encoding_are_lossless():
    from got_war.v2.application import reduced_expression,behavior_view
    from got_war.v2.mechanisms import table_expression
    from got_war.structural_programs import evaluate
    domains=[['low','middle','high'],[0,1]];outputs=[0,1,0,0,1,1]
    expression=reduced_expression(table_expression(['A','B'],domains,outputs))
    assert [evaluate(expression,dict(zip(['A','B'],x)),{}) for x in itertools.product(*domains)]==outputs
    model=toy();model['nodes'][0].update(type='category',values=domains[0],observed='high',reference='low')
    model['background']['UA']={'type':'category','values':domains[0],'observed':'high'}
    model['nodes'][-1]['expr']=expression
    behavior=inspect_mechanism(SCM(model),'W');encoded=behavior_view(behavior)['behavior_table']
    decoded=[{'inputs':{n:d[c] for n,d,c in zip(encoded['input_order'],encoded['input_domains'],row)},
              'output':encoded['output_domain'][code]} for row,code in zip(encoded['input_rows'],encoded['output_codes'])]
    assert decoded==behavior['rows']


def test_a_dependency_retraction_cannot_hide_active_behavior():
    import pytest
    from got_war.v2.application import certify_retractions
    rows=list(itertools.product([0,1],repeat=2));outputs=[0,1,0,1]
    certify_retractions(['A','B'],rows,outputs,['A'])
    with pytest.raises(ValueError,match='still changes'):
        certify_retractions(['A','B'],rows,outputs,['B'])
def test_literal_operand_normalization_does_not_infer_category_predicates():
    from got_war.v2.application import literal_operands
    from got_war.structural_programs import evaluate
    expression={'op':'eq','args':[{'ref':'C'},'enabled']}
    normalized=literal_operands(expression,{'enabled','disabled'})
    assert evaluate(normalized,{'C':'enabled'}, {})==1
    assert evaluate(normalized,{'C':'disabled'}, {})==0
    assert expression['args'][1]=='enabled'
    assert literal_operands({'op':'and','args':[{'ref':'C'},1]}, {'enabled','disabled'})['args'][0]=={'ref':'C'}
    assert literal_operands('undeclared category',{'enabled','disabled'})=='undeclared category'

