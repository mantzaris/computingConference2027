"""Checkpoint and stop only the obsolete mixed-time-unit application worker."""
import json,os,signal,sqlite3,time,sys
from datetime import datetime,timezone
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
reason=sys.argv[1] if len(sys.argv)>1 else 'consistent generated time units'
prefix=sys.argv[2] if len(sys.argv)>2 else 'application_thinking'
if not prefix.startswith('application_'):raise ValueError('Only application workers may be checkpointed by this helper')
old=next(p for p in reversed(json.loads((b.run/'processes.json').read_text())) if p['label'].startswith(prefix))
db=sqlite3.connect(str(b.run/'queue.sqlite'),timeout=30)
# Snapshot before signaling: a dependency supervisor may start a new stage as
# soon as this worker exits. Never mark those newly started requests cancelled.
unfinished=db.execute("SELECT key,role,created FROM jobs WHERE status='running' AND role LIKE 'application_%'").fetchall()
if process_birth(old['pid'])==old['birth'] and os.getpgid(old['pid'])==old['pgid']==old['pid']:
    os.killpg(old['pgid'],signal.SIGTERM)
    time.sleep(1)
    if process_birth(old['pid'])==old['birth']:
        stat=Path('/proc/%s/stat'%old['pid'])
        if stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':os.killpg(old['pgid'],signal.SIGKILL)
rows=[]
for key,role,created in unfinished:
    partial=b.run/('partial_'+key+'.jsonl');saved=b.run/('interrupted_'+key+'.jsonl')
    if partial.exists() and not saved.exists():partial.rename(saved)
    rows.append({'key':key,'role':role,'created':created,'partial_stream_file':saved.name if saved.exists() else None,'error':'Project application worker checkpointed for '+reason+'; no completion was fabricated.'})
    db.execute("UPDATE jobs SET status='cancelled',error=? WHERE key=?",(reason+'; partial stream retained',key))
db.commit();db.close()
previous=b.run/'application_time_unit_checkpoint.json'
if previous.exists():
    value=json.loads(previous.read_text());saved=b.run/('application_checkpoint_%d.json'%value['stopped_worker']['pid'])
    if not saved.exists():atomic_json(saved,value)
atomic_json(b.run/('application_checkpoint_%d.json'%old['pid']),{'stopped_worker':old,'at':datetime.now(timezone.utc).isoformat(),'reason':reason,'unfinished_requests':rows,'other_jobs_stopped':False})
with open('results/failures.jsonl','a') as f:
    for row in rows:f.write(json.dumps(row)+'\n')
print('Checkpointed the selected application worker; no other worker or model-service group was signaled')
