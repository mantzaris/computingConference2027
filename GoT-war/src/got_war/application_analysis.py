"""Descriptive application audits; literary model predictions are never gold."""
import collections,csv,json
from pathlib import Path
from .budget import atomic_json
from .structural_programs import SCM,equation


def analyze(root):
    root=Path(root);run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
    summaries=[];catalog=[];comparisons=[];critique=[]
    alias_file=root/'results/source_alias_checks.json'
    alias_findings=json.loads(alias_file.read_text())['findings'] if alias_file.exists() else []
    for folder in sorted((run/'application').iterdir()):
        files=sorted(folder.glob('alternative_*.json'))
        if not files:continue
        records=[json.loads(p.read_text()) for p in files];principal=records[0]
        model=principal['model'];nodes=model['nodes'];edges=principal['edge_evidence']
        node_status=collections.Counter(n.get('event_assessment','unassessed') for n in nodes)
        edge_status=collections.Counter(e.get('status','unassessed') for e in edges.values())
        review_path=folder/'final_source_review.json'
        review=json.loads(review_path.read_text()) if review_path.exists() else {'status':'not run','audits':[]}
        for row in review['audits']:critique.append(dict(case=folder.name,**row))
        audits=[]
        for file in files:
            path=folder/('explanation_audit_'+file.stem.split('_')[-1]+'.json')
            if path.exists():audits.append(json.loads(path.read_text()))
        row={'case':folder.name,'principal_model':model['id'],'accepted_generations':len(records),
             'nodes':len(nodes),'edges':len(edges),'principal_figure_size_target_met':len(nodes)>=10,
             'initial_event_assessments':dict(node_status),'mechanism_assessments':dict(edge_status),
             'unsupported_mechanism_fraction':(edge_status['unsupported']+edge_status['unassessed'])/max(1,len(edges)),
             'raw_positive_scores_on_unsupported_mechanisms':sum(e.get('status','unassessed') in ('unsupported','unassessed') and e.get('raw_score',e.get('score',0))>0 for e in edges.values()),
             'positive_priority_segments':sum(s['priority']>0 for s in principal['evidence_priority']['segments']),
             'positively_supported_paths':sum(p['evidence_support']>0 for p in principal['evidence_priority']['paths']),
             'final_source_critique_status':review['status'],
             'final_event_support':dict(collections.Counter(r['event_support'] for r in review['audits'])),
             'contradicted_story_times':[r['id'] for r in review['audits'] if r['story_time']=='contradicted'],
             'reference_semantics_flags':[r['id'] for r in review['audits'] if r['reference_semantics']!='consistent'],
             'duplicate_event_flags':[{'id':r['id'],'duplicates':r['duplicates']} for r in review['audits'] if r.get('duplicates')],
             'parent_order_flags':[{'child':r['id'],'parents':r['parent_order_flags']} for r in review['audits'] if r.get('parent_order_flags')],
             'unresolved_parent_order_fields':review.get('unresolved_parent_order_fields',[]),
             'posthoc_unverified_alias_flags':[r for r in alias_findings if r['case']==folder.name],
             'explanations_audited':len(audits),'explanations_passing_automatic_check':sum(a.get('automatic_check_passed',False) for a in audits),
             'no_independent_human_review':True,'literary_counterfactual_gold_available':False}
        summaries.append(row)
        for record in records:
            for node in record['model']['nodes']:
                catalog.append({'case':folder.name,'alternative':record['model']['alternative'],'id':node['id'],'label':node['label'],'definition':node['definition'],
                    'type':node['type'],'domain':json.dumps(node.get('values',node.get('bounds',[0,1]))),'story_time':node['time'],
                    'observed':node['observed'],'reference':node['reference'],'reference_meaning':node['reference_meaning'],
                    'parents':';'.join(node['parents']),'equation':equation(node['expr']),'background_ids':';'.join(node.get('noise',[])),
                    'assumptions':json.dumps(node.get('assumptions',[])),'source_ids':';'.join(c['segment_id'] for c in node.get('citations',[]))})
        baseline_path=folder/'baselines.json'
        if baseline_path.exists():
            baseline=json.loads(baseline_path.read_text());qmap={q['id']:q for q in principal['queries']}
            scms=[SCM(r['model']) for r in records]
            for method,response in baseline['methods'].items():
                amap={a['id']:a for a in response.get('answers',[]) if isinstance(a,dict) and 'id' in a}
                for qid,q in qmap.items():
                    answer=amap.get(qid,{});values=answer.get('possible_outcome',[])
                    valid=isinstance(values,list) and bool(values) and all(v in (0,1) for v in values)
                    model_set=sorted({s.solve(interventions=q['intervention'])[s.model['outcome']] for s in scms})
                    comparisons.append({'case':folder.name,'method':method,'question':qid,'intervention':json.dumps(q['intervention'],sort_keys=True),
                        'baseline_possible_outcomes':json.dumps(sorted(set(values))) if valid else '',
                        'retained_model_outcomes':json.dumps(model_set),'baseline_explicit_uncertainty':valid and set(values)=={0,1},
                        'baseline_model_set_agreement':valid and sorted(set(values))==model_set,
                        'baseline_response_available':bool(answer),'interpretation':'Descriptive set agreement only; neither side is literary gold.'})
    def write(name,rows):
        with (root/'results'/name).open('w',newline='') as file:
            if rows:
                writer=csv.DictWriter(file,fieldnames=list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');writer.writeheader()
                writer.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
    write('variable_equation_catalog.csv',catalog);write('application_baseline_comparison.csv',comparisons);write('final_source_critique.csv',critique)
    result={'cases':summaries,'baseline_rows':len(comparisons),
        'interpretation':'Descriptive audits of generated hypotheses. Source critiques and explanation audits use the same primary model; they are neither independent human labels nor literary counterfactual validation.'}
    atomic_json(root/'results/application_audit_summary.json',result)
    return result


if __name__=='__main__':
    import sys
    print(json.dumps(analyze(sys.argv[1] if len(sys.argv)>1 else '.'),indent=2))
