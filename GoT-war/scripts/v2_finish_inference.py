"""Stop only this campaign's model service when the fixed inference design ends."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime,timezone
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v2.runtime import budget
from got_war.budget import atomic_json,process_birth
from v2_resources import capture,summarize


def live(entry):
    if process_birth(entry['pid'])!=entry['birth']:return False
    try:return Path('/proc/%d/stat'%entry['pid']).read_text().rsplit(')',1)[1].split()[0]!='Z'
    except OSError:return False


def main():
    b=budget(ROOT)
    cases=[json.loads(line) for line in (b.run/'benchmark_cases.jsonl').read_text().splitlines()]
    while True:
        b.check()
        completed=[]
        for case in cases:
            file=b.run/'benchmark'/(case['id']+'.json')
            if file.exists() and json.loads(file.read_text()).get('completed'):completed.append(case['id'])
        registry=json.loads((b.run/'processes.json').read_text())
        active=[e for e in registry if e['label'].startswith('v2_fixed_') and live(e)]
        if len(completed)==len(cases) and not active:break
        atomic_json(b.run/'inference_monitor.json',{'at':datetime.now(timezone.utc).isoformat(),'completed':len(completed),'planned':len(cases),'active_workers':[e['label'] for e in active]})
        time.sleep(30)
    atomic_json(b.run/'inference_finished.json',{'at':datetime.now(timezone.utc).isoformat(),'completed':len(completed),'planned':len(cases),
        'criterion':'Every frozen record completed and all fixed workers exited; no score-based stopping.'})
    capture(b.run);summarize()
    stopped=b.stop_owned(labels=['v2_model_server_1'])
    for _ in range(20):
        if not any(e['label']=='v2_model_server_1' and live(e) for e in registry):break
        time.sleep(1)
    still=[e['label'] for e in registry if e['label']=='v2_model_server_1' and live(e)]
    if still:
        stopped+=b.stop_owned(signal.SIGKILL,labels=['v2_model_server_1']);time.sleep(2)
    gpu=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
    processes=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True,timeout=15)
    try:jupyter=requests.get('http://127.0.0.1:8888',allow_redirects=False,timeout=10).status_code
    except requests.RequestException as error:jupyter=type(error).__name__
    atomic_json(b.run/'shutdown_verification.json',{'at':datetime.now(timezone.utc).isoformat(),'stopped_registered_labels':stopped,
        'gpu_memory_mib_and_utilization':gpu.stdout.strip(),'compute_processes':processes.stdout.strip(),'jupyter_http_status':jupyter,
        'scope':'Only the v2-created model service was signaled, after birth/group verification. The pod, SSH and unrelated services remain untouched. Campaign analysis and packaging continue under the original deadline.'})
    print('FIXED_INFERENCE_FINISHED',len(completed),'SERVER_STOPPED',stopped,flush=True)


if __name__=='__main__':main()
