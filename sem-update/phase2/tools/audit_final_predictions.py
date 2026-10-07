#!/usr/bin/env python3
"""Verify frozen specifications, final numerical tables, and saved CUDA samples."""
import json
import math
import hashlib
import numpy as np
import pandas as pd
from sem_update.phase2.runtime import RESULTS,root,freeze_guard,read_json,digest,file_hash,atomic_json

def main():
    protocol=freeze_guard();cfg=protocol['config']
    if not (RESULTS/'final_test_access.json').exists():
        raise RuntimeError('Final evaluation has not opened; this audit must wait')
    frozen=read_json(RESULTS/'frozen_selections.json')
    assert file_hash(RESULTS/'selected_models.json')==frozen['selected_models_sha256']
    tasks={t['task_id']:t for t in read_json(RESULTS/'selected_models.json')['tasks']}
    frame=pd.read_csv(RESULTS/'metrics.csv')
    if frame.empty:raise RuntimeError('Completed final metrics are required')
    assert not frame.duplicated(['task_id','method','stage','endpoint']).any()
    expected_main={(task,method) for task in tasks for method in ['M0','M1','M2','M3','M4','M5']}
    observed_main=set(zip(frame.loc[(frame.stage=='selected')&(frame.endpoint=='T2'),'task_id'],
                          frame.loc[(frame.stage=='selected')&(frame.endpoint=='T2'),'method']))
    assert expected_main<=observed_main
    expected_all={(task,method) for task,t in tasks.items() for method in t['methods']}
    assert observed_main==expected_all
    target_hashes={};sample_files=set();environment_count=0;generated_rows=0
    artifacts=[]
    for path,part in frame.groupby('evaluation_artifact'):
        source=root()/path;value=read_json(source);source_sha=file_hash(source)
        assert part.evaluation_sha256.eq(source_sha).all()
        assert part.data_id.nunique()==1
        for (_,method,stage),group in part.groupby(['task_id','method','stage']):
            required=set(value['endpoints'])
            if stage=='before_audit':required&={'T2','T2_exploratory'}
            if method.startswith('checkpoint_'):required={'T2'}
            assert set(group.endpoint)==required
        for row in part.itertuples():
            task=tasks[row.task_id];spec=task['methods'][row.method][row.stage]
            assert digest(spec)==row.model_hash and spec['kind']==row.model_kind
            expected=value['endpoints'][row.endpoint]
            for metric,number in expected.items():
                actual=getattr(row,metric)
                if number is None:
                    assert metric=='nll' and row.method=='M0' and pd.isna(actual)
                else:
                    assert math.isfinite(number) and math.isfinite(float(actual))
                    assert np.isclose(actual,number,rtol=5e-9,atol=1e-10),(row.task_id,metric)
            assert row.sw1>=0 and row.worst_regime_sw1>=0
        sample_path=root()/'generated_samples'/(source.stem+'.npz')
        sample_sha=file_hash(sample_path)
        assert sample_sha==value['sample_sha256'] and part.sample_sha256.eq(sample_sha).all()
        assert value['generated_samples_per_environment']==cfg['evaluation_samples']
        with np.load(sample_path) as arrays:
            assert set(arrays.files)=={e['environment'] for e in value['environments']}
            d=int(part.iloc[0].d);data_id=part.iloc[0].data_id
            for e in value['environments']:
                y=arrays[e['environment']]
                assert y.shape==(cfg['evaluation_samples'],d) and np.isfinite(y).all()
                assert e['generated_rows']==len(y) and e['actual_rows']>0
                targets=[j for j in range(d) if j not in e['non_target_nodes']]
                for j in targets:
                    key=(data_id,e['environment'],j)
                    sha=hashlib.sha256(np.ascontiguousarray(y[:,j]).tobytes()).hexdigest()
                    if key in target_hashes:assert target_hashes[key]==sha,'Unequal target draws across methods'
                    else:target_hashes[key]=sha
                environment_count+=1;generated_rows+=len(y)
        sample_files.add(sample_path.name)
        artifacts.append({'path':path,'sha256':source_sha,'samples_sha256':sample_sha,
                          'curated_rows':len(part),'environments':len(value['environments'])})
    result={'passed':True,'metric_rows':len(frame),'six_main_conditions':len(expected_main),
        'all_frozen_method_conditions':len(expected_all),
        'unique_prediction_artifacts':len(artifacts),'sample_archives':len(sample_files),
        'unique_model_environment_predictions':environment_count,'generated_observations_in_checked_archives':generated_rows,
        'target_design_streams_checked':len(target_hashes),
        'metrics_sha256':file_hash(RESULTS/'metrics.csv'),'protocol_hash':protocol['protocol_hash'],
        'checks':['complete six-method and supplementary T2 coverage','unique task/method/stage/endpoint rows',
                  'all prescribed endpoints retained',
                  'frozen specification identity','finite and faithfully rounded endpoint metrics',
                  'empirical-control NLL unavailable','saved sample SHA256 and finite values',
                  'equal final sample counts including mixtures','identical prescribed target draws across methods'],
        'scope':'CPU integrity audit of already executed CUDA predictions; no new fitting, sampling, selection or tuning'}
    atomic_json(root()/'runs/final_prediction_integrity.json',{'summary':result,'artifacts':artifacts})
    atomic_json(RESULTS/'final_prediction_audit.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
