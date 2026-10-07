"""Disjoint fit/early/search/calibration/audit views and fresh synthetic systems."""
from pathlib import Path
import hashlib
import numpy as np
import torch
from sem_update.data import SyntheticSCM,Environment,validate_splits
from .runtime import root,atomic_json,read_json,digest,file_hash,PROJECT,RESULTS

ROLES=('fit','early','search','calibration','audit')
FRACTIONS=dict(zip(ROLES,(.5,.1,.2,.1,.1)))
OBS_COUNTS=dict(zip(ROLES,(4096,1024,1024,512,512)))

def partition_hashes(manifest,arrays):
    return {role:digest([{'environment':e,'array_sha256':hashlib.sha256(np.ascontiguousarray(arrays[e['array']]).tobytes()).hexdigest()}
                         for e in environments]) for role,environments in manifest['splits'].items()}

def training_identity(manifest):
    return digest({'id':manifest['id'],'d':manifest['d'],'standardization':manifest['standardization'],
        'fit':manifest['partition_hashes']['fit'],'early':manifest['partition_hashes']['early'],
        'cache_identity_version':2})

def seal_manifest(manifest,arrays,folder):
    manifest['arrays_sha256']=file_hash(folder/'learner.npz')
    manifest['partition_hashes']=partition_hashes(manifest,arrays)
    manifest['cache_identity_version']=2;manifest['dataset_hash']=training_identity(manifest)
    return manifest

class Data:
    def __init__(self,manifest,arrays,device,allowed=ROLES):
        self.manifest=manifest;self.key=manifest['dataset_hash'];self.d=manifest['d']
        self.preprocessing_hash=digest(manifest['standardization']);self.allowed=tuple(allowed)
        self.roles={r:[Environment(e['name'],torch.as_tensor(arrays[e['array']],device=device),
                    e['assignments'],tuple(e['row_ids']),tuple(e.get('blocks',())))
                    for e in manifest['splits'][r]] for r in allowed}
    def get(self,role):
        if role not in self.allowed:
            raise ValueError('Partition is not available in this learner view: '+role)
        return self.roles[role]

def load(path,device='cuda',allowed=ROLES):
    path=Path(path);m=read_json(path/'manifest.json');validate_splits(m)
    if file_hash(path/'learner.npz')!=m['arrays_sha256']:raise ValueError('Data checksum mismatch')
    return Data(m,np.load(path/'learner.npz'),device,allowed)

def prepare(d,family,seed,budget,development=False,semantic=False):
    ident=f'p2-{"dev" if development else "main"}-{family}-d{d}-s{seed}-B{budget}'+('-semantic' if semantic else '')
    folder=root()/'data/processed'/ident;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'manifest.json').exists():return folder
    scm=SyntheticSCM(d,family,seed,semantic)
    # Generation occurs on CUDA, with independent fresh role streams. Prefixes
    # of maximum-length draws keep the two budgets nested within each role.
    obs=scm.sample(4096,seed*1000+10,device='cuda').cpu().numpy()
    mu,sd=obs.mean(0),obs.std(0).clip(1e-5)
    seen=[0,1,2] if semantic else sorted(map(int,np.random.default_rng(seed+8723).choice(d,3 if d==5 else 6,replace=False)))
    arrays={};splits={}
    for ri,role in enumerate(ROLES):
        x=scm.sample(OBS_COUNTS[role],seed*1000+10+ri,device='cuda').cpu().numpy()
        key=role+'_obs';arrays[key]=((x-mu)/sd).astype('float32')
        splits[role]=[{'name':'obs','array':key,'assignments':{},'row_ids':[f'{seed}:obs:{role}:{i}' for i in range(len(x))]}]
        for j in seen:
            n=int(budget*FRACTIONS[role])
            law={j:{'kind':'normal','mean':float(mu[j]+sd[j]),'scale':float(.25*sd[j])}}
            x=scm.sample(400,seed*1000+100+ri*20+j,law,device='cuda').cpu().numpy()[:n]
            key=f'{role}_do{j}';arrays[key]=((x-mu)/sd).astype('float32')
            splits[role].append({'name':f'do{j}+','array':key,'assignments':{str(j):{'kind':'normal','mean':1.,'scale':.25}},
                                 'row_ids':[f'{seed}:do{j}:{role}:{i}' for i in range(n)]})
    manifest={'id':ident,'d':d,'family':family,'seed':seed,'budget_per_target':budget,
        'non_test_intervention_rows':len(seen)*budget,'seen_targets':seen,'development':development,'semantic':semantic,
        'standardization':{'mean':mu.tolist(),'std':sd.tolist()},'splits':splits,'phase':2,
        'generator':'unchanged historical SyntheticSCM; fresh graph/mechanism/observation seed',
        'root_nodes':[0,1,2] if semantic else [],'assignment_calibration_outcome_rows':0}
    validate_splits(manifest)
    np.savez_compressed(folder/'learner.npz',**arrays)
    seal_manifest(manifest,arrays,folder)
    atomic_json(folder/'manifest.json',manifest);atomic_json(folder/'truth.json',scm.json())
    return folder

