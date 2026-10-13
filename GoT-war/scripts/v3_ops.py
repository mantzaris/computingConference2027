"""Bounded v3 service lifecycle; existing pod/cache only, identity-scoped cleanup."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from got_war.budget import Budget, atomic_json, process_birth
from got_war.v3.study import RUN


def start():
    import requests
    cfg_path = ROOT/'configs/budget_v3.json'
    if cfg_path.exists():
        raise RuntimeError('Immutable v3 service budget exists; no restart resets it')
    compute = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader']).decode().strip()
    if compute:
        raise RuntimeError('Existing compute processes; no allocation or termination')
    try:
        requests.get('http://127.0.0.1:8765/v1/models',timeout=2)
    except requests.ConnectionError:
        pass
    else:
        raise RuntimeError('Existing endpoint; inspect before changing service')
    model=json.loads((ROOT/'configs/models.json').read_text())
    cached=ROOT/'.cache/huggingface/hub/models--Qwen--Qwen3-14B-AWQ/snapshots'/model['revision']
    if not cached.exists():
        raise RuntimeError('Authorized cached model unavailable; no downloads in this pilot')
    now=datetime.now(timezone.utc);end=now+timedelta(seconds=7200)
    atomic_json(cfg_path,{'campaign_id':RUN,'started_at':now.isoformat(),'hard_deadline':end.isoformat(),
        'soft_deadline':(end-timedelta(seconds=20)).isoformat(),'no_heavy_jobs_after':end.isoformat(),
        'output_token_ceiling':150000,'analysis_reserve_hours':0,'request_timeout_seconds':180,
        'application_request_timeout_seconds':180,'immutable_service_seconds':7200,
        'scope':'V3 development; original v1/v2 budgets preserved'})
    b=Budget(ROOT,'budget_v3.json')
    probe=subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)'],start_new_session=True)
    born=process_birth(probe.pid);probe.terminate();probe.wait(timeout=3)
    if born is None:raise RuntimeError('Actual-host identity capture failed')
    atomic_json(b.run/'infrastructure.json',{'at':now.isoformat(),'gpu':subprocess.check_output(
        ['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv,noheader']).decode().strip(),
        'cache_revision':model['revision'],'cache_present':True,'process_identity_probe':True,
        'free_disk':subprocess.check_output(['df','-h','/workspace']).decode(),
        'jupyter_status':requests.get('http://127.0.0.1:8888',allow_redirects=False,timeout=3).status_code})
    watchdog=b.launch([str(ROOT/'.venv/bin/python'),str(Path(__file__).resolve()),'watch'],'v3_watchdog')
    command=['env','HF_HUB_ENABLE_HF_TRANSFER=0','HF_HUB_OFFLINE=1','HF_HOME='+str(ROOT/'.cache/huggingface'),
        str(ROOT/'.venv/bin/vllm'),'serve',model['primary'],'--revision',model['revision'],
        '--host','127.0.0.1','--port','8765','--max-model-len',str(model['max_model_len']),
        '--gpu-memory-utilization',str(model['gpu_memory_utilization']),'--max-num-seqs','2',
        '--dtype',model['dtype'],'--enforce-eager','--disable-log-requests']
    server=b.launch(command,'v3_model_server')
    atomic_json(b.run/'service_launch.json',{'server':server,'watchdog':watchdog,'model':model})
    print(json.dumps({'started_at':now.isoformat(),'hard_deadline':end.isoformat(),'server_pid':server['pid']}))


def watch():
    import requests
    b=Budget(ROOT,'budget_v3.json');peak=0
    while True:
        counters={}
        try:
            response=requests.get('http://127.0.0.1:8765/metrics',timeout=3)
            counters={line.split('{')[0].split()[0]:float(line.rsplit(' ',1)[1]) for line in response.text.splitlines()
                      if line.startswith(('vllm:generation_tokens_total','vllm:prompt_tokens_total'))}
            atomic_json(b.run/'service_counters.json',{'at':datetime.now(timezone.utc).isoformat(),'values':counters})
        except (requests.RequestException,ValueError):pass
        reason=('completed' if (b.run/'INFERENCE_DONE').exists() else 'deadline' if b.remaining() <= 0
                else 'token_cap' if counters.get('vllm:generation_tokens_total',0)>=150000 else None)
        sample=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits']).decode().strip()
        with open(b.run/'gpu_samples.jsonl','a') as f:f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'sample':sample})+'\n')
        atomic_json(b.run/'heartbeat.json',{'at':datetime.now(timezone.utc).isoformat(),'remaining_seconds':b.remaining(),'reason':reason})
        if reason:
            labels=['v3_model_server'] if reason=='completed' else ['v3_model_server','v3_study']
            stopped=b.stop_owned(signal.SIGTERM,labels=labels)
            time.sleep(5)
            b.stop_owned(signal.SIGKILL,labels=labels)
            (b.run/'COMPLETE').write_text(datetime.now(timezone.utc).isoformat()+'\n')
            atomic_json(b.run/'service_stop.json',{'reason':reason,'stopped':stopped,
                'at':datetime.now(timezone.utc).isoformat(),'generated_tokens':counters.get('vllm:generation_tokens_total'),
                'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader']).decode().strip(),
                'jupyter_status':requests.get('http://127.0.0.1:8888',allow_redirects=False,timeout=3).status_code})
            return
        time.sleep(10)


def launch():
    import requests
    r=requests.get('http://127.0.0.1:8765/v1/models',timeout=5);r.raise_for_status()
    b=Budget(ROOT,'budget_v3.json')
    print(json.dumps(b.launch([str(ROOT/'.venv/bin/python'),'-m','got_war.v3.study','run','--root',str(ROOT)],'v3_study')))


def transport(action, items):
    from remote import Remote
    r=Remote();r.s.delaybeforesend=.005
    try:
        if action=='put':print(r.put(items))
        elif action=='command':print(r.command(items[0],timeout=120))
        else:print(r.pull(['runs/'+RUN,'configs/budget_v3.json','.private/prompts_v3'],sync_record='runs/'+RUN+'/sync.json'))
    finally:r.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['start','watch','launch','put','pull','command']);p.add_argument('items',nargs='*')
    a=p.parse_args()
    if a.action in ('start','watch','launch'):globals()[a.action]()
    else:transport(a.action,a.items)
