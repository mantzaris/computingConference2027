#!/usr/bin/env python3
"""Recompute the historical headline checks without changing phase-one evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import subprocess

PROJECT=Path(__file__).resolve().parents[2]
REPO=PROJECT.parent
COMMIT='ad21e604ef37f65e20ce32d78b0c2d04a0737cd7'

def main():
    metrics=PROJECT/'results/curated/metrics.csv'
    with metrics.open() as stream:rows=list(csv.DictReader(stream))
    key=lambda r:tuple(r[c] for c in ['study','d','family','seed','budget','corruption','metadata_variant'])
    final=[r for r in rows if r['endpoint']=='T2' and r['stage']=='selected']
    controlled=[r for r in final if r['study']=='controlled' and float(r['corruption']) in (.2,.5)]
    fixed={key(r):float(r['sw1']) for r in controlled if r['method']=='fixed'}
    methods={m:[r for r in controlled if r['method']==m] for m in ['fixed','random','diagnostic']}
    means={m:statistics.mean(float(r['sw1']) for r in part) for m,part in methods.items()}
    updates={m:statistics.mean(float(r['canonical_optimizer_updates']) for r in part) for m,part in methods.items()}
    outcomes={}
    for stage in ['before_audit','selected']:
        part=[r for r in rows if r['endpoint']=='T2' and r['stage']==stage and
              r['study']=='controlled' and r['method']=='diagnostic' and float(r['corruption']) in (.2,.5)]
        counts={'beneficial':0,'neutral':0,'harmful':0}
        for r in part:
            base=fixed[key(r)];delta=float(r['sw1'])-base;threshold=max(.001,.05*base)
            counts['harmful' if delta>threshold else 'beneficial' if delta < -threshold else 'neutral']+=1
        outcomes[stage]=counts
    def paired_delta(study,reference,variant=None):
        part=[r for r in final if r['study']==study and (variant is None or r['metadata_variant']==variant)]
        comparison={key(r):float(r['sw1']) for r in part if r['method']==reference}
        return statistics.mean(float(r['sw1'])-comparison[key(r)] for r in part if r['method']=='diagnostic')
    ledger=PROJECT/'.artifacts/ledger_snapshot.sqlite'
    with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as book:
        intervals=sorted(book.execute('SELECT start,end FROM intervals'))
    if any(b is None for a,b in intervals):raise RuntimeError('Historical snapshot contains an open interval')
    seconds=0.;end=0.
    for a,b in intervals:seconds+=max(0.,b-max(a,end));end=max(end,b)
    changed=subprocess.check_output(['git','diff','--name-only',COMMIT,'--','sem-update/'],cwd=REPO,text=True).splitlines()
    changed=[p for p in changed if not p.startswith(('sem-update/phase2/','sem-update/src/sem_update/phase2/'))]
    llm=json.loads((PROJECT/'phase2/results/historical_llm_audit.json').read_text())
    record={'historical_commit':COMMIT,'method_runs':len({r['run_id'] for r in rows}),
        'datasets':len({r['data_id'] for r in rows}),'metric_rows':len(rows),
        'controlled_conditions':len(fixed),'controlled_T2_means':means,
        'canonical_fitting_updates':updates,'diagnostic_repair_outcomes':outcomes,
        'semantic_all_metadata_diagnostic_minus_llm':paired_delta('semantic','llm_edit'),
        'semantic_coherent_diagnostic_minus_llm':paired_delta('semantic','llm_edit','coherent'),
        'real_coherent_diagnostic_minus_fixed':paired_delta('real','fixed','coherent'),
        'historical_device_hours':seconds/3600,'historical_tracked_changes':changed,
        'metrics_sha256':hashlib.sha256(metrics.read_bytes()).hexdigest(),
        'ledger_snapshot_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest(),
        'LLM_valid_new_edits':llm['counts']['valid_new_edits'],
        'scope':'Read-only recomputation of recorded headline values; original uncertainty estimates and raw-file verification are retained separately'}
    checks={'869_runs':record['method_runs']==869,'66_datasets':record['datasets']==66,
        '120_controlled_conditions':len(fixed)==120,
        'controlled_means':all(abs(means[m]-v)<1e-8 for m,v in
            [('fixed',.1774175682),('random',.1475192564),('diagnostic',.09926660894)]),
        'ten_harmful_before_and_after':all(v['harmful']==10 for v in outcomes.values()),
        'diagnostic_used_more_updates':updates['diagnostic']>updates['random'],
        'semantic_and_real_worsened':record['semantic_coherent_diagnostic_minus_llm']>0 and record['real_coherent_diagnostic_minus_fixed']>0,
        'GPU_usage':abs(seconds/3600-10.318524638083247)<1e-8,
        'no_admissible_LLM_edits':record['LLM_valid_new_edits']==0,
        'historical_tracked_files_unchanged':not changed}
    record.update(checks=checks,passed=all(checks.values()))
    target=PROJECT/'phase2/results/historical_verification.json'
    target.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps(record,indent=2));return 0 if record['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
