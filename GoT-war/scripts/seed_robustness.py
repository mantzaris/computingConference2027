"""Predeclared balanced test subset; additional seeds are not independent SCMs."""
import json,requests
from pathlib import Path
from got_war.budget import Budget, atomic_json
from got_war.experiments import run_case

root=Path.cwd();budget=Budget(root)
cases=[json.loads(line) for line in (root/'benchmark/cases.jsonl').read_text().splitlines()]
selected=[]
for size in (12,18,24):
    for condition in ('complete','incomplete'):
        group=sorted((c for c in cases if c['split']=='test' and c['variant']==0 and c['size']==size and c['condition']==condition),key=lambda c:c['scm_id'])
        selected.extend(group[:2])
manifest={'scm_ids':[c['scm_id'] for c in selected],'seeds':[2027,2028,2029],
          'selection':'First two test SCM identifiers in each size/evidence stratum; original text only; no outcome-based selection.',
          'inference_prompts':'Unchanged primary controlled prompts; only decoding seeds vary.',
          'experimental_unit':'Generating SCM; seed and text variants are repeated observations.'}
atomic_json(root/'configs/seed_robustness.json',manifest)
# Do not displace either core experiment with optional repetitions.
missing=[c['id'] for c in cases if not (budget.run/'benchmark'/(c['id']+'_s2027.json')).exists()]
if missing:raise RuntimeError('Core benchmark incomplete: %d texts'%len(missing))
if not all(list((budget.run/'application'/case).glob('alternative_*.json')) for case in ('five_kings','northern_campaign','daenerys_conquest')):
    raise RuntimeError('Core application networks not ready')
budget.check(heavy=True,estimated_seconds=24*5*45,reserve_seconds=5*3600)
completed=[];skipped=[]
for seed in (2028,2029):
    for case in selected:
        # A whole record has at most B0 + three synthesis attempts + B1.
        # Stop before starting a record whose worst-case output will not fit.
        metrics=requests.get('http://127.0.0.1:8765/metrics',timeout=10).text
        used=sum(float(line.rsplit(' ',1)[1]) for line in metrics.splitlines() if line.startswith('vllm:generation_tokens_total'))
        if used+16384+16384+12000>budget.config['output_token_ceiling']:
            skipped.append({'seed':seed,'case':case['id'],'reason':'Whole-record output ceiling plus concurrent-stream and final-audit reserve','server_output_tokens':used})
            atomic_json(budget.run/'seed_robustness_progress.json',{'completed':completed,'skipped':skipped})
            continue
        print('SEED',seed,case['id'],flush=True)
        run_case(root,case,seed)
        completed.append({'seed':seed,'case':case['id']})
        atomic_json(budget.run/'seed_robustness_progress.json',{'completed':completed,'skipped':skipped})
atomic_json(budget.run/'seed_robustness_complete.json',dict(manifest,completed=completed,skipped=skipped,all_planned_completed=not skipped))
