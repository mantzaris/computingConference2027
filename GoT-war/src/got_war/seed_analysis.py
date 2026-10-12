"""Descriptive repeated-seed analysis without multiplying independent units."""
import collections,json
from pathlib import Path
import numpy as np
from .budget import atomic_json
from .evaluation import score,ci


def analyze(root):
    root=Path(root);run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
    plan=json.loads((root/'configs/seed_robustness.json').read_text())
    cases={c['id']:c for c in map(json.loads,(root/'benchmark/cases.jsonl').read_text().splitlines())}
    records={};missing=[]
    for ident in plan['scm_ids']:
        for seed in plan['seeds']:
            path=run/'benchmark'/(ident+'_v0_s%d.json'%seed)
            if path.exists():records[(ident,seed)]=json.loads(path.read_text())
            else:missing.append({'scm_id':ident,'seed':seed})
    values={};by_seed=[]
    for seed in plan['seeds']:
        selected=[r for (ident,s),r in records.items() if s==seed]
        for method in ('B0','B1','B2','P'):
            for r in selected:values[(r['scm_id'],seed,method)]=score(cases[r['id']],r['methods'].get(method,{}))['score']
            numbers=[values[(r['scm_id'],seed,method)] for r in selected]
            by_seed.append({'seed':seed,'method':method,'scms':len(numbers),'mean_score':float(np.mean(numbers)) if numbers else None})
    full=[ident for ident in plan['scm_ids'] if all((ident,seed) in records for seed in plan['seeds'])]
    method_ranges=[]
    for method in ('B0','B1','B2','P'):
        ranges=[max(values[(ident,s,method)] for s in plan['seeds'])-min(values[(ident,s,method)] for s in plan['seeds']) for ident in full]
        method_ranges.append({'method':method,'scms_with_all_seeds':len(full),'mean_within_scm_score_range':float(np.mean(ranges)) if ranges else None,'changed_scms':sum(x>0 for x in ranges)})
    paired=[]
    for left,right in [('P','B0'),('B2','B0'),('P','B2')]:
        differences=[float(np.mean([values[(ident,s,left)]-values[(ident,s,right)] for s in plan['seeds']])) for ident in full]
        paired.append({'comparison':left+'-'+right,'independent_scms':len(full),'seed_averaged_difference':float(np.mean(differences)) if differences else None,'scm_bootstrap_ci':ci(differences)})
    result={'selection':plan['selection'],'planned_scms':len(plan['scm_ids']),'seeds':plan['seeds'],
        'planned_records':len(plan['scm_ids'])*len(plan['seeds']),'completed_records':len(records),'missing':missing,
        'fully_repeated_scms':len(full),'by_seed':by_seed,'within_scm_variation':method_ranges,'paired_seed_averages':paired,
        'validity_by_seed':[{'seed':s,'records':sum(seed==s for ident,seed in records),'initial_valid':sum(bool(r['attempts'] and r['attempts'][0].get('valid')) for (ident,seed),r in records.items() if seed==s),'eventual_valid':sum('model' in r['methods'].get('B2',{}) for (ident,seed),r in records.items() if seed==s)} for s in plan['seeds']],
        'interpretation':'Predeclared balanced original-text subset. Repeated seeds remain observations of the same SCM; primary held-out comparisons use seed 2027 and both text variants only. Subset estimates are sensitivity analyses, not additional independent validation.'}
    atomic_json(root/'results/seed_robustness_summary.json',result)
    return result
