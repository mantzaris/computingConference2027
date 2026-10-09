"""Recorded assignments, whole-run partitions and sealed randomized outcomes."""
import copy
import numpy as np
import pandas as pd
import torch
from sem_update.data import Environment, validate_splits
from sem_update.phase2.data import Data, seal_manifest
from app_runtime import ROOT, RESULTS, atomic_json, read_json, digest, file_hash

VARS = ['load_in','load_out','hatch','rpm_in','rpm_out','current_in','current_out',
        'pressure_upwind','pressure_downwind','pressure_intake','pressure_ambient']
UNITS = ['duty fraction','duty fraction','degree','rpm','rpm','A','A','Pa relative to ambient',
         'Pa relative to ambient','Pa relative to ambient','Pa']
ROOTS = (0,1,2,10)
ACTUATORS = (0,1,2)
OUTCOMES = (5,6,7,8,9)
ROLES = {'fit': list(range(2,10)), 'early': [10,11], 'search': [12,13], 'calibration': [14], 'audit': [15]}
FINAL = ['validate_load_in','validate_load_in_mic','validate_load_out','validate_load_out_mic','validate_hatch_rpms']
SECONDARY = ['validate_load_in_current_out','validate_load_out_current_in','validate_load_out_pressure_intake']

def raw(dataset, name): return ROOT/'raw'/dataset/dataset/(name+'.csv')

def calibrated(frame):
    x = frame[VARS].to_numpy(float).copy()
    for j in (5,6):
        setting = frame['v_in' if j==5 else 'v_out'].to_numpy()
        if not np.allclose(setting,1.1): raise ValueError('Incompatible current calibration')
        x[:,j] *= 1.16/(1023*5)*2.5
    x[:,7:10] -= x[:,10,None]
    return x

def eligible(frame):
    """Only command histories determine eligibility; all spans use elapsed seconds."""
    t = frame.timestamp.to_numpy(); good = t-t[0]>=15
    for column, span in [('load_in',.1),('load_out',.1),('hatch',5.)]:
        s = pd.Series(frame[column].to_numpy(), index=pd.to_timedelta(t-t[0],unit='s'))
        roll = s.rolling('10s'); good &= (roll.max()-roll.min()).to_numpy()<=span
    ids=[]; last=-np.inf
    for k in np.where(good)[0]:
        if t[k]-last>=3: ids.append(int(k)); last=t[k]
    return np.array(ids, dtype=int)

def check_configuration(frame):
    expected={**{k:8 for k in ['osr_in','osr_out','osr_upwind','osr_downwind','osr_ambient','osr_intake']},
              'res_in':1,'res_out':1,'v_in':1.1,'v_out':1.1}
    if not (frame.config=='standard').all(): raise ValueError('Feedback/nonstandard configuration')
    for key,value in expected.items():
        if not np.allclose(frame[key],value): raise ValueError('Incompatible '+key)

