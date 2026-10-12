"""Switch only a failed project application construction worker, with an audit."""
import json,os,signal,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
first=b.run/'application/five_kings'
if not (first/'failure.json').exists():
 raise RuntimeError('Wait for the bounded monolithic artifact to finish/fail; do not interrupt it preemptively')
entries=json.loads((b.run/'processes.json').read_text());stopped=[]
for item in entries:
 if item['label']=='application_budgeted' and process_birth(item['pid'])==item['birth']:
  os.killpg(item['pgid'],signal.SIGTERM);stopped.append(item['pid'])
reason='Monolithic application candidate exhausted bounded repairs. Switch to modular variable/dependency/citation artifacts without supplying any topic-specific cause or graph.'
row={'at':datetime.now(timezone.utc).isoformat(),'stopped_project_pids':stopped,'reason':reason,'partial_streams_retained':[p.name for p in b.run.glob('partial_*.jsonl')]}
atomic_json(b.run/'modular_switch.json',row)
with open(Path('results/failures.jsonl'),'a') as f:f.write(json.dumps(row)+'\n')
conn=sqlite3.connect(b.run/'queue.sqlite');conn.execute("UPDATE jobs SET status='failed',error=?,finished=? WHERE status='running' AND role LIKE 'application_%'",(reason,row['at']));conn.commit();conn.close()
print(b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_modular'))
