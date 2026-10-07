#!/usr/bin/env python3
"""Verify actual non-test arrays, split hashes and budgets without final outcomes."""
import json
import numpy as np
import pandas as pd
from sem_update.data import validate_splits
from sem_update.phase2.data import partition_hashes,training_identity
from sem_update.phase2.runtime import root,RESULTS,PROJECT,freeze_guard,read_json,file_hash,atomic_json

def main():
    protocol=freeze_guard();rows=[];seeds={};archives=[]
    previous=read_json(PROJECT/'results/curated/frozen_protocol.json')
    old_seeds={item['seed'] for item in previous['matrix'] if item['study']!='real'}
    for item in protocol['matrix']:
        folder=root()/'data/processed'/item['data_id'];manifest=read_json(folder/'manifest.json')
        assert file_hash(folder/'manifest.json')==item['manifest_sha256']
        assert file_hash(folder/'learner.npz')==manifest['arrays_sha256']
        validate_splits(manifest);arrays=np.load(folder/'learner.npz')
        assert partition_hashes(manifest,arrays)==manifest['partition_hashes']
        assert training_identity(manifest)==manifest['dataset_hash']==item['data_hash']
        total=0
        for role,environments in manifest['splits'].items():
            ordinary=targeted=0
            for environment in environments:
                x=arrays[environment['array']]
                assert x.shape==(len(environment['row_ids']),item['d']) and np.isfinite(x).all()
                if environment['assignments']:targeted+=len(x)
                else:ordinary+=len(x)
            counted=targeted+(ordinary if item['study']=='real' else 0);total+=counted
            rows.append({k:item[k] for k in ('data_id','study','family','d','seed','budget')}|
                {'partition':role,'reference_rows':ordinary,'targeted_rows':targeted,
                 'counted_intervention_rows':counted,'partition_sha256':manifest['partition_hashes'][role]})
        assert total==manifest['non_test_intervention_rows']
        if item['study']!='real':
            assert item['seed'] not in old_seeds
            seeds.setdefault(item['study'],set()).add(item['seed'])
        archives.append({'data_id':item['data_id'],'arrays_sha256':manifest['arrays_sha256'],
                         'measured_intervention_rows':total,'all_five_partitions_counted':True})
        arrays.close()
    pd.DataFrame(rows).to_csv(RESULTS/'measured_sample_budgets.csv',index=False)
    result={'complete':True,'datasets':len(archives),'final_outcomes_loaded':False,
        'independent_scms':{k:len(v) for k,v in seeds.items()},'historical_seed_overlap':[],
        'protocol_hash':protocol['protocol_hash'],'datasets_verified':archives}
    atomic_json(RESULTS/'input_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='datasets_verified'},indent=2))

if __name__=='__main__':main()
