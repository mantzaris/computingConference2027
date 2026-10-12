from got_war.v2.analysis import score_answers, ndcg, interval, structural_scores
from got_war.v2.benchmark import generate
from got_war.v2.experiments import validate


def queries():
    return [{'id':'a','identified':True,'changed':True,'gold_possible':[0]},
            {'id':'b','identified':True,'changed':False,'gold_possible':[1]},
            {'id':'c','identified':False,'changed':None,'gold_possible':[0,1]}]


def test_failure_remains_in_primary_denominator_and_uncertainty_is_separate():
    metrics,_=score_answers({},queries())
    assert metrics['identified_correct']==0 and metrics['uncertainty_appropriate']==0
    point,_=score_answers({'answers':[{'id':q['id'],'values':[1]} for q in queries()]},queries())
    assert point['changed_correct']==0 and point['unchanged_correct']==1
    assert point['unsupported_confident']==2/3 and point['uncertainty_appropriate']==0
    abstain,_=score_answers({'answers':[{'id':q['id'],'values':[],'abstain':True} for q in queries()]},queries())
    assert abstain['identified_correct']==0 and abstain['uncertainty_appropriate']==1


def test_ranking_unavailable_is_zero_only_when_relevance_exists():
    assert ndcg([],{'a':2,'b':0})==0
    assert ndcg([],{'a':0}) is None
    assert ndcg(['a'],{'a':2,'b':0})==1
    assert ndcg(['b','a'],{'a':2,'b':0})<1


def test_cluster_summary_is_mean_over_scms_not_questions():
    summary=interval([0,1,None])
    assert summary['estimate']==.5 and summary['scms']==2


def test_function_score_cannot_credit_different_truth_table():
    model,_,_,_=generate(8,278000,'complete')
    case={'gold':model,'hidden_nodes':[]}
    record={'model':model,'synthesis_attempts':[{'valid':True}]}
    assert structural_scores(record,case)['known_function_agreement']==1
    import copy
    wrong=copy.deepcopy(model)
    # Both functions fit the factual row; factual fit alone must not earn equivalence.
    node=wrong['nodes'][-1]
    assert node['observed']==1
    node['expr']={'op':'or','args':[{'op':'not','args':[{'ref':node['parents'][0]}]},{'ref':node['parents'][1]}]}
    record['model']=wrong
    assert structural_scores(record,case)['known_function_agreement']<1
