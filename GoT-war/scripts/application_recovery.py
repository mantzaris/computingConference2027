"""One revised structured candidate per failed case; maximum two repairs per artifact.

Protocol v1 is preserved under runs/.../application_v1. This is a declared
schema-stage revision after an application construction failure, not test tuning.
"""
import json,os,time
from pathlib import Path
from got_war.application import run_application
from got_war.budget import Budget
root=Path.cwd();b=Budget(root)
# Wait for the original project application worker to finish, never interrupt a request.
registry=json.loads((b.run/'processes.json').read_text())
entry=next((x for x in reversed(registry) if x['label']=='application_main'),None)
if entry:
 from got_war.budget import process_birth
 while process_birth(entry['pid'])==entry['birth']:
  b.check(estimated_seconds=20,reserve_seconds=5*3600)
  # A zombie has finished; do not wait for the external reaper.
  state=Path('/proc/%d/stat'%entry['pid']).read_text().rsplit(')',1)[1].split()[0]
  if state=='Z':break
  time.sleep(10)
for case in json.loads((root/'configs/experiment.json').read_text())['cases']:
 folder=b.run/'application'/case['id']
 if folder.exists() and not list(folder.glob('alternative_*.json')):
  archive=b.run/'application_v1'/case['id'];archive.parent.mkdir(exist_ok=True)
  if not archive.exists():folder.rename(archive)
run_application(root)
