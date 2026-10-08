"""Development throughput probe; never used as a scientific method result."""
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
import torch
from sem_update.phase3.runtime import setup,require_cuda,job,RESULTS,atomic_json,file_hash
from sem_update.phase3.discovery import official_model
from sem_update.runtime import check_budget

def worker(ordinal):
    setup();require_cuda();cfg={'layers':2,'width':64,'flow_layers':2,'flow_width':8}
    torch.manual_seed(393001+ordinal);model=official_model(100,cfg)
    x=torch.randn(256,100,device='cuda');optimizer=torch.optim.RMSprop(model.parameters(),lr=.001)
    torch.cuda.reset_peak_memory_stats();start=time.monotonic()
    for step in range(1200):
        lp=model.compute_log_likelihood(x,*model.get_parameters());a=model.get_w_adj()
        h=(torch.matrix_exp(a.double()).trace()-100)/1e43
        objective=-lp.mean()+.1*a.mean()+h.square()
        optimizer.zero_grad(set_to_none=True);objective.backward();optimizer.step()
        if step%100==0:check_budget()
    torch.cuda.synchronize()
    return {'worker':ordinal,'steps':1200,'seconds':time.monotonic()-start,'peak_bytes':torch.cuda.max_memory_allocated(),
        'finite_loss':bool(torch.isfinite(objective)),'device':str(x.device)}

def main():
    setup();require_cuda()
    with job('parallel-throughput-probe',{'steps':1200,'d':100,'source':file_hash(__file__)}) as active:
        if not active:return
        records=[]
        for workers in (1,3,4,6):
            start=time.monotonic()
            with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
                result=list(pool.map(worker,range(workers)))
            seconds=time.monotonic()-start
            records.append({'workers':workers,'wall_seconds_including_startup':seconds,
                'joint_updates_per_second':1200*workers/seconds,'results':result})
            atomic_json(RESULTS/'parallel_profile.json',records)
            print(json.dumps(records[-1]),flush=True)
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
