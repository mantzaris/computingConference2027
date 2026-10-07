"""Download via authors' package and inspect real schema before subset design."""
import importlib.metadata
from pathlib import Path
import urllib.request
import pandas as pd
import numpy as np
from .runtime import artifact_root,PROJECT,atomic_json,file_hash

DATASET='lt_interventions_standard_v1'
BASE='https://raw.githubusercontent.com/juangamella/causal-chamber/main/datasets/'+DATASET+'/'

def audit():
    from causalchamber.datasets import Dataset
    root=artifact_root()/'data/raw'
    dataset=Dataset(DATASET,root=str(root),download=True)
    folder=root/DATASET
    protocol=root/'protocol'
    protocol.mkdir(exist_ok=True)
    for filename in ('README.md','variables.csv','generators/uniform.py'):
        target=protocol/Path(filename).name
        if not target.exists():
            urllib.request.urlretrieve(BASE+filename,target)
    records=[]
    schema=None
    for path in sorted(folder.glob('*.csv')):
        frame=pd.read_csv(path)
        if schema is None:
            schema={c:str(t) for c,t in frame.dtypes.items()}
        records.append({'name':path.stem,'rows':len(frame),'columns':list(frame.columns),
                        'missing':int(frame.isna().sum().sum()),'sha256':file_hash(path),'bytes':path.stat().st_size,
                        'time_columns':[c for c in frame if 'time' in c or 'timestamp' in c]})
    report={'dataset':DATASET,'package_version':importlib.metadata.version('causalchamber'),
            'source':BASE,'license':'CC BY 4.0 (authors dataset repository)',
            'schema':schema,'experiments':records,
            'protocol_files':{p.name:file_hash(p) for p in protocol.iterdir() if p.is_file()},
            'selection_status':'schema audit only; causal subset/splits require protocol review'}
    atomic_json(PROJECT/'results/curated/dataset_audit.json',report)
    return report

if __name__=='__main__':
    print(audit())

VARIABLES=['red','green','blue','current','pol_1','angle_1']

