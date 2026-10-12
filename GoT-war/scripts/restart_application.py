"""Stop only the identified project application worker; preserve other jobs."""
import json,os,signal,time
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
entries=json.loads((b.run/'processes.json').read_text())
for item in entries:
 if item['label']=='application_recovery' and process_birth(item['pid'])==item['birth']:
  os.killpg(item['pgid'],signal.SIGTERM)
  atomic_json(b.run/'application_timeout_recovery.json',{'stopped_pid':item['pid'],'birth':item['birth'],'at':time.time(),'reason':'Schema-constrained decoding exceeded the 240-second pilot request limit. Increase only application schema requests to 600 seconds; immutable campaign deadline unchanged. Partial streams from early timed-out requests were not captured; failure metadata and server token totals retained.'})
# Archive timeout-only artifacts, then resume the same source-bounded construction.
folder=b.run/'application'/'five_kings'
if folder.exists() and not (folder/'blueprint.json').exists():
 archive=b.run/'application_timeouts'/'five_kings';archive.parent.mkdir(exist_ok=True)
 if not archive.exists():folder.rename(archive)
print(b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python -m got_war.application .'],'application_budgeted'))
