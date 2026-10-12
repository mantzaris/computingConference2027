"""Budgeted two-worker campaign launcher; resumes from persisted per-item records."""
import json,os,subprocess,time
from pathlib import Path
from got_war.budget import Budget,atomic_json
from got_war.environment import collect
root=Path.cwd();b=Budget(root)
while not (b.run/'pilot_summary.json').exists():
    b.check(estimated_seconds=30,reserve_seconds=5*3600);time.sleep(10)
pilot=json.loads((b.run/'pilot_summary.json').read_text())
# Conservative request-count bound: 96*(B0+B1+synthesis+two repairs) + application requests.
pending_requests=96*5+150
projection=pending_requests*max(pilot['p90_seconds'],30)+5*3600
if pilot['json_valid']<16 or pilot['synthesis_executable']<2:
    raise RuntimeError('Pilot validity gate failed; review retained failures before further inference')
b.check(heavy=True,estimated_seconds=projection)
atomic_json(b.run/'feasibility.json',{'pilot':pilot,'pending_request_upper_bound':pending_requests,'projected_remaining_seconds_including_five_hour_reserve':projection,'remaining_seconds':b.remaining(),'decision':'complete primary model campaign; omit optional second model initially','checked_at':time.time()})
collect(root)
jobs=[]
for label,module in [('benchmark_main','got_war.experiments'),('application_main','got_war.application')]:
    command=['bash','-c','PYTHONPATH=src .venv/bin/python -m '+module+(' benchmark --root .' if label=='benchmark_main' else ' .')]
    jobs.append(b.launch(command,label))
atomic_json(b.run/'core_workers.json',jobs)
print('Core workers launched after measured feasibility gate',flush=True)