def prepare(budget=400):
    """Restricted current/position case: no omitted varying optical LED causes.

    Raw final rows are indexed in a sealed manifest, never placed in learner.npz.
    The single apparatus and quantized measurements limit causal interpretation.
    """
    from .runtime import digest,read_json
    from .data import validate_splits
    root=artifact_root()/'data/processed'/f'chambers-B{budget}'
    root.mkdir(exist_ok=True,parents=True)
    if (root/'manifest.json').exists():
        if read_json(root/'manifest.json').get('budget_accounting_version')!=2:
            raise RuntimeError('archive the pre-freeze real manifest and arrays, then prepare with explicit reference-regime accounting')
        return root
    raw=artifact_root()/'data/raw'/DATASET
    ref=pd.read_csv(raw/'uniform_reference.csv')
    train=ref.iloc[:4096]
    # Protocol assignment blocks contain one measurement each; conservative
    # ten-row reporting blocks and gaps address potential serial dependence.
    acf={c:[float(train[c].autocorr(lag=k)) for k in range(1,65)] for c in VARIABLES}
    threshold=3/np.sqrt(len(train))
    crossing=next((k for k in range(1,57) if all(abs(v)<threshold for c in VARIABLES for v in acf[c][k-1:k+7])),64)
    gap=max(64,crossing)
    quantum=np.array([1.,1.,1.,1.,.9,1.])
    def dequant(frame,seed):
        x=frame[VARIABLES].to_numpy(dtype=float)
        return x+(np.random.default_rng(seed).random(x.shape)-.5)*quantum
    ref_values=dequant(ref,34010)
    mu,sd=ref_values[:4096].mean(0),ref_values[:4096].std(0).clip(1e-6)
    def assignment(j,lo,hi):
        return {str(j):{'kind':'discrete_uniform_dequantized','low':lo,'high':hi,'quantum':1.,
                         'location':float(mu[j]),'spread':float(sd[j])}}
    arrays,splits={},dict(fit=[],early=[],search=[],audit=[])
    final=[]
    selected=['uniform_reference']+[f'uniform_{color}_{level}' for color in VARIABLES[:3] for level in ('mid','strong')]
    settings={}
    for name in selected:
        frame=ref if name=='uniform_reference' else pd.read_csv(raw/(name+'.csv'))
        settings[name]={c:sorted(map(float,frame[c].unique())) for c in ['osr_c','v_c','osr_angle_1','v_angle_1']}
        if settings[name]!={'osr_c':[1.],'v_c':[5.],'osr_angle_1':[1.],'v_angle_1':[5.]}:
            raise ValueError('measurement parameters are not fixed as expected')
    obs_ranges=dict(fit=(0,4096),early=(4200,5224),search=(5330,6354),audit=(6460,6972))
    mid_ranges=dict(fit=(0,int(.6*budget)),early=(304,304+int(.1*budget)),
                    search=(408,408+int(.2*budget)),audit=(552,552+int(.1*budget)))
    for role in splits:
        for j,name in [(-1,'uniform_reference')]+[(j,f'uniform_{c}_mid') for j,c in enumerate(VARIABLES[:3])]:
            a,b=obs_ranges[role] if j<0 else mid_ranges[role]
            frame=ref if j<0 else pd.read_csv(raw/(name+'.csv'))
            values=ref_values if j<0 else dequant(frame,34020+j)
            key=role+'_'+name
            arrays[key]=((values[a:b]-mu)/sd).astype('float32')
            splits[role].append({'name':'obs' if j<0 else name,'array':key,'assignments':{} if j<0 else assignment(j,86,170),
                                 'row_ids':[f'{name}:{i}' for i in range(a,b)],'blocks':sorted({i//10 for i in range(a,b)})})
    final.append({'name':'uniform_reference','endpoint':'observational','start':7100,'stop':8124,'assignments':{},'dequant_seed':34010})
    for j,color in enumerate(VARIABLES[:3]):
        final.append({'name':f'uniform_{color}_mid','endpoint':'T1','start':656,'stop':1000,
                      'assignments':assignment(j,86,170),'dequant_seed':34020+j})
        final.append({'name':f'uniform_{color}_strong','endpoint':'T2','start':0,'stop':1000,
                      'assignments':assignment(j,171,255),'dequant_seed':34030+j})
    reference_rows=sum(b-a for a,b in obs_ranges.values())
    manifest={'id':f'chambers-B{budget}','d':6,'family':'real','seed':34001,'budget_per_target':budget,
              'budget_accounting_version':2,'non_test_intervention_rows':reference_rows+3*budget,
              'non_test_reference_policy_rows':reference_rows,'non_test_target_regime_rows':3*budget,
              'budget_definition':'B is per additional mid-RGB target regime; total experimental observations also count randomized reference rows',
              'seen_targets':[0,1,2],'root_nodes':[0,1,2,4],
              'standardization':{'mean':mu.tolist(),'std':sd.tolist()},'splits':splits,
              'variables':VARIABLES,'dequantization_quantum':quantum.tolist(),'development':False,
              'source_checksums':{name:file_hash(raw/(name+'.csv')) for name in selected},
              'split_gap_rows':gap,'reporting_block_rows':10,'independent_apparatuses':1,
              'assignment_calibration_outcome_rows':0,'T3_available':False}
    # Include final IDs only for overlap validation; keep final loader separate.
    checking={'splits':{**splits,'test':[{'name':r['name'],'row_ids':[f'{r["name"]}:{i}' for i in range(r['start'],r['stop'])]} for r in final]}}
    validate_splits(checking)
    np.savez_compressed(root/'learner.npz',**arrays)
    manifest['arrays_sha256']=file_hash(root/'learner.npz')
    manifest['dataset_hash']=digest(manifest)
    atomic_json(root/'manifest.json',manifest)
    atomic_json(root/'sealed_test_design.json',final)
    atomic_json(PROJECT/'results/curated/real_split_audit.json',{'variables':VARIABLES,'settings':settings,
                'training_autocorrelations':acf,'gap_rows':gap,'block_rows':10,
                'reference_intervals':obs_ranges,'intervention_intervals':mid_ranges,'final_design':final,
                'limitations':['one apparatus','one acquisition run per regime','block uncertainty is conditional',
                'quantized/dequantized measurements','root position firmware quantization','no real unseen-target endpoint'],
                'reference_edges_for_postselection_display_only':[[0,3],[1,3],[2,3],[4,5]]})
    return root
