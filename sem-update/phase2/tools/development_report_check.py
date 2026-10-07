#!/usr/bin/env python3
"""Exercise reporting on completed development pilots, never main outcomes."""
import json
import time
import pandas as pd
import torch
from sem_update.phase2 import reporting as r
from sem_update.phase2.runtime import PHASE,RESULTS,root,read_json,atomic_json,file_hash,freeze_guard

def main():
    if torch.cuda.is_available():raise RuntimeError('Hide CUDA for this reporting-only check')
    protocol=freeze_guard();start=time.monotonic()
    destination=root()/'runs/reporting-development-v2'
    destination.mkdir(parents=True,exist_ok=True)
    r.RESULTS=destination;r.PHASE=destination
    (destination/'paper/tables').mkdir(parents=True,exist_ok=True)
    frames=[pd.read_csv(p) for p in sorted((root()/'runs/development').glob('*-metrics.csv'))]
    frame=pd.concat(frames,ignore_index=True)
    if not frame.seed.isin([295001,295002]).all():raise RuntimeError('Only the two original timed pilots are permitted')
    # The pilots predate the explicit incremental-attribution output column.
    if 'actual_incremental_seconds' not in frame:frame['actual_incremental_seconds']=float('nan')
    tasks=[]
    for data_id in sorted(frame.data_id.unique()):
        tasks.extend(read_json(root()/'runs/datasets'/data_id/'complete.json')['tasks'])
    cfg=read_json(PHASE/'configs/pilots.json')
    summary,table=r.method_table(frame,cfg);reliability,pairs=r.repair_table(frame,cfg)
    core=frame[(frame.stage=='selected')&(frame.endpoint=='T2')]
    comparisons=r.primary_comparisons(core,cfg);checkpoints=r.checkpoint_table(frame,cfg)
    r.analysis_tables(frame,summary,pairs,tasks,cfg);r.latex_tables(table,reliability);r.method_overview(cfg)
    record={'complete':True,'main_outcomes_accessed':False,'cuda_visible':False,
        'development_scms':sorted(map(int,frame.seed.unique())),'metric_rows':len(frame),
        'six_method_rows':len(table),'primary_comparisons':len(comparisons),
        'repair_summary_rows':len(reliability),'checkpoint_summary_rows':len(checkpoints),
        'seconds':time.monotonic()-start,'frozen_scientific_hash_verified':protocol['scientific_hash'],
        'reporting_sha256':file_hash(r.__file__),'test_count':5,
        'test_log':'.artifacts/phase2/logs/reporting_cpu_tests.log',
        'outputs':str(destination.relative_to(root()))}
    atomic_json(RESULTS/'reporting_validation.json',record);print(json.dumps(record,indent=2))

if __name__=='__main__':main()
