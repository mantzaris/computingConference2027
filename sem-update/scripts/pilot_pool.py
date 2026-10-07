"""Cold-cache timing of the same three declared pilot tasks on one GPU."""
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path
import time
from sem_update.runtime import artifact_root,PROJECT,Ledger,digest,atomic_json,read_json,file_hash

def task(arguments):
    d,family,seed,root=arguments
    os.environ['SEM_UPDATE_ARTIFACT_ROOT']=root
    from sem_update.cli import require_cuda
    from sem_update.data import prepare_synthetic,load_learner
    from sem_update.graphs import DAG,corrupt
    from sem_update.search import repair
    from sem_update.training import DEFAULT_TRAIN
    require_cuda()
    data_root=prepare_synthetic(d,family,seed,400,development=True)
    data=load_learner(data_root,'cuda')
    truth=DAG.from_json(read_json(data_root/'truth.json')['graph'])
    graph,_=corrupt(truth,.5,seed+80)
    run_id=f'pool-pilot-d{d}-{family}'
    result=repair(data,[graph],run_id,train_config=DEFAULT_TRAIN)
    return {'d':d,'family':family,'seed':seed,'data_hash':data.key,
            **{k:result[k] for k in ('wall_seconds','candidate_count','new_parent_sets','unique_parent_sets',
                                    'optimizer_updates','peak_vram_bytes')}}

def main():
    from sem_update.experiments import implementation_hash
    key=digest({'implementation':implementation_hash(),'script':file_hash(__file__),'workers':3})
    job='cold-pool-pilots-'+key[:12]
    ledger=Ledger()
    target=PROJECT/'results/curated/pool_pilot.json'
    if not ledger.claim(job,{'key':key},expected_seconds=1800):
        print(read_json(target))
        return
    root=artifact_root()/'runs'/job/'cold_artifacts'
    args=[(d,family,seed,str(root)) for d,family,seed in
          ((5,'linear',91001),(5,'heteroscedastic',92001),(10,'heteroscedastic',92002))]
    try:
        start=time.monotonic()
        with ledger.device_interval(job):
            with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
                rows=list(pool.map(task,args))
        ledger.finish(job)
        result={'workers':3,'same_existing_device':True,'wall_seconds':time.monotonic()-start,
                'tasks':rows,'implementation_hash':implementation_hash(),
                'purpose':'cold-cache concurrency timing after implementation corrections, not seed selection',
                'all_final_benchmark_outcomes_sealed':True,'ledger':ledger.snapshot()}
        atomic_json(target,result)
        print(result)
    except BaseException as error:
        ledger.finish(job,str(error))
        raise

if __name__=='__main__':
    main()
