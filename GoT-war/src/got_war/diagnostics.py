"""Descriptive error, ablation and repeated-text analysis of frozen generations."""
import collections,csv,hashlib,json
from pathlib import Path
import numpy as np
from .evaluation import score,ci
from .budget import atomic_json


def analyze(root):
    root=Path(root);run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
    cases={c['id']:c for c in map(json.loads,(root/'benchmark/cases.jsonl').read_text().splitlines())}
    units={c['scm_id']:c for c in cases.values()};splits=collections.defaultdict(set);programs=collections.defaultdict(list)
    for c in cases.values():splits[c['scm_id']].add(c['split'])
    for ident,c in units.items():
        program=[{k:n[k] for k in ('id','parents','expr')} for n in c['gold']['nodes']]
        programs[hashlib.sha256(json.dumps(program,sort_keys=True).encode()).hexdigest()].append(ident)
    profiles=[]
    for condition in ('complete','incomplete'):
        group=[c for c in units.values() if c['split']=='test' and c['condition']==condition]
        questions=[q for c in group for q in c['queries'] if q['kind'] in ('intervention','counterfactual','joint')]
        counts=collections.Counter(tuple(q['gold_possible']) for q in questions)
        identified=[(c,q) for c in group for q in c['queries'] if q['kind'] in ('intervention','counterfactual','joint') and q['identified']]
        unchanged=sum(q['gold_possible']==[next(n['observed'] for n in c['gold']['nodes'] if n['id']==q['target'])] for c,q in identified)
        profiles.append({'condition':condition,'test_scms':len(group),'structural_queries_per_scm':5,'identified_queries':len(identified),'ambiguous_queries':counts[(0,1)],'identified_zero_outcomes':counts[(0,)],'identified_one_outcomes':counts[(1,)],'identified_queries_equal_to_factual_outcome':unchanged,'factual_carry_forward_accuracy_on_identified_structural_queries':unchanged/len(identified) if identified else None,'interpretation':'Post-hoc dataset diagnostic, not a predeclared inference baseline; each SCM counted once.'})
    records=[json.loads(p.read_text()) for p in sorted((run/'benchmark').glob('*_s2027.json'))]
    test=[r for r in records if r['split']=='test'];rows=[];failures=[]
    for r in test:
        case=cases[r['id']]
        for method in ('B0','B1','B2','P'):
            prediction=r['methods'].get(method,{})
            for kind in sorted({q['kind'] for q in case['queries']}):
                subset=dict(case,queries=[q for q in case['queries'] if q['kind']==kind])
                rows.append({'scm_id':case['scm_id'],'case_id':case['id'],'condition':case['condition'],'size':case['size'],'kind':kind,'method':method,**score(subset,prediction)})
            if 'error' in prediction:failures.append({'case_id':case['id'],'method':method,'error':prediction['error']})
        if not r['methods'].get('B2',{}).get('model'):
            failures.append({'case_id':case['id'],'method':'B2/P','error':' | '.join(a.get('error','') for a in r['attempts'])})
    strata=[]
    for condition in ('complete','incomplete'):
        for kind in sorted({r['kind'] for r in rows}):
            for method in ('B0','B1','B2','P'):
                grouped=collections.defaultdict(list)
                for r in rows:
                    if (r['condition'],r['kind'],r['method'])==(condition,kind,method):grouped[r['scm_id']].append(r['score'])
                values=[float(np.mean(v)) for v in grouped.values()]
                if values:strata.append({'condition':condition,'query_kind':kind,'method':method,'scms':len(values),'mean':float(np.mean(values)),'ci_low':ci(values)[0],'ci_high':ci(values)[1]})
    def read(name):
        with open(root/'results'/name) as f:return list(csv.DictReader(f))
    ext=[r for r in read('extraction.csv') if r['split']=='test' and r['seed']=='2027']
    admitted=[r for r in ext if r['eventual_valid']=='True']
    extract={'test_texts':len(ext),'test_scms':len({r['scm_id'] for r in ext}),'initial_valid':sum(r['first_valid']=='True' for r in ext),'admissible':len(admitted)}
    for key in ('edge_precision','edge_recall','event_id_recall','source_reference_validity','specified_nonroot_function_agreement','unexplained_internal_backgrounds'):
        values=[float(r[key]) for r in admitted if r.get(key)]
        extract['admitted_mean_'+key]=float(np.mean(values)) if values else None
    paths=[r for r in read('path_diagnostics.csv') if r['split']=='test' and r['seed']=='2027']
    a2={'admitted_test_texts':len(paths),'nonzero_naive_residual':sum(abs(float(r['naive_residual']))>1e-10 for r in paths),
        'positive_naive_residual':sum(float(r['naive_sum'])>float(r['contrast'])+1e-10 for r in paths),
        'negative_naive_residual':sum(float(r['naive_sum'])<float(r['contrast'])-1e-10 for r in paths),
        'max_absolute_naive_residual':max((abs(float(r['naive_residual'])) for r in paths),default=0),
        'max_efficiency_residual':max((float(r['efficiency_residual']) for r in paths),default=0)}
    rank=[r for r in read('evidence_ranking.csv') if r['split']=='test' and r['seed']=='2027' and r['P_ndcg5'] and r['A1_ndcg5']]
    grouped=collections.defaultdict(list)
    for r in rank:grouped[r['scm_id']].append(float(r['P_ndcg5'])-float(r['A1_ndcg5']))
    differences=[float(np.mean(v)) for v in grouped.values()]
    a1={'eligible_test_texts':len(rank),'eligible_scms':len(grouped),'paired_ndcg5_difference':float(np.mean(differences)) if differences else None,'ci':ci(differences),
        'interpretation':'Known source-support labels conditional on generated influential paths; availability proxy, not independent causal-importance labels.'}
    paraphrases=[]
    for method in ('B0','B1','B2','P'):
        grouped=collections.defaultdict(dict)
        for r in test:grouped[r['scm_id']][r['variant']]=score(cases[r['id']],r['methods'].get(method,{}))['score']
        differences=[abs(v[0]-v[1]) for v in grouped.values() if set(v)=={0,1}]
        paraphrases.append({'method':method,'scms':len(differences),'mean_absolute_score_change':float(np.mean(differences)),'changed_scms':sum(d>0 for d in differences)})
    for name,data in [('query_strata.csv',strata),('generation_failures.csv',failures)]:
        with open(root/'results'/name,'w',newline='') as f:
            if data:w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    result={'dataset_integrity':{'independent_scm_ids':len(units),'distinct_structural_programs':len(programs),'cross_split_scm_ids':[i for i,v in splits.items() if len(v)>1],'duplicate_program_ids':[v for v in programs.values() if len(v)>1],'automated_only':True},'query_profile':profiles,'extraction':extract,'A1':a1,'A2':a2,'paraphrase_sensitivity':paraphrases,'primary_seed':2027,'selection_warning':'Admitted-only diagnostics condition on successful synthesis. Failure-inclusive query scores remain primary.'}
    atomic_json(root/'results/diagnostic_summary.json',result);return result


if __name__=='__main__':
    import sys
    print(json.dumps(analyze(sys.argv[1] if len(sys.argv)>1 else '.'),indent=2))
