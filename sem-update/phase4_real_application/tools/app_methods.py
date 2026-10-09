"""Explicit real-design adapters around the unchanged historical algorithms."""
import time
import numpy as np
import torch
from sem_update.data import assign_values
from sem_update.graphs import DAG
from sem_update.phase2.models import Ensemble, EmpiricalMarginals, ridge_fit
from sem_update.phase3 import bank, flows, objectives, selection, discovery
from sem_update.phase3.graphs import edit_descriptors
from sem_update.diagnostics import mmd, hsic
from sem_update.training import atomic_torch
from app_runtime import ROOT, atomic_json, read_json, file_hash, source_hash, job, cuda
from app_data import ACTUATORS, ROOTS, NuisanceView, load, prepare

ORIGINAL_FIT = flows.fit_graph

def fit_graph(data,graph,config,allow_training=True):
    if any(graph.parents(j) for j in ROOTS): raise ValueError('Incoming edge to assigned command/context root')
    return ORIGINAL_FIT(NuisanceView(data),graph,config,allow_training)

@torch.no_grad()
def sample_joint(model,spec,n,seed):
    d=model.d if isinstance(model,Ensemble) else model.graph.d
    gen=torch.Generator(device='cuda').manual_seed(seed)
    u=torch.randn(n,d,device='cuda',generator=gen)
    laws={k:v for k,v in spec.items() if v['kind']!='recorded_joint'}
    values=assign_values(laws,n,gen,'cuda')
    joint={k:v for k,v in spec.items() if v['kind']=='recorded_joint'}
    if joint:
        lengths={len(v['values']) for v in joint.values()}
        if len(lengths)!=1: raise ValueError('Broken joint assignment tuples')
        idx=torch.randint(next(iter(lengths)),(n,),generator=gen,device='cuda')
        values.update({int(k):torch.tensor(v['values'],device='cuda')[idx] for k,v in joint.items()})
    if isinstance(model,Ensemble): return model.sample_intervention(u,values,torch.rand(n,device='cuda',generator=gen))
    return model.sample_intervention(u,values)

def sample_many(model,environments,n,seed=491,offset=0):
    return [sample_joint(model,e.assignments,n,seed+(i+1)*19+offset) for i,e in enumerate(environments)]

def legal_edits(graph,max_indegree):
    return [e for e in edit_descriptors(graph,max_indegree)
            if (e[0]!='add' or e[2] not in ROOTS) and (e[0]!='reverse' or e[1] not in ROOTS)]

@torch.no_grad()
def conditional_diagnostics(model,environments,seed,cap=64,permutations=16,pair_cap=8,environment_cap=4):
    """Historical MMD/HSIC priorities, with a conditional acquisition reference.

    There is no unmanipulated observational environment in this dataset. The
    first fixed-order search environment is the reference, always masking commands.
    """
    rng=np.random.default_rng(seed); indices=[0]+sorted(rng.choice(range(1,len(environments)),min(environment_cap,len(environments)-1),replace=False))
    envs=[environments[i] for i in indices]; gen=torch.Generator(device='cuda').manual_seed(seed)
    xs=[e.x[torch.randperm(len(e.x),device='cuda',generator=gen)[:cap]] for e in envs]
    residuals=[model.infer_disturbances(x,e.targets) for x,e in zip(xs,envs)]; result=[]
    for j in range(model.graph.d):
        terms={'marginal':[],'parents':[],'pairs':[]}
        for i,(e,x,rs) in enumerate(zip(envs,xs,residuals)):
            if j not in rs: continue
            u=rs[j]
            if i: terms['marginal'].append(mmd(u,residuals[0][j],gen,permutations)[1])
            pa=model.graph.parents(j)
            if pa: terms['parents'].append(hsic(u,x[:,pa],gen,permutations,True)[1])
            peers=[k for k in rs if k!=j]
            terms['pairs'].extend(hsic(u,rs[int(k)],gen,permutations)[1] for k in rng.choice(peers,min(pair_cap,len(peers)),replace=False))
        means={k:float(torch.stack(v).mean()) if v else 0. for k,v in terms.items()}
        result.append({'node':j,'priority':sum(means.values()),'components':means,'environment_names':[e.name for e in envs]})
    return result

def install():
    bank.fit_graph=fit_graph; bank.edit_descriptors=legal_edits; bank.disturbances=conditional_diagnostics
    objectives.sample_many=sample_many

def initial_graph(data):
    """Greedy Gaussian BIC on fitting rows only, with declared exogenous roots."""
    x=torch.cat([e.x for e in data.get('fit')]).cpu().numpy().astype(float)
    n,d=x.shape; graph=DAG(d)
    def value(j,parents):
        design=np.c_[np.ones(n),x[:,parents]]
        residual=x[:,j]-design@np.linalg.lstsq(design,x[:,j],rcond=None)[0]
        return n*np.log(max(np.mean(residual**2),1e-8))+len(parents)*np.log(n)
    for _ in range(2*d):
        choices=[]
        for op,a,b,affected in legal_edits(graph,2):
            if op!='add': continue
            pa=list(graph.parents(b)); delta=value(b,pa+[a])-value(b,pa)
            choices.append((delta,a,b))
        if not choices: break
        delta,a,b=min(choices)
        if delta>=-2: break
        graph=DAG(d,graph.edges+((a,b),))
    return graph

