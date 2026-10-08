"""Run frozen fitting, integrity gates, final evaluation and paper outputs."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from sem_update.phase3.runtime import setup,root,atomic_json,freeze_guard,file_hash,RESULTS

def main():
    setup();freeze_guard();state_path=root()/'runs/main_session.json'
    if os.getpgrp()!=os.getpid():os.setsid()
    stop=root()/'runs/main_session_stopped';stop.unlink(missing_ok=True)
    monitor=subprocess.Popen([sys.executable,'-u','phase3/tools/monitor_gpu.py','--stop-file',str(stop)])
    stages=[('fit',['-m','sem_update.phase3.runner','run']),
        ('frozen-input-and-selection-audit',['phase3/tools/audit_execution.py']),
        ('final-predictions',['phase3/tools/evaluate_frozen.py']),
        ('illustrations',['-m','sem_update.phase3.illustrations']),
        ('readable-local-graph-layout',['phase3/tools/refine_figure_layout.py']),
        ('curated-statistics-and-figures',['-m','sem_update.phase3.reporting']),
        ('prediction-integrity-audit',['phase3/tools/audit_execution.py','--predictions']),
        ('cost-and-coverage-summary',['phase3/tools/summarize_execution.py']),
        ('final-figure-manifest',['-m','sem_update.phase3.reporting']),
        ('curated-only-reproduction',['phase3/tools/check_plot_reproduction.py'])]
    state={'pid':os.getpid(),'protocol_sha256':file_hash(RESULTS/'protocol.json'),'status':'running','completed_stages':[]}
    atomic_json(state_path,state)
    guard=subprocess.Popen([sys.executable,'-u','phase3/tools/enforce_budget.py'],start_new_session=True)
    try:
        for name,args in stages:
            state.update(stage=name,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            atomic_json(state_path,state);print(json.dumps({'stage':name,'status':'starting'}),flush=True)
            subprocess.run([sys.executable,'-u',*args],check=True)
            state['completed_stages'].append(name)
        state['status']='complete'
    except BaseException:
        state.update(status='failed',traceback=traceback.format_exc());raise
    finally:
        state['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();atomic_json(state_path,state)
        stop.touch()
        monitor.wait(timeout=30)
        guard.wait(timeout=10)

if __name__=='__main__':main()
