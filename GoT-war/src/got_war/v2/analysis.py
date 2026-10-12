"""Frozen component scoring; independent generating SCMs are the resampling units."""
import collections
import csv
import itertools
import json
import math
from pathlib import Path
import numpy as np
from ..budget import atomic_json
from ..structural_programs import SCM, evaluate
from .runtime import paths

METHODS=('B0','B1','B2','ALT','FULL','CARRY','ORACLE_FAMILY','ORACLE_TRUE')
BOOTSTRAP_SEED=271828
BOOTSTRAP_REPLICATES=5000


def interval(values):
    values=np.asarray([x for x in values if x is not None],dtype=float)
    if not len(values):return {'estimate':None,'lower':None,'upper':None,'scms':0}
    rng=np.random.default_rng(BOOTSTRAP_SEED)
    draws=values[rng.integers(0,len(values),(BOOTSTRAP_REPLICATES,len(values)))].mean(axis=1)
    lo,hi=np.quantile(draws,[.025,.975])
    return {'estimate':float(values.mean()),'lower':float(lo),'upper':float(hi),'scms':len(values)}


def mean(values):
    values=list(values)
    return sum(values)/len(values) if values else None


def parse_answers(output, queries):
    """Duplicates, missing IDs and malformed values fail, rather than disappearing."""
    rows=output.get('answers',[]) if isinstance(output,dict) else []
    known={q['id'] for q in queries};collected=collections.defaultdict(list)
    if isinstance(rows,list):
        for row in rows:
            if isinstance(row,dict) and row.get('id') in known:collected[row['id']].append(row)
    result={}
    for ident in known:
        matches=collected[ident]
        if len(matches)!=1:result[ident]=None;continue
        row=matches[0];values=row.get('values');abstain=row.get('abstain',False)
        if not isinstance(values,list) or any(type(v) not in (int,bool) or v not in (0,1) for v in values) or not isinstance(abstain,bool):
            result[ident]=None;continue
        values=sorted(set(values))
        result[ident]={'values':values,'abstain':abstain} if values or abstain else None
    return result


def score_answers(output, queries):
    answers=parse_answers(output,queries);rows=[]
    for q in queries:
        answer=answers[q['id']];valid=answer is not None
        singleton=valid and not answer['abstain'] and len(answer['values'])==1
        exact=valid and not answer['abstain'] and answer['values']==q['gold_possible']
        uncertainty=valid and (answer['abstain'] or len(answer['values'])>1)
        unsupported=singleton and (not q['identified'] or answer['values']!=q['gold_possible'])
        rows.append({'query':q['id'],'identified':q['identified'],'changed':q['changed'],
            'valid_answer':int(valid),'identified_correct':int(exact) if q['identified'] else None,
            'changed_correct':int(exact) if q['changed'] is True else None,
            'unchanged_correct':int(exact) if q['changed'] is False else None,
            'uncertainty_appropriate':int(uncertainty) if not q['identified'] else None,
            'exact_outcome_set':int(exact),'unsupported_confident':int(unsupported)})
    metrics={k:mean(r[k] for r in rows if r[k] is not None) for k in rows[0] if k not in ('query','identified','changed')}
    metrics['eligible_questions']={k:sum(r[k] is not None for r in rows) for k in metrics}
    return metrics,rows


def ndcg(ranking, relevance, k=5):
    """Unavailable rankings score zero when the independent gold has a relevant item."""
    ideal=sorted(relevance.values(),reverse=True)[:k]
    denominator=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(ideal))
    if not denominator:return None
    if not isinstance(ranking,list):return 0.
    # Invalid/duplicate items occupy a rank but gain nothing.
    seen=set();numerator=0.
    for i,ident in enumerate(ranking[:k]):
        gain=relevance.get(ident,0) if isinstance(ident,str) and ident not in seen else 0
        if isinstance(ident,str):seen.add(ident)
        numerator+=(2**gain-1)/math.log2(i+2)
    return numerator/denominator