def timed(name,identity,function):
    path=ROOT/'runs'/(name+'.json')
    with job(name,identity) as active:
        if active:
            cuda(); torch.cuda.reset_peak_memory_stats(); start=time.monotonic()
            value=function(); torch.cuda.synchronize()
            value.update(stage_seconds=time.monotonic()-start,stage_peak_bytes=torch.cuda.max_memory_allocated())
            atomic_json(path,value)
    return read_json(path)

def run_task(config,replicate=0,semantic=None,development=False):
    install(); folder=prepare(replicate,development); data=load(folder); limited=load(folder,('fit','early'))
    view=load(folder,('fit','early','search')); name=folder.name+('-semantic' if semantic is not None else '')
    cp=ROOT/'runs'/name; cp.mkdir(parents=True,exist_ok=True)
    identity={'data':data.key,'config':config,'source':source_hash(),'semantic':semantic}
    initial=DAG.from_json(semantic) if semantic is not None else initial_graph(limited)
    atomic_json(cp/'initial.json',{'graph':initial.json(),'source':'actual local LLM' if semantic else 'fit-only Gaussian BIC'})
    methods={}
    def ridge():
        model=ridge_fit(NuisanceView(limited),initial,config['ridge_alpha'],1e-4)
        path=cp/'ridge.pt'; atomic_torch(path,model)
        return {'selected':{'kind':'ridge','path':str(path.relative_to(ROOT)),'sha256':file_hash(path),'graph':initial.json()}}
    rr=timed(name+'-ridge',identity,ridge)
    methods['M1']={**rr,'logical_seconds':rr['stage_seconds'],'fitting_updates':0}
    start=time.monotonic(); marginal=EmpiricalMarginals(torch.cat([e.x for e in limited.get('fit')]))
    methods['M0']={'selected':{'kind':'marginal'},'logical_seconds':time.monotonic()-start,'fitting_updates':0}
    if replicate==0 and semantic is None:
        dc=timed(name+'-discovery',identity,lambda:discovery.discover(NuisanceView(limited),config['dcdi'],ROOTS))
        def refit():
            model,stats=fit_graph(limited,DAG.from_json(dc['graph']),config['train'])
            return {'selected':selection.graph_spec(dc['graph']),'fits':stats,'cost':bank.cost({'x':{'fits':stats}})}
        refitted=timed(name+'-dcdi-refit',identity,refit)
        methods['M2']={**refitted,'discovery':dc,'logical_seconds':dc['seconds']+refitted['cost']['fit_seconds'],
                       'fitting_updates':refitted['cost']['fitting_updates']}
    banks={}
    policies=('diagnostic','random') if replicate==0 else ('diagnostic',)
    for policy in policies:
        bn=name+'-'+policy
        timed(bn,identity,lambda p=policy,bn=bn:bank.build(view,[initial],bn,config,p,ROOTS))
        b=read_json(ROOT/'runs'/bn/'bank.json'); banks[policy]=b
        sel=timed(bn+'-selection',identity,lambda b=b,bn=bn:selection.choose(b,data,config,bn+'-select',development,True))
        for key,row in sel['methods'].items():
            if key in ('rho0','tau0','uniform'): continue
            methods[key]={**row,'fitting_updates':row['cost']['fitting_updates'],
                          'stage_peak_bytes':max(b['peak_vram_bytes'],sel['stage_peak_bytes'])}
        if policy=='diagnostic':
            stats=b['candidates'][b['initial']]['fits']; cost=bank.cost({'x':{'fits':stats}})
            methods['fixed']={'selected':selection.graph_spec(initial.json()),'logical_seconds':cost['fit_seconds'],
                'fitting_updates':cost['fitting_updates'],'cost':cost}
    result={'data_folder':str(folder.relative_to(ROOT)),'dataset_hash':data.key,'initial':initial.json(),
        'methods':methods,'bank_hashes':{k:v['bank_hash'] for k,v in banks.items()},'config':config,
        'source_hash':source_hash(),'selected_before_final':True,'replicate':replicate,'semantic':semantic is not None}
    atomic_json(cp/'frozen.json',result)
    return result

def load_model(spec,data,config):
    if spec['kind']=='marginal': return EmpiricalMarginals(torch.cat([e.x for e in data.get('fit')]))
    if spec['kind']=='ridge':
        if file_hash(ROOT/spec['path'])!=spec['sha256']: raise ValueError('Ridge changed')
        return torch.load(ROOT/spec['path'],map_location='cuda',weights_only=False)
    if spec['kind']=='flow': return fit_graph(data,DAG.from_json(spec['graph']),config['train'],False)[0]
    return Ensemble([fit_graph(data,DAG.from_json(g),config['train'],False)[0] for g in spec['components']],spec['weights'])
