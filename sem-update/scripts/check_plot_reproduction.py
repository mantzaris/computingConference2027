#!/usr/bin/env python3
"""Rebuild all paper vectors/tables from a clean curated-only copy with CUDA hidden."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PROJECT=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts')).resolve()
    (root/'archives').mkdir(parents=True,exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='plot-reproduction-',dir=root/'archives'))/'sem-update'
    scratch.mkdir()
    for name in ('src','configs','prompts','results/curated'):
        shutil.copytree(PROJECT/name,scratch/name,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(PROJECT/'requirements.lock',scratch/'requirements.lock')
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in (PROJECT/'results/curated').rglob('*')
            if p.is_file() and (p.suffix=='.csv' or p.parent.name=='graphs')}
    clean_root=scratch/'.artifacts'
    env=os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='',PYTHONPATH=str(scratch/'src'),
               SEM_UPDATE_ARTIFACT_ROOT=str(clean_root),
               PYTHONPYCACHEPREFIX=str(clean_root/'model_cache/pycache'),
               MPLCONFIGDIR=str(clean_root/'model_cache/matplotlib'),
               CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    cuda_probe=subprocess.check_output([sys.executable,'-c',
        'import torch; print(torch.cuda.is_available())'],env=env,text=True).strip()
    if cuda_probe!='False' or clean_root.exists() and any(clean_root.glob('data/**/*')):
        raise RuntimeError('Clean plotting check must have no CUDA or experiment data')
    log=root/'logs/plot-reproduction.log'
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as output:
        code=subprocess.call([sys.executable,'-m','sem_update.cli','export-paper','--plots-only'],
                              cwd=scratch,env=env,stdout=output,stderr=subprocess.STDOUT)
    outputs={}
    for folder,suffixes in [('paper/figures',('.pdf','.svg')),('paper/tables',('.tex',))]:
        for original in sorted((PROJECT/folder).iterdir()):
            if original.suffix in suffixes:
                name=str(original.relative_to(PROJECT))
                reproduced=scratch/name
                actual=sha(reproduced) if reproduced.exists() else None
                outputs[name]={'expected_sha256':sha(original),'reproduced_sha256':actual,
                               'identical':actual==sha(original)}
    changed_inputs=[name for name,value in inputs.items() if sha(scratch/name)!=value]
    report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'exit_code':code,'cuda_visible_devices':'','torch_cuda_available':False,
            'raw_data_or_models_copied':False,'changed_numeric_or_graph_inputs':changed_inputs,
            'outputs':outputs,'all_outputs_identical':all(r['identical'] for r in outputs.values()),
            'source_script_sha256':sha(Path(__file__)),
            'archive':str(scratch.relative_to(root)),'log':str(log.relative_to(root))}
    target=PROJECT/'results/curated/plot_reproduction_check.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if code==0 and report['all_outputs_identical'] and not changed_inputs else 1

if __name__=='__main__':
    raise SystemExit(main())
