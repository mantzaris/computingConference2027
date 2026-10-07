"""Conditional acquisition-block uncertainty, only after frozen final evaluation.

These intervals resample observations within each held-out regime. They do not
represent variation across apparatuses or refitted graphs. Model-generated
samples and projection directions remain fixed across bootstrap replicates.
"""
import json
import numpy as np
import pandas as pd
import torch
from .runtime import PROJECT,artifact_root,read_json,atomic_json,Ledger
from .data import load_learner
from .evaluation import load_final_environments
from .metrics import projections

def resample_blocks(n,block,repeats,generator,device):
    if n%block:
        raise ValueError('whole acquisition blocks are required')
    indices=torch.randint(n//block,(repeats,n//block),generator=generator,device=device)
    return (indices[:,:,None]*block+torch.arange(block,device=device)).reshape(repeats,-1)

def projected_bootstrap(observed,prediction_quantiles,indices):
    q=(torch.arange(512,device=observed.device,dtype=observed.dtype)+.5)/512
    chunks=[]
    for offset in range(0,len(indices),8):
        batch=observed[indices[offset:offset+8]].permute(0,2,1)
        empirical=torch.quantile(batch,q,dim=2).permute(1,0,2)
        chunks.append((empirical[:,None]-prediction_quantiles[None]).abs().mean((2,3)))
    return torch.cat(chunks)

@torch.no_grad()
def block_intervals(frame):
    from .experiments import timed_job
    marker=PROJECT/'results/curated/real_block_intervals.csv'
    if marker.exists():
        return pd.read_csv(marker)
    protocol=read_json(PROJECT/'results/curated/frozen_protocol.json')
    cfg=protocol['config']
    selected=frame[(frame.study=='real')&(frame.stage=='selected')&(frame.endpoint=='T2')].reset_index(drop=True)
    if selected.empty:
        return pd.DataFrame()
    item=next(row for row in protocol['matrix'] if row['study']=='real')
    root=artifact_root()/'data/processed'/item['data_id']
    data=load_learner(root,'cuda')
    groups=load_final_environments(data.manifest,root)
    repeats,block=cfg['real_block_bootstrap_replicates'],cfg['real_block_rows']
    job='real-conditional-block-bootstrap'
    output=artifact_root()/'runs/real_block_bootstrap.json'
    def execute():
        by_environment=[]
        for ei,env in enumerate(groups['T2']):
            keep=[j for j in range(data.d) if j not in env.targets]
            seed=item['seed']+170011+ei*31
            v=projections(len(keep),cfg['evaluation_projections'],seed,'cuda')
            q=(torch.arange(512,device='cuda')+.5)/512
            observed=env.x[:,keep]@v
            predictions=[]
            for row in selected.itertuples():
                key=row.evaluation_artifact.rsplit('/',1)[1].removeprefix('evaluation-').removesuffix('.json')
                with np.load(artifact_root()/'generated_samples'/(key+'.npz')) as archive:
                    generated=torch.tensor(archive[env.name],device='cuda')[:,keep]@v
                predictions.append(torch.quantile(generated,q,dim=0))
            prediction_quantiles=torch.stack(predictions)
            generator=torch.Generator(device='cuda').manual_seed(cfg['bootstrap_seed']+ei)
            indices=resample_blocks(len(observed),block,repeats,generator,'cuda')
            by_environment.append(projected_bootstrap(observed,prediction_quantiles,indices).cpu().numpy())
        draws=np.stack(by_environment).mean(0)
        np.savez_compressed(artifact_root()/'generated_samples/real_block_bootstrap.npz',sw1=draws)
        rows=[]
        for i,row in selected.iterrows():
            lo,hi=np.quantile(draws[:,i],[.025,.975])
            rows.append({'run_id':row.run_id,'method':row.method,'metadata_variant':row.metadata_variant,
                         'sw1':row.sw1,'conditional_block_low':float(lo),'conditional_block_high':float(hi),
                         'replicates':repeats,'block_rows':block,'independent_apparatuses':1})
        comparisons=[]
        for variant in ('coherent','anonymous','shuffled'):
            a=selected.index[(selected.method=='diagnostic')&(selected.metadata_variant==variant)][0]
            for comparator in ('fixed','random','llm_edit'):
                b=selected.index[(selected.method==comparator)&(selected.metadata_variant==variant)][0]
                low,high=np.quantile(draws[:,a]-draws[:,b],[.025,.975])
                comparisons.append({'metadata_variant':variant,'comparison':'diagnostic - '+comparator,
                                    'delta':float(selected.iloc[a].sw1-selected.iloc[b].sw1),
                                    'conditional_block_low':float(low),'conditional_block_high':float(high)})
        atomic_json(output,{'models':rows,'paired_comparisons':comparisons,'protocol_hash':protocol['protocol_hash'],
                    'interpretation':'conditional within-regime observation uncertainty; fixed fitted models and generated samples; one apparatus'})
    timed_job(Ledger(),job,{'protocol':protocol['protocol_hash'],'replicates':repeats,'block':block},execute,600)
    report=read_json(output)
    pd.DataFrame(report['models']).to_csv(marker,index=False)
    pd.DataFrame(report['paired_comparisons']).to_csv(PROJECT/'results/curated/real_block_comparisons.csv',index=False)
    return pd.DataFrame(report['models'])