def structural_scores(record,case):
    model=record.get('model');gold=case['gold'];gold_nodes={n['id']:n for n in gold['nodes']}
    # Root identity/background assignments are scored as factual grounding;
    # functional agreement concerns the substantive known endogenous rules.
    known=[n for n in gold['nodes'] if n['parents'] and n['id'] not in case['hidden_nodes']]
    scores={'synthesis_first':int(bool(record.get('synthesis_attempts')) and record['synthesis_attempts'][0].get('valid',False)),
        'synthesis_after_repair':int(bool(model)),'known_function_agreement':0.,'unknown_flag_accuracy':0.,
        'direction_precision':0.,'direction_recall':0.,'direction_grounding':0.,'event_state_agreement':0.}
    if not model:return scores
    scm=SCM(model);matches=[]
    for true in known:
        node=scm.nodes[true['id']];parents=sorted(set(true['parents'])|set(node['parents']))
        same=True
        for values in itertools.product((0,1),repeat=len(parents)):
            state=dict(zip(parents,values))
            a=evaluate(true['expr'],state,{u:v['observed'] for u,v in gold['background'].items()})
            b=evaluate(node['expr'],state,scm.u)
            if a!=b:same=False;break
        matches.append(same)
    expected={(p,n['id']) for n in gold['nodes'] for p in n['parents']}
    proposed={(p,n['id']) for n in model['nodes'] for p in n['parents']}
    supported=[]
    for node in model['nodes']:
        for edge in node.get('influences',[]):
            supported.append((edge['parent'],node['id']) in expected and 'seg_'+node['id'] in edge.get('segments',[]) and edge.get('direction_status')=='explicit')
    scores.update(known_function_agreement=mean(matches),
        unknown_flag_accuracy=mean(bool(n.get('unknown'))==(n['id'] in case['hidden_nodes']) for n in model['nodes']),
        direction_precision=len(expected&proposed)/len(proposed) if proposed else 0.,
        direction_recall=len(expected&proposed)/len(expected) if expected else 1.,
        direction_grounding=mean(supported) if supported else 0.,
        event_state_agreement=mean(n['observed']==gold_nodes[n['id']]['observed'] for n in model['nodes']))
    return scores


def explanation_scores(record):
    explanation=record.get('explanation',{});controls=record.get('reviewer_controls',{})
    reviewed={r['sentence_id']:r['verdict'] for r in controls.get('review',{}).get('reviews',[])}
    expected=controls.get('expected',{'S01':'supported','S02':'unsupported','S03':'unsupported','S04':'supported'})
    return {'explanation_generated':int(bool(explanation.get('sentences'))),
        'explanation_deterministic_pass':int(explanation.get('deterministic_check',{}).get('passed',False)),
        'reviewer_valid_ids':int(explanation.get('review',{}).get('reviewer_valid',False)),
        'explanation_same_model_supported':int(explanation.get('review',{}).get('all_supported',False)),
        'explanation_displayable':int(explanation.get('displayable',False)),
        'reviewer_control_accuracy':mean(reviewed.get(k)==v for k,v in expected.items()),
        'reviewer_control_false_acceptance':mean(reviewed.get(k)=='supported' for k,v in expected.items() if v=='unsupported'),
        'reviewer_control_missing':mean(k not in reviewed for k in expected)}


