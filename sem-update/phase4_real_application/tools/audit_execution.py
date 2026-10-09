"""Verify immutable inputs, candidate semantics, selection and prediction records."""
import json
import numpy as np
from sem_update.graphs import DAG
from sem_update.phase2.objectives import select
from app_runtime import ROOT,RESULTS,read_json,file_hash,digest,atomic_json,source_hash,snapshot
from app_data import ROOTS,ROLES,eligible,raw
import pandas as pd

def main():
    protocol=read_json(RESULTS/'protocol.json');seal=read_json(RESULTS/'frozen_selections.json')
    assert protocol['scientific_hash']==source_hash()
    assert seal['protocol_sha256']==file_hash(RESULTS/'protocol.json')
    runs=[r for names in ROLES.values() for r in names];assert len(runs)==len(set(runs))
    banks=0;selections=0;graphs=0;predictions=0
    for name,sha in seal['records'].items():
        assert file_hash(ROOT/name)==sha;record=read_json(ROOT/name)
        m=read_json(ROOT/record['data_folder']/'manifest.json')
        assert m['dataset_hash']==record['dataset_hash']
        assert file_hash(ROOT/record['data_folder']/'learner.npz')==m['arrays_sha256']
        for policy,bh in record['bank_hashes'].items():
            task=(ROOT/name).parent.name;folder=ROOT/'runs'/(task+'-'+policy)
            b=read_json(folder/'bank.json');assert digest({k:v for k,v in b.items() if k!='bank_hash'})==bh
            assert not set(b['construction_partitions'])&{'calibration','audit','final'}
            bank_graphs=[]
            for k,c in b['candidates'].items():
                g=DAG.from_json(c['graph']);assert g.key==k and g.d==11
                assert all(not g.parents(j) for j in ROOTS)
                assert max(len(g.parents(j)) for j in range(g.d))<=3
                bank_graphs.append(g.json());graphs+=1
            s=read_json(ROOT/'runs'/(task+'-'+policy+'-select')/'selection.json')
            assert s['bank_hash']==bh
            for method,row in s['methods'].items():
                if method in ('M3','M4','rho0','random'):
                    chosen,_=select(s['calibration_scores'],b['initial'],row['rho'],protocol['config']['search']['improvement'])
                    assert chosen==row['selected_key']
                selected=row['selected'];before=row['before_audit']
                assert selected==(before if row['audit_pass'] else row['initial'])
                if selected['kind']=='ensemble':
                    assert len(selected['components'])<=3 and min(selected['weights'])>=0
                    assert abs(sum(selected['weights'])-1)<1e-7
                    assert all(g in bank_graphs for g in selected['components'])
                else:assert selected['graph'] in bank_graphs
                selections+=1
            banks+=1
    for path,sha in read_json(ROOT/'sealed_checkpoints.json').items():assert file_hash(ROOT/path)==sha
    for path in (ROOT/'generated_samples').glob('prediction-*.npz'):
        timing=read_json(path.with_suffix('.json'));assert timing['sha256']==file_hash(path)
        with np.load(path) as arrays:
            for name in arrays.files:
                x=arrays[name];assert x.shape==(protocol['config']['evaluation_samples'],11) and np.isfinite(x).all()
                run,arm=name.rsplit('_',1);design=next(r for r in protocol['final_design'] if r['run']==run)
                assignment={**design['nuisance'],design['target']:design['high'] if int(arm) else design['low']}
                for j,c in enumerate(('load_in','load_out','hatch')):assert np.allclose(x[:,j],assignment[c],atol=2e-5)
                predictions+=1
    m=read_json(ROOT/'data/processed/main/manifest.json')
    fitting=m['retained_rows_by_role']['fit'];preprocessing=m['preprocessing_fit_rows']
    total=m['non_test_intervention_rows']+preprocessing-fitting
    result={'passed':True,'frozen_records':len(seal['records']),'verified_banks':banks,'candidate_records':graphs,
        'verified_selections':selections,'prediction_arrays':predictions,'prediction_samples':predictions*protocol['config']['evaluation_samples'],
        'main_model_rows':m['non_test_intervention_rows'],'additional_preprocessing_only_rows':preprocessing-fitting,
        'all_main_non_test_rows':total,'development_rows_examined':14000,
        'all_non_test_including_development':total+14000,'source_rows_in_main_acquisitions':140000,
        'reporting_correction':'Frozen non_test_intervention_rows counts modeling rows. One additional fit-only row used in standardization is also charged; no fitting or selection changed.',
        'protocol_sha256':file_hash(RESULTS/'protocol.json'),'scientific_hash':source_hash()}
    atomic_json(RESULTS/'execution_audit.json',result);atomic_json(ROOT/'runtime_snapshot.json',snapshot())
    print(json.dumps(result))

if __name__=='__main__':main()
