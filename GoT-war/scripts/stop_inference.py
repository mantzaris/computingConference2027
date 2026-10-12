"""Release this project's model service after all required inference artifacts exist."""
import json,os,signal,time
from datetime import datetime,timezone
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json

b=Budget('.')
if not (b.run/'inference_complete.json').exists():
    raise RuntimeError('Verify and record inference completion before stopping the service')
registry=json.loads((b.run/'processes.json').read_text())
server=next(p for p in reversed(registry) if p['label']=='model_server_ready')
if process_birth(server['pid'])==server['birth'] and os.getpgid(server['pid'])==server['pgid']==server['pid']:
    os.killpg(server['pgid'],signal.SIGTERM)
    for _ in range(30):
        if process_birth(server['pid'])!=server['birth']:break
        time.sleep(1)
    if process_birth(server['pid'])==server['birth'] and os.getpgid(server['pid'])==server['pgid']:
        stat=Path('/proc/%s/stat'%server['pid'])
        if stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':os.killpg(server['pgid'],signal.SIGKILL)
atomic_json(b.run/'inference_finished.json',{'service_stopped_at':datetime.now(timezone.utc).isoformat(),'server_label':server['label'],'pid':server['pid'],'scope':'Only the verified project model-service process group; the pod and Jupyter remain running.'})
print('Project inference service stopped')
