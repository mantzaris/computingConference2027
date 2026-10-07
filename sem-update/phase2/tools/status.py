#!/usr/bin/env python3
"""Read-only status without importing the GPU stack or touching final outcomes."""
import json
import os
from pathlib import Path
import sqlite3
import time

project=Path(__file__).resolve().parents[2]
root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',project/'.artifacts/phase2')).resolve()
book=sqlite3.connect((root/'ledger.sqlite').as_uri()+'?mode=ro',uri=True)
intervals=sorted((a,b or time.time()) for a,b in book.execute('SELECT start,end FROM intervals'))
total=0.;end=0.
for a,b in intervals:total+=max(0.,b-max(a,end));end=max(end,b)
boundary=json.loads((root/'phase_boundary.json').read_text())
complete=[]
for path in (root/'runs/datasets').glob('*/complete.json'):
    record=json.loads(path.read_text())
    if record['item']['data_id'].startswith(('p2-main','p2-chambers')):
        complete.append({'data_id':record['item']['data_id'],'tasks':len(record['tasks'])})
result={'historical_device_hours':boundary['historical_gpu_seconds']/3600,
        'phase2_device_hours':(total-boundary['historical_gpu_seconds'])/3600,
        'additional_hours_remaining':(boundary['cumulative_cap_seconds']-total)/3600,
        'completed_main_datasets':len(complete),'completed_main_settings':sum(r['tasks'] for r in complete),
        'active_jobs':[r[0] for r in book.execute("SELECT id FROM jobs WHERE status='running' ORDER BY id")],
        'failed_jobs':[{'id':r[0],'attempts':r[1]} for r in book.execute("SELECT id,attempts FROM jobs WHERE status='failed' AND id LIKE 'phase2-%'")],
        'retried_jobs':[{'id':r[0],'attempts':r[1]} for r in book.execute("SELECT id,attempts FROM jobs WHERE attempts>1 AND id LIKE 'phase2-%'")],
        'final_test_opened':(project/'phase2/results/final_test_access.json').exists(),
        'resume':'PYTHONPATH=src .artifacts/venv/bin/python -u -m sem_update.phase2.runner run'}
print(json.dumps(result,indent=2))
