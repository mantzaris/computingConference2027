#!/usr/bin/env python3
"""Read-only experiment progress; never imports model or final-test loaders."""
import collections
import argparse
import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time

PROJECT=Path(__file__).resolve().parents[1]

def snapshot():
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts')).resolve()
    database=root/'ledger.sqlite'
    if not database.exists():
        raise RuntimeError('Run on the execution machine with its live artifact ledger')
    connection=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=10)
    jobs=[dict(zip(('id','status','attempts','error'),r)) for r in connection.execute('SELECT id,status,attempts,error FROM jobs')]
    intervals=sorted((a,b or time.time()) for a,b in connection.execute('SELECT start,end FROM intervals'))
    used,end=0.,0.
    for a,b in intervals:
        used+=max(0.,b-max(a,end));end=max(end,b)
    connection.close()
    path=PROJECT/'results/curated/run_index.json'
    index=json.loads(path.read_text()) if path.exists() else {'runs':[],'complete':False}
    protocol=json.loads((PROJECT/'results/curated/frozen_protocol.json').read_text())
    cfg=protocol['config']
    expected=0
    for item in protocol['matrix']:
        if item['study']=='controlled':
            expected+=4+4*len(cfg['corruptions'])
            if item['family']=='heteroscedastic' and item['d']==5:
                expected+=4+(3 if item['budget']==100 else 0)
        else:
            expected+=(4 if item['study']=='semantic' else 2)+4*len(cfg['metadata_variants'])
    shards=[]
    for path in (root/'runs/shards').glob('*.json'):
        value=json.loads(path.read_text())
        shards.append({'data_id':path.stem,'runs':len(value['runs']),'complete':value['complete']})
    progress=[]
    for path in sorted((root/'runs').glob('dcdi-*/trace.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:3]:
        age=time.time()-path.stat().st_mtime
        if age<120:
            progress.append({'discovery':path.parent.name,'updates':json.loads(path.read_text())[-1]['step'],
                             'seconds_since_checkpoint':round(age)})
    report={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'gpu_job_hours_used':used/3600,'cap_hours':cfg['cap_hours'],
            'completed_method_runs':len(index['runs']),'expected_method_runs':expected,
            'completed_datasets':sum(s['complete'] for s in shards),'expected_datasets':len(protocol['matrix']),
            'runs_by_scope':dict(collections.Counter((r['study']+'-d'+str(r['d'])) for r in index['runs'])),
            'matrix_selection_complete':index['complete'],
            'active_jobs':[r['id'] for r in jobs if r['status']=='running'],
            'recorded_failed_jobs':sum(r['status']=='failed' for r in jobs),
            'recent_discovery_checkpoints':progress,
            'final_test_access_record_present':(PROJECT/'results/curated/final_test_access.json').exists()}
    continuation=PROJECT/'results/curated/continuation_status.json'
    report['continuation_phase']=json.loads(continuation.read_text())['state'] if continuation.exists() else 'selection'
    try:
        report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used',
                                              '--format=csv,noheader'],text=True).strip()
    except (OSError,subprocess.SubprocessError):
        report['gpu']='unavailable'
    return report

def write_status(report):
    path=PROJECT/'docs/status.md'
    text=path.read_text()
    start='<!-- live-execution-progress -->'
    stop='<!-- /live-execution-progress -->'
    continuation=PROJECT/'results/curated/continuation_status.json'
    phase=json.loads(continuation.read_text())['state'] if continuation.exists() else 'selection'
    lines=[start,'','## Live execution checkpoint','',
           'Updated '+report['timestamp_utc']+'.','',
           f"- Selected method runs: {report['completed_method_runs']}/{report['expected_method_runs']}.",
           f"- Completed dataset blocks: {report['completed_datasets']}/{report['expected_datasets']}.",
           f"- Recorded GPU-job hours: {report['gpu_job_hours_used']:.3f}/{report['cap_hours']}.",
           '- Continuation phase: '+phase+'.',
           '- GPU utilization and memory used: '+report['gpu']+'.',
           '- Final-test access record present: '+str(report['final_test_access_record_present'])+'.',
           '- Failed ledger jobs, including preserved development failures: '+str(report['recorded_failed_jobs'])+'.','',
           'Active ledger jobs: '+(', '.join('`'+s+'`' for s in report['active_jobs']) or 'none')+'.','',stop]
    block='\n'.join(lines)
    if start in text and stop in text:
        text=text[:text.index(start)]+block+text[text.index(stop)+len(stop):]
    else:
        text+='\n\n'+block+'\n'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(text)
    temporary.replace(path)
    return phase

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--write-status',action='store_true')
    parser.add_argument('--watch',action='store_true',help='write a status checkpoint every 50 seconds until continuation ends')
    args=parser.parse_args()
    while True:
        report=snapshot()
        phase=write_status(report) if args.write_status or args.watch else None
        print(json.dumps(report,indent=None if args.watch else 2),flush=True)
        if not args.watch or phase in ('blocked','evaluation_and_export_complete'):
            break
        time.sleep(50)
