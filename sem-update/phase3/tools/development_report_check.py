"""Exercise plots and missing-cell reporting using actual development pilots only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import pandas as pd
import torch
from sem_update.phase3.runtime import PROJECT,RESULTS,root,read_json,atomic_json,file_hash,freeze_guard

def main():
    if torch.cuda.is_available():raise RuntimeError('Hide CUDA for this CPU reporting check')
    protocol=freeze_guard();inputs=[];frames=[]
    for pilot in read_json(RESULTS/'pilots.json'):
        assert pilot['task']['development'] and pilot['task']['seed'] in (390020,390050,390100)
        for resource in ('fixed','adjusted'):
            record=read_json(root()/pilot['records'][-1][resource])
            manifest=read_json(root()/record['data_folder']/'manifest.json')
            path=root()/'runs'/(record['condition']+'-'+resource+'-pilot-metrics.json')
            rows=pd.DataFrame(read_json(path))
            assert set(rows.scm)=={pilot['task']['seed']}
            rows=rows[rows.resource==resource].copy()
            # Development files predate the explicit main/sensitivity label.
            # Map only known metadata; missing newer cost fields stay unavailable.
            rows['budget']=manifest['budget_per_target'];rows['sensitivity']='primary'
            if 'search_gpu_seconds' not in rows:rows['search_gpu_seconds']=float('nan')
            frames.append(rows);inputs.append({'path':str(path.relative_to(root())),'sha256':file_hash(path)})
    scratch=Path(tempfile.mkdtemp(prefix='report-development-',dir=root()/'archives'))/'sem-update'
    scratch.mkdir()
    shutil.copytree(PROJECT/'src',scratch/'src',ignore=shutil.ignore_patterns('__pycache__'))
    destination=scratch/'phase3/results';destination.mkdir(parents=True)
    pd.concat(frames,ignore_index=True).to_csv(destination/'metrics.csv',index=False,float_format='%.9g')
    clean=scratch/'.artifacts/phase3'
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONPATH':str(scratch/'src'),
         'SEM_UPDATE_ARTIFACT_ROOT':str(clean),'MPLCONFIGDIR':str(clean/'model_cache/matplotlib')}
    log=root()/'logs/development-report-check.log'
    previous=RESULTS/'reporting_validation.json'
    for path in (log,previous):
        if path.exists():shutil.copy2(path,root()/'logs'/(path.stem+'-'+file_hash(path)+path.suffix))
    with log.open('w') as stream:
        code=subprocess.call([sys.executable,'-m','sem_update.phase3.reporting'],cwd=scratch,env=env,
                             stdout=stream,stderr=subprocess.STDOUT)
    outputs=[str(p.relative_to(scratch)) for p in sorted((scratch/'phase3/paper').rglob('*')) if p.is_file()]
    value={'passed':code==0,'exit_code':code,'cuda_available':False,'main_outcomes_accessed':False,
           'development_scms':[390020,390050,390100],'metric_rows':sum(len(r) for r in frames),
           'inputs':inputs,'outputs':outputs,'scope':'Actual pilots, including intentionally absent additive/profile cells; no invented benchmark values',
           'scientific_hash':protocol['scientific_hash'],'reporting_sha256':file_hash(PROJECT/'src/sem_update/phase3/reporting.py'),
           'scratch':str(scratch.relative_to(root())),'log':str(log.relative_to(root()))}
    atomic_json(RESULTS/'reporting_validation.json',value);print(json.dumps(value,indent=2))
    raise SystemExit(code)

if __name__=='__main__':main()
