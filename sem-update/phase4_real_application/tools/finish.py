"""Wait for sealed fitting, then execute final evaluation and reproducible reporting."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from app_runtime import ROOT,RESULTS,PROJECT,atomic_json

def main():
    lock=open(ROOT/'runs/final-coordinator.lock','w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    atomic_json(ROOT/'runs/final_coordinator.json',{'pid':os.getpid(),'started_unix':time.time()})
    while not (RESULTS/'frozen_selections.json').exists():time.sleep(10)
    tools=Path(__file__).parent
    subprocess.run([sys.executable,str(tools/'audit_execution.py')],check=True,cwd=PROJECT)
    shutil.copyfile(RESULTS/'execution_audit.json',ROOT/'reports/preselection_audit.json')
    subprocess.run([sys.executable,'-u',str(tools/'application.py'),'evaluate'],check=True,cwd=PROJECT)
    subprocess.run([sys.executable,str(tools/'audit_execution.py')],check=True,cwd=PROJECT)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':''}
    subprocess.run([sys.executable,str(tools/'render_figures.py'),'--prepare'],check=True,cwd=PROJECT,env=env)
    subprocess.run([sys.executable,str(tools/'summarize.py')],check=True,cwd=PROJECT,env=env)
    atomic_json(ROOT/'runs/pipeline_complete.json',{'completed_unix':time.time(),'status':'evaluation and initial reporting complete'})

if __name__=='__main__':main()
