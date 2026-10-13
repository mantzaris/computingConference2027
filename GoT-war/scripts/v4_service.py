"""Project-scoped service setup, absolute deadline, token cap and identity checks."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.budget import Budget, atomic_json


def now():
    return datetime.now(timezone.utc)


def setup():
    subprocess.run(['python3','-m','venv','--system-site-packages',str(ROOT/'.venv')],check=True)
    env=dict(os.environ,PIP_CACHE_DIR=str(ROOT/'.cache/pip'),HF_HOME=str(ROOT/'.cache/huggingface'),
             HF_HUB_ENABLE_HF_TRANSFER='0')
    subprocess.run([str(ROOT/'.venv/bin/pip'),'install','vllm==0.10.2','transformers==4.56.2',
                    'networkx','beautifulsoup4','requests'],env=env,check=True,timeout=750)
    model=json.loads((ROOT/'configs/models.json').read_text())
    code='from huggingface_hub import snapshot_download; print(snapshot_download('+repr(model['primary'])+',revision='+repr(model['revision'])+'))'
    subprocess.run([str(ROOT/'.venv/bin/python'),'-c',code],env=env,check=True,timeout=750)
    (Budget(ROOT,'budget_v4.json').run/'SETUP_DONE').write_text(now().isoformat())


def start():
    b=Budget(ROOT,'budget_v4.json')
    p=b.run/'service_window.json'
    if p.exists():raise RuntimeError('Never reset a service window')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader']).strip():
        raise RuntimeError('Existing GPU work; no changes')
    model=json.loads((ROOT/'configs/models.json').read_text())
    start=now();end=min(start+timedelta(seconds=7200),datetime.fromisoformat(b.config['hard_deadline']))
    atomic_json(p,{'started_at':start.isoformat(),'deadline':end.isoformat(),'generated_token_cap':150000,'model':model})
    b.launch([sys.executable,str(Path(__file__).resolve()),'watch'],'v4_service_watchdog')
    command=['env','HF_HOME='+str(ROOT/'.cache/huggingface'),'HF_HUB_OFFLINE=1','HF_HUB_ENABLE_HF_TRANSFER=0',
        str(ROOT/'.venv/bin/vllm'),'serve',model['primary'],'--revision',model['revision'],'--host','127.0.0.1',
        '--port','8765','--max-model-len','12288','--gpu-memory-utilization','0.88','--max-num-seqs','1',
        '--dtype','half','--enforce-eager','--disable-log-requests']
    print(json.dumps(b.launch(command,'v4_model_server')))


def watch():
    import requests
    b=Budget(ROOT,'budget_v4.json');window=json.loads((b.run/'service_window.json').read_text())
    peak=0
    while True:
        try:
            content=requests.get('http://127.0.0.1:8765/metrics',timeout=3).text
            generated=sum(float(line.rsplit(' ',1)[1]) for line in content.splitlines()
                          if line.startswith('vllm:generation_tokens_total'))
            peak=max(peak,generated)
        except Exception:pass
        sample=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader']).decode().strip()
        atomic_json(b.run/'service_accounting.json',{'at':now().isoformat(),'generated_tokens':peak,'gpu':sample})
        with (b.run/'gpu_samples.jsonl').open('a') as f:f.write(json.dumps({'at':now().isoformat(),'sample':sample})+'\n')
        reason='requested_completion' if (b.run/'INFERENCE_DONE').exists() else 'deadline' if now()>=datetime.fromisoformat(window['deadline']) else 'token_cap' if peak>=150000 else None
        if reason:
            stopped=b.stop_owned(signal.SIGTERM,labels=['v4_model_server','v4_inference'])
            time.sleep(3);b.stop_owned(signal.SIGKILL,labels=['v4_model_server','v4_inference'])
            atomic_json(b.run/'service_stop.json',{'at':now().isoformat(),'reason':reason,'stopped':stopped,'generated_tokens':peak})
            return
        time.sleep(10)


if __name__=='__main__':
    globals()[sys.argv[1]]()
