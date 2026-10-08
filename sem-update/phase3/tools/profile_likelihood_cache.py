"""Validate the demonstrated mask-cache optimization on frozen development fits."""
import gc
import importlib.util
import json
import tarfile
import time
from pathlib import Path
import numpy as np
import torch
from sem_update.flows import Mechanism
from sem_update.graphs import DAG
from sem_update.phase3.flows import FastSCM
from sem_update.phase3.runtime import setup,require_cuda,root,RESULTS,job,read_json,atomic_json,file_hash
from sem_update.phase3.data import load

def main():
    setup();require_cuda();folder=root()/'cache_memory_probe';folder.mkdir(exist_ok=True)
    source=root()/'archives/pilot_source.tar.gz'
    with tarfile.open(source) as archive:
        names=[m for m in archive.getmembers() if m.name.endswith('/phase3/flows.py')]
        assert len(names)==1
        old_path=folder/'pilot_flows.py';old_path.write_bytes(archive.extractfile(names[0]).read())
    spec=importlib.util.spec_from_file_location('sem_update.phase3._archived_pilot_flows',old_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bank=read_json(root()/'runs/sparse-heteroscedastic-d100-s390100-B400-c0.5-diagnostic/bank.json')
    record=read_json(root()/'runs/sparse-heteroscedastic-d100-s390100-B400-c0.5/adjusted-frozen.json')
    data=load(root()/record['data_folder'],allowed=('fit',));x=data.get('fit')[0].x[:64]
    masks=[()]+[(j,) for j in data.manifest['seen_targets']];cfg=record['config']['train']
    identity={'pilot_bank':bank['bank_hash'],'source':file_hash(__file__),'current_flows':file_hash(__import__('sem_update.phase3.flows',fromlist=['__file__']).__file__)}
    records=[];outputs=[]
    with job('likelihood-cache-memory-probe',identity) as active:
        if not active:return
        for label,cls in [('archived_pilot',module.FastSCM),('bounded_masks',FastSCM)]:
            gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats();models=[];values=[]
            start=time.monotonic()
            for candidate in bank['candidates'].values():
                graph=DAG.from_json(candidate['graph']);mechanisms=[]
                for j,fit in enumerate(candidate['fits']):
                    model=Mechanism(graph.parents(j),cfg['width'],cfg['bins'],cfg['transforms']).cuda()
                    ck=torch.load(root()/'checkpoints'/(fit['key']+'.pt'),map_location='cuda',weights_only=False)
                    model.load_state_dict(ck['best_state']);mechanisms.append(model)
                models.append(cls(graph,mechanisms))
            with torch.no_grad():
                for model in models:
                    values.append(torch.stack([model.log_probability(x,mask).sum(1) for mask in masks]).cpu().numpy())
            torch.cuda.synchronize()
            records.append({'version':label,'graphs':len(models),'masks_per_graph':len(masks),'rows':len(x),
                'seconds_including_load':time.monotonic()-start,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                'retained_allocated_bytes':torch.cuda.memory_allocated(),'reserved_bytes':torch.cuda.memory_reserved()})
            outputs.append(np.stack(values));del models,model,mechanisms,ck
        np.testing.assert_allclose(outputs[0],outputs[1],rtol=0,atol=0)
        np.savez_compressed(folder/'densities.npz',archived=outputs[0],bounded=outputs[1])
        value={'passed':True,'exact_density_equality':True,'records':records,'pilot_only':True,
            'source_sha256':identity['current_flows'],'artifact':'cache_memory_probe/densities.npz',
            'artifact_sha256':file_hash(folder/'densities.npz'),'scope':'No fitting or hidden main outcomes; only parameter-cache lifetime changes'}
        atomic_json(RESULTS/'likelihood_cache_profile.json',value);print(json.dumps(value,indent=2))

if __name__=='__main__':main()
