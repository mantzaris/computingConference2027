"""Explicit phases: correctness, pilots, freeze, selection, final evaluation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from .runtime import configure_caches,artifact_root,PROJECT,Ledger,atomic_json,read_json,source_state,digest

def require_cuda():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Production execution requires CUDA; refusing CPU fallback')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False
    torch.use_deterministic_algorithms(True)

def run_pilots(config=None):
    import torch
    from .data import prepare_synthetic,load_learner
    from .graphs import DAG,corrupt
    from .search import repair,DEFAULT_SEARCH
    from .training import DEFAULT_TRAIN
    require_cuda()
    marker=PROJECT/'results/curated/correctness.json'
    if not marker.exists() or not read_json(marker)['passed']:
        raise RuntimeError('correctness gate must pass first')
    cfg=read_json(config) if config else {'train':DEFAULT_TRAIN,'search':DEFAULT_SEARCH}
    ledger=Ledger()
    reports=[]
    for d,family,seed in ((5,'linear',91001),(5,'heteroscedastic',92001),(10,'heteroscedastic',92002)):
        run_id=f'pilot-d{d}-{family}-{digest(cfg)[:8]}'
        target=PROJECT/'results/curated'/f'{run_id}.json'
        if ledger.claim(run_id,cfg,expected_seconds=1800):
            try:
                with ledger.device_interval(run_id):
                    torch.cuda.reset_peak_memory_stats()
                    root=prepare_synthetic(d,family,seed,400,development=True)
                    data=load_learner(root,'cuda')
                    truth=DAG.from_json(read_json(root/'truth.json')['graph'])
                    initial,_=corrupt(truth,.5,seed+80)
                    record=repair(data,[initial],run_id,train_config=cfg['train'],search_config=cfg['search'])
                    # Pilots exercise selection and audit; final benchmark test loaders stay closed.
                    summary={k:record[k] for k in ('run_id','wall_seconds','candidate_count','unique_parent_sets',
                                                   'new_parent_sets','optimizer_updates','peak_vram_bytes','audit')}
                    summary.update(d=d,family=family,config=cfg,data_hash=data.key,source=source_state())
                    atomic_json(target,summary)
                ledger.finish(run_id)
            except Exception:
                ledger.finish(run_id,traceback.format_exc())
                raise
        reports.append(read_json(target))
        atomic_json(PROJECT/'results/curated/pilots.json',{'pilots':reports,'ledger':ledger.snapshot()})
        print(json.dumps(reports[-1]),flush=True)
    return reports

def main():
    configure_caches()
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['doctor','smoke','pilots','prepare-data','prepare-models','run','freeze','evaluate','export-paper','verify-artifacts'])
    parser.add_argument('--config')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--frozen-manifest')
    parser.add_argument('--run-index')
    parser.add_argument('--require-cuda',action='store_true',default=True,help='CUDA is mandatory for production commands')
    parser.add_argument('--data-id',help='internal independent-dataset worker; never freezes the whole matrix')
    parser.add_argument('--plots-only',action='store_true',help='rebuild vectors/tables from curated results without GPU experiments')
    args=parser.parse_args()
    if args.plots_only and args.command!='export-paper':
        parser.error('--plots-only is only valid for export-paper')
    if args.command=='doctor':
        from .runtime import doctor
        print(json.dumps(doctor(),indent=2))
    elif args.command=='smoke':
        require_cuda()
        ledger=Ledger()
        job='correctness-'+time.strftime('%Y%m%dT%H%M%S')
        ledger.claim(job,source_state())
        log=artifact_root()/'logs'/(job+'.log')
        (artifact_root()/'runs'/job).mkdir(parents=True,exist_ok=True)
        with ledger.device_interval(job),open(log,'w') as output:
            status=subprocess.call([sys.executable,'-m','pytest','-q','--basetemp',str(artifact_root()/'runs'/job/'tmp')],cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT)
        ledger.finish(job,None if status==0 else 'pytest exit '+str(status))
        from .experiments import implementation_hash
        atomic_json(PROJECT/'results/curated/correctness.json',{'passed':status==0,'exit_code':status,'source':source_state(),
                    'scientific_implementation_hash':implementation_hash(),'log':str(log.relative_to(artifact_root()))})
        print(log.read_text())
        raise SystemExit(status)
    elif args.command=='pilots':
        run_pilots(args.config)
    elif args.command=='prepare-data':
        from .chambers import audit
        print(json.dumps(audit(),indent=2))
    elif args.command=='prepare-models':
        from .bootstrap import prepare_models
        print(json.dumps(prepare_models(),indent=2))
    elif args.command=='verify-artifacts':
        from .runtime import verify_artifacts
        print(json.dumps(verify_artifacts(),indent=2))
    else:
        from .experiments import dispatch
        if args.command in ('run','evaluate','export-paper') and not args.plots_only:
            ledger=Ledger()
            job='execution-'+args.command+'-'+time.strftime('%Y%m%dT%H%M%S')+'-'+str(os.getpid())
            ledger.claim(job,{'arguments':vars(args),'source':source_state()})
            try:
                with ledger.device_interval(job):
                    dispatch(args)
                ledger.finish(job)
                atomic_json(PROJECT/'results/curated/runtime_ledger.json',ledger.snapshot())
            except BaseException:
                ledger.finish(job,traceback.format_exc())
                raise
        else:
            dispatch(args)

if __name__=='__main__':
    main()