def prepare(replicate=0, development=False):
    ident = 'development' if development else 'main' if replicate==0 else f'group-refit-{replicate}'
    folder=ROOT/'data/processed'/ident; folder.mkdir(parents=True,exist_ok=True)
    if (folder/'manifest.json').exists(): return folder
    roles=copy.deepcopy(ROLES)
    if development:
        # One independent development acquisition; separated 1,000-row blocks.
        roles={r:[16] for r in roles}
    if replicate:
        roles['fit']=np.random.default_rng(44000+replicate).choice(ROLES['fit'],len(ROLES['fit']),replace=True).tolist()
    frames={}; retained={}; values={}; counts={}
    for run in sorted({v for a in roles.values() for v in a}):
        name=f'actuators_random_walk_{run}'; frame=pd.read_csv(raw('wt_walks_v1',name))
        check_configuration(frame)
        if frame[VARS].isna().any().any(): raise ValueError('Missing modeled outcome; no silent imputation')
        frames[run]=frame; retained[run]=eligible(frame); values[run]=calibrated(frame)
    arrays={}; splits={}; chosen={}
    for ri,(role,runs) in enumerate(roles.items()):
        chosen[role]=[]
        for slot,run in enumerate(runs):
            ids=retained[run]
            if development: ids=ids[(ids>=ri*2000+50)&(ids<(ri+1)*2000-50)]
            chosen[role].append((run,slot,ids))
    fitting=np.concatenate([values[run][ids] for run,slot,ids in chosen['fit']])
    mean=fitting.mean(0); sd=fitting.std(0).clip(1e-5)
    for role,parts in chosen.items():
        splits[role]=[]
        for run,slot,ids in parts:
            # Fixed command-space bins produce calibration environments, preserving
            # the joint assignment tuples within each environment.
            xyz=values[run][ids,:3]; bins=(xyz[:,0]>.5).astype(int)+2*(xyz[:,1]>.5)+4*(xyz[:,2]>22.5)
            for b in sorted(set(bins)):
                take=ids[bins==b]
                if len(take)<4: continue
                key=f'{role}_r{run}_s{slot}_b{b}'; x=((values[run][take]-mean)/sd).astype('float32')
                arrays[key]=x
                assignments={str(j):{'kind':'recorded_joint','values':x[:,j].astype(float).tolist()} for j in ACTUATORS}
                splits[role].append({'name':key,'array':key,'assignments':assignments,
                    'row_ids':[f'walk{run}:{k}:resample{slot}' if replicate else f'walk{run}:{k}' for k in take],
                    'blocks':[int(k//100) for k in take], 'acquisition_run':run,'source_rows':take.tolist()})
        if not splits[role]: raise ValueError('No eligible data for '+role)
        counts[role]=sum(len(e['row_ids']) for e in splits[role])
    manifest={'id':ident,'d':len(VARS),'variables':VARS,'units':UNITS,'root_nodes':list(ROOTS),
        'standardization':{'mean':mean.tolist(),'std':sd.tolist()},'splits':splits,
        'roles_acquisition_runs':roles,'development':development,'group_refit':replicate,
            'non_test_intervention_rows':sum(counts.values()),'retained_rows_by_role':counts,
            'preprocessing_fit_rows':len(fitting),
        'source_sha256':{str(run):file_hash(raw('wt_walks_v1',f'actuators_random_walk_{run}')) for run in frames},
        'observational_rows':0,'assignment_policy':'all three commands assigned; nuisance command marginals never counted as physical mechanisms',
        'independent_apparatuses':1,'preprocessing':'calibrated current; three pressures minus simultaneously recorded ambient; training-only scales'}
    validate_splits(manifest); np.savez_compressed(folder/'learner.npz',**arrays)
    seal_manifest(manifest,arrays,folder); atomic_json(folder/'manifest.json',manifest)
    return folder

def load(folder,allowed=tuple(ROLES),device='cuda'):
    m=read_json(folder/'manifest.json')
    if file_hash(folder/'learner.npz')!=m['arrays_sha256']: raise ValueError('Changed data arrays')
    return Data(m,np.load(folder/'learner.npz'),device,allowed)

class NuisanceView:
    """Assignment-law fits reuse measured rows with all physical losses masked.

    No new observations enter this view. Actuator root densities are nuisance
    placeholders, excluded from every scientific score and always replaced at do.
    """
    def __init__(self,data): self.__dict__.update(data.__dict__); self.data=data
    def __getattr__(self,name): return getattr(self.data,name)
    def get(self,role):
        envs=self.data.get(role)
        if role not in ('fit','early'): return envs
        x=torch.cat([e.x for e in envs]); assignment={str(j):{'kind':'fixed','value':0} for j in range(self.d) if j not in ACTUATORS}
        return envs+[Environment('assignment-law-only',x,assignment,(),())]

def final_design():
    cfg=pd.read_csv(ROOT/'protocols/wt_validate_v1/wt_standard_validation_configs.csv')
    rows=[]
    for name in FINAL+SECONDARY+['validate_hatch_mic','validate_hatch_pressures']:
        match=[r for _,r in cfg.iterrows() if 'validate_'+r['from']+('' if pd.isna(r['to']) else '_'+r['to'])==name]
        if len(match)!=1: raise ValueError('Ambiguous protocol target')
        r=match[0]; f=pd.read_csv(raw('wt_validate_v1',name),usecols=['load_in','load_out','hatch','flag','timestamp'])
        target=r['from']; expected=np.where(f.flag==0,r.xA,r.xB)
        if not np.allclose(f[target],expected): raise ValueError('Flag is inconsistent with actual assignment')
        rows.append({'run':name,'target':target,'low':float(r.xA),'high':float(r.xB),'wait_ms':float(r['T']),
            'panel':'primary' if name in FINAL else 'shorter_wait' if name in SECONDARY else 'immediate_acoustic',
            'n':len(f),'protocol_n':int(r.N),'arm_n':[int((f.flag==a).sum()) for a in (0,1)],
            'nuisance':{c:float(f[c].iloc[0]) for c in VARS[:3] if c!=target},'sha256':file_hash(raw('wt_validate_v1',name))})
    return rows