def analyze(root,split='test'):
    root,run,result=paths(root)
    cases=[json.loads(s) for s in (run/'benchmark_cases.jsonl').read_text().splitlines()]
    cases=[c for c in cases if c['split']==split];records={}
    for c in cases:
        f=run/'benchmark'/(c['id']+'.json')
        records[c['id']]=json.loads(f.read_text()) if f.exists() else {}
    measurements=[];questions=[];components=[];ranking=[]
    for case in cases:
        record=records[case['id']];metadata={k:case[k] for k in ('id','condition','size','split')}
        scores=structural_scores(record,case)
        components.append(dict(metadata,**scores,**explanation_scores(record),model_available=bool(record.get('model')),
            elapsed_seconds=record.get('elapsed_seconds'),stage_failures=record.get('stage_failures',[])))
        for method in METHODS:
            if method.startswith('ORACLE') or method=='CARRY':
                output={'answers':[{'id':q['id'],'values':q['gold_possible'] if method=='ORACLE_FAMILY' else
                    [q['factual'] if method=='CARRY' else q['generating_outcome']],'abstain':False} for q in case['queries']]}
            else:output=record.get('methods',{}).get(method,{})
            metric,detail=score_answers(output,case['queries'])
            measurements.append(dict(metadata,method=method,**metric,model_available=bool(record.get('model'))))
            questions.extend(dict(metadata,method=method,**r) for r in detail)
        selected=case['queries'][case['seed']%len(case['queries'])]
        for method in ('B0','B1','FULL','UNIFORM'):
            output=record.get('methods',{}).get(method,{})
            score=ndcg(output.get('ranked_sources',[]),selected['relevance'])
            ranking.append(dict(metadata,method=method,query=selected['id'],ndcg_at_5=score,
                ranking_available=bool(output.get('ranked_sources')),independent_positive_labels=sum(v>0 for v in selected['relevance'].values())))
    metrics=[k for k in measurements[0] if k not in ('id','condition','size','split','method','eligible_questions','model_available')]
    tables=[]
    for condition in ('all','complete','incomplete','missing_intermediate','missing_outcome','multiple_missing'):
        group=[r for r in measurements if condition=='all' or r['condition']==condition or condition=='incomplete' and r['condition']!='complete']
        for method in METHODS:
            rows=[r for r in group if r['method']==method]
            tables.append({'condition':condition,'method':method,'metrics':{m:interval([r[m] for r in rows]) for m in metrics}})
    pairs=[]
    for left,right in (('B1','B0'),('B2','B0'),('ALT','B2'),('FULL','B0'),('FULL','CARRY')):
        a={r['id']:r for r in measurements if r['method']==left};b={r['id']:r for r in measurements if r['method']==right}
        pairs.append({'left':left,'right':right,'metrics':{m:interval([a[k][m]-b[k][m] for k in a if a[k][m] is not None and b[k][m] is not None]) for m in metrics}})
    components_summary={k:interval([r[k] for r in components]) for k in components[0] if k not in ('id','condition','size','split','model_available','elapsed_seconds','stage_failures')}
    rank_summary={method:interval([r['ndcg_at_5'] for r in ranking if r['method']==method]) for method in ('B0','B1','FULL','UNIFORM')}
    rank_by={method:{r['id']:r['ndcg_at_5'] for r in ranking if r['method']==method} for method in rank_summary}
    rank_pairs={method:interval([rank_by['FULL'][k]-v for k,v in rank_by[method].items() if v is not None and rank_by['FULL'][k] is not None]) for method in ('B0','B1','UNIFORM')}
    conditional={method:{m:interval([r[m] for r in measurements if r['method']==method and r['model_available']]) for m in metrics} for method in ('B2','ALT','FULL')}
    summary={'version':2,'split':split,'planned_scms':len(cases),'completed_records':sum(r.get('completed',False) for r in records.values()),
        'inference_unit':'One frozen generation seed per independent SCM; questions are repeated measurements.',
        'primary_denominator':'Every planned SCM, including failed synthesis and missing records. SCM means with no eligible questions omitted only for that stratum.',
        'uncertainty':{'method':'Paired nonparametric bootstrap of independent SCM means; percentile 95% intervals','replicates':BOOTSTRAP_REPLICATES,'seed':BOOTSTRAP_SEED,'multiplicity':'Descriptive intervals; no significance-seeking stopping or multiplicity-adjusted discovery claim.'},
        'tables':tables,'paired_differences':pairs,'components':components_summary,'source_priority':rank_summary,'source_priority_paired':rank_pairs,
        'successful_synthesis_only_secondary':conditional,
        'source_relevance_definition':'Gold query-specific causal-slice rule relevance, specified before inference; this is not human literary salience. No positive labels means ranking not evaluable. A missing/zero ranking with positive labels receives zero.',
        'oracle_caution':'ORACLE_FAMILY is an achievable-information ceiling supplied the declared compatible family. ORACLE_TRUE receives the hidden generating model and can overstate identification; it is only a diagnostic point-prediction oracle.',
        'explanation_caution':'Displayability combines deterministic checks and same-model review. Known reviewer controls test trace facts and interpretation only. Neither establishes independent narrative entailment.',
        'full_pipeline_caution':'FULL and ALT intentionally share outcome sets. FULL additionally produces attribution, evidence priorities and reviewed prose; each has its own measured component score.'}
    atomic_json(result/(split+'_summary.json'),summary)
    for name,rows in [('scm_scores',measurements),('query_scores',questions),('component_scores',components),('ranking_scores',ranking)]:
        dest=run/'analysis'/(split+'_'+name+'.json');atomic_json(dest,rows)
    # Compact per-SCM scores are the reproducible statistical input, not raw text.
    public=[]
    for row in measurements:
        public.append({k:v for k,v in row.items() if k!='eligible_questions'})
    with (result/(split+'_scm_scores.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(public[0]));writer.writeheader();writer.writerows(public)
    return summary


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--split',default='test');a=p.parse_args()
    result=analyze(a.root,a.split)
    print(json.dumps({'split':result['split'],'completed':result['completed_records'],'planned':result['planned_scms']}))