def prepare_real():
    """Unused polarizer regimes, plus separately labeled exploratory RGB tests."""
    import pandas as pd
    from sem_update.chambers import DATASET,VARIABLES
    folder=root()/'data/processed/p2-chambers-B400';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'manifest.json').exists():return folder
    raw=PROJECT/'.artifacts/data/raw'/DATASET
    old=read_json(PROJECT/'.artifacts/data/processed/chambers-B400/manifest.json')
    quantum=np.array(old['dequantization_quantum'])
    ref_ranges=dict(fit=(0,3400),early=(4200,5224),search=(5330,6354),calibration=(3500,4012),audit=(6460,6972))
    mid_ranges=dict(fit=(0,200),early=(304,344),search=(408,488),calibration=(656,696),audit=(552,592))
    targets=[(0,'red'),(1,'green'),(2,'blue'),(4,'pol_1')]
    selected=['uniform_reference']+[f'uniform_{c}_mid' for j,c in targets]
    values={};temporal={};settings={}
    for name in selected:
        # Do not even load the final T1/reference rows into the preparation view.
        prefix=max(b for a,b in (ref_ranges if name=='uniform_reference' else mid_ranges).values())
        frame=pd.read_csv(raw/(name+'.csv'),nrows=prefix)
        if frame.isna().any().any():raise ValueError('Missing real measurements')
        for col,expected in [('osr_c',1.),('v_c',5.),('osr_angle_1',1.),('v_angle_1',5.)]:
            if set(frame[col].unique())!={expected}:raise ValueError('Measurement settings changed')
        settings[name]={col:sorted(map(float,frame[col].unique())) for col in ('osr_c','v_c','osr_angle_1','v_angle_1')}
        fit_frame=frame.iloc[:3400 if name=='uniform_reference' else 200]
        design=np.column_stack([np.ones(len(fit_frame)),fit_frame[['red','green','blue','pol_1']].to_numpy(float)])
        temporal[name]={}
        def acf(vector):
            values=[float(pd.Series(vector).autocorr(lag=k)) for k in (1,5,10,20,50)]
            return [v if np.isfinite(v) else None for v in values]
        for col in VARIABLES:
            vector=fit_frame[col].to_numpy(float)
            residual=vector-design@np.linalg.lstsq(design,vector,rcond=None)[0] if col in ('current','angle_1') else vector
            temporal[name][col]={'rows':len(vector),'lags':[1,5,10,20,50],
                'raw_acf':acf(vector),'residual_acf':acf(residual)}
        seed=34010 if name=='uniform_reference' else 34020+next(j for j,c in targets if name==f'uniform_{c}_mid')
        values[name]=frame[VARIABLES].to_numpy(float)+(np.random.default_rng(seed).random((len(frame),len(VARIABLES)))-.5)*quantum
    mu=values['uniform_reference'][:3400].mean(0);sd=values['uniform_reference'][:3400].std(0).clip(1e-6)
    def assignment(j,low,high):
        if j==4:return {'4':{'kind':'recorded_design'}}
        return {str(j):{'kind':'discrete_uniform_dequantized','low':low,'high':high,'quantum':1.,'location':float(mu[j]),'spread':float(sd[j])}}
    arrays={};splits={}
    for role in ROLES:
        splits[role]=[]
        for j,name in [(-1,'uniform_reference')]+[(j,f'uniform_{c}_mid') for j,c in targets]:
            a,b=ref_ranges[role] if j<0 else mid_ranges[role]
            key=role+'_'+name;arrays[key]=((values[name][a:b]-mu)/sd).astype('float32')
            law={} if j<0 else assignment(j,86,170)
            if j==4:law['4']['values']=arrays[key][:,4].tolist()
            splits[role].append({'name':'obs' if j<0 else name,'array':key,'assignments':law,
                'row_ids':[f'{name}:{i}' for i in range(a,b)],'blocks':list(range(a//10,(b-1)//10+1))})
    designs=[{'name':'uniform_reference','endpoint':'observational','start':7100,'stop':8124,'assignments':{},'dequant_seed':34010,'phase1_exposed':True}]
    for j,c in targets:
        designs += [{'name':f'uniform_{c}_mid','endpoint':'T1' if j==4 else 'T1_exploratory','start':760,'stop':1000,
                     'assignments':assignment(j,86,170),'dequant_seed':34020+j,'phase1_exposed':j!=4},
                    {'name':f'uniform_{c}_strong','endpoint':'T2' if j==4 else 'T2_exploratory','start':0,'stop':1000,
                     'assignments':assignment(j,171,255),'dequant_seed':34030+j,'phase1_exposed':j!=4}]
    validate_splits({'splits':{**splits,'final':[{'name':r['name'],'row_ids':[f'{r["name"]}:{i}' for i in range(r['start'],r['stop'])],
                'blocks':list(range(r['start']//10,(r['stop']-1)//10+1))} for r in designs]}})
    count=sum(b-a for a,b in ref_ranges.values())
    files=selected+[f'uniform_{c}_strong' for j,c in targets]
    manifest={'id':'p2-chambers-B400','d':6,'family':'real','seed':244001,'budget_per_target':400,
        'non_test_intervention_rows':count+1600,'non_test_reference_policy_rows':count,'seen_targets':[0,1,2,4],
        'root_nodes':[0,1,2,4],'standardization':{'mean':mu.tolist(),'std':sd.tolist()},'splits':splits,
        'variables':VARIABLES,'dequantization_quantum':quantum.tolist(),'development':False,'semantic':False,
        'phase':2,'exploratory_RGB':True,'new_regime_T2':'uniform_pol_1_strong',
        'new_regime_scope':'Previously schema/checksum audited, but never fitted, selected or outcome-scored in phase one; known apparatus and phase-one-informed design',
        'motor_assignment':'Conditional prediction for recorded firmware-quantized setpoints; same assignment draws for all methods',
        'source_checksums':{n:file_hash(raw/(n+'.csv')) for n in files},'reporting_block_rows':10,'independent_apparatuses':1}
    np.savez_compressed(folder/'learner.npz',**arrays)
    seal_manifest(manifest,arrays,folder)
    atomic_json(folder/'sealed_test_design.json',designs)
    manifest['sealed_test_design_sha256']=file_hash(folder/'sealed_test_design.json')
    atomic_json(folder/'manifest.json',manifest)
    atomic_json(RESULTS/'real_preselection_audit.json',{'variables':VARIABLES,'settings':settings,
        'training_only_autocorrelations':temporal,'reference_ranges':ref_ranges,'target_ranges':mid_ranges,
        'final_design_sha256':manifest['sealed_test_design_sha256'],'non_test_intervention_rows':manifest['non_test_intervention_rows'],
        'heldout_outcomes_loaded':False,'block_rows':10,'guard_gaps_at_least':64,
        'interpretation':'Temporal diagnostics use fitting rows only; finite sample ACF does not prove independence. One acquisition per regime, one apparatus.'})
    return folder

def final_environments(folder,device='cuda'):
    """Called only behind the phase-two selection freeze, except development."""
    from sem_update.evaluation import load_final_environments
    folder=Path(folder);m=read_json(folder/'manifest.json')
    if m['family']!='real':return load_final_environments(m,folder,device)
    import pandas as pd
    from sem_update.chambers import DATASET,VARIABLES
    mu=np.array(m['standardization']['mean']);sd=np.array(m['standardization']['std'])
    quantum=np.array(m['dequantization_quantum']);groups={}
    if file_hash(folder/'sealed_test_design.json')!=m['sealed_test_design_sha256']:
        raise RuntimeError('Sealed real test design changed')
    for r in read_json(folder/'sealed_test_design.json'):
        path=PROJECT/'.artifacts/data/raw'/DATASET/(r['name']+'.csv')
        if file_hash(path)!=m['source_checksums'][r['name']]:raise ValueError('Raw real source changed')
        frame=pd.read_csv(path)
        x=frame[VARIABLES].to_numpy(float)+(np.random.default_rng(r['dequant_seed']).random((len(frame),len(VARIABLES)))-.5)*quantum
        x=((x[r['start']:r['stop']]-mu)/sd).astype('float32')
        law={k:dict(v) for k,v in r['assignments'].items()}
        if '4' in law:law['4']['values']=x[:,4].tolist()
        groups.setdefault(r['endpoint'],[]).append(Environment(r['name'],torch.tensor(x,device=device),law,
             tuple(f'{r["name"]}:{i}' for i in range(r['start'],r['stop'])),tuple(range(r['start']//10,(r['stop']-1)//10+1))))
    return groups
