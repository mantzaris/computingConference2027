#!/usr/bin/env python3
"""Reconstruct sealed reference arrays after evaluation for durable preservation.

Uses the frozen loader and seeds, verifies the actually reported reference
means, and records that these arrays were reconstructed after evaluation.
Never fits a model or alters an evaluation result.
"""
import ast
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sem_update.cli import require_cuda
from sem_update.evaluation import load_final_environments
from sem_update.experiments import implementation_hash,timed_job
from sem_update.runtime import PROJECT,artifact_root,read_json,atomic_json,file_hash,Ledger

def main():
    require_cuda()
    protocol=read_json(PROJECT/'results/curated/frozen_protocol.json')
    completed=read_json(PROJECT/'results/curated/evaluation_complete.json')
    if completed['status']!='complete' or implementation_hash()!=protocol['implementation_hash']:
        raise RuntimeError('completed evaluation and unchanged frozen implementation required')
    if completed['metrics_sha256']!=file_hash(PROJECT/'results/curated/metrics.csv'):
        raise RuntimeError('evaluation metrics changed')
    evidence=pd.read_csv(artifact_root()/'runs/evaluation_environment_metrics.csv')
    output=PROJECT/'results/curated/final_reference_preservation.json'
    def execute():
        rows=[]
        with torch.no_grad():
            for item in protocol['matrix']:
                root=artifact_root()/'data/processed'/item['data_id']
                manifest=read_json(root/'manifest.json')
                if manifest['dataset_hash']!=item['data_hash']:
                    raise RuntimeError('dataset identity changed')
                groups=load_final_environments(manifest,root,'cuda')
                arrays={}
                references=evidence[evidence.data_id==item['data_id']]
                for environments in groups.values():
                    for env in environments:
                        record=references[references.environment==env.name].iloc[0]
                        nodes=ast.literal_eval(record.non_target_nodes)
                        expected=torch.tensor(ast.literal_eval(record.outcome_means_actual),device='cuda')
                        actual=env.x[:,nodes].mean(0)
                        torch.testing.assert_close(actual,expected,rtol=0,atol=1e-7)
                        if len(env.x)!=int(record.actual_rows):
                            raise RuntimeError('reference row count differs from evaluation')
                        arrays[env.name]=env.x.cpu().numpy()
                destination=artifact_root()/'generated_samples'/('final-reference-'+item['data_id']+'.npz')
                np.savez_compressed(destination,**arrays)
                rows.append({'data_id':item['data_id'],'data_hash':item['data_hash'],
                             'artifact':str(destination.relative_to(artifact_root())),
                             'sha256':file_hash(destination),'environment_count':len(arrays),
                             'reported_reference_means_verified':True})
        atomic_json(output,{'protocol_hash':protocol['protocol_hash'],'datasets':rows,
                    'provenance':'reconstructed after evaluation using frozen loader, seeds and data; reported means and row counts verified',
                    'no_new_fitting_or_selection':True,'device':'cuda'})
    timed_job(Ledger(),'preserve-final-reference-arrays',{'protocol':protocol['protocol_hash']},execute,120)
    if not output.exists():
        raise RuntimeError('completed preservation job lacks its manifest')
    print(json.dumps({'datasets':len(read_json(output)['datasets']),'manifest':str(output)},indent=2))

if __name__=='__main__':
    main()
