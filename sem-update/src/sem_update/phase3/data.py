"""Connected, relabeled SCMs with bounded interactions and sealed role streams."""
import math
from pathlib import Path
import networkx as nx
import numpy as np
import torch
from sem_update.graphs import DAG
from sem_update.data import assign_values,Environment,validate_splits
from sem_update.phase2.data import Data,load,ROLES,FRACTIONS,OBS_COUNTS,seal_manifest
from .runtime import root,atomic_json,read_json,digest,file_hash

def seed_for(seed,*labels):
    return int(digest([seed,*labels])[:15],16)%(2**31-1)

class System:
    def __init__(self,d,family,profile,seed):
        self.d,self.family,self.profile,self.seed=d,family,profile,seed
        rng=np.random.default_rng(seed_for(seed,'graph'));order=rng.permutation(d)
        edges=[];degree=np.ones(d)
        counts=np.minimum(np.arange(d),7 if profile=='dense' else 2)
        if profile=='hub':
            counts=np.array([0]+[min(k,int(rng.choice([1,2,3,4,5,6],p=[.4,.25,.15,.1,.06,.04]))) for k in range(1,d)])
            while counts.sum()!=2*d-3:
                direction=1 if counts.sum()<2*d-3 else -1
                eligible=[k for k in range(1,d) if (counts[k]<min(k,6) if direction>0 else counts[k]>1)]
                counts[int(rng.choice(eligible))]+=direction
        for k in range(1,d):
            count=int(counts[k])
            if profile=='deep':pa=np.arange(k-count,k)
            elif profile=='hub':
                prob=degree[:k]**2;pa=rng.choice(k,count,replace=False,p=prob/prob.sum())
            else:pa=rng.choice(k,count,replace=False)
            for a in pa:
                edges.append((int(order[a]),int(order[k])));degree[a]+=1
        self.graph=DAG(d,tuple(edges))
        rng=np.random.default_rng(seed_for(seed,'mechanisms'))
        self.nodes=[]
        for j in range(d):
            p=self.graph.parents(j);q=len(p)
            self.nodes.append({'parents':list(p),'weights':(rng.choice([-1.,1.],q)*rng.uniform(.65,1.15,q)).tolist(),
                'forms':rng.integers(0,3,q).tolist(),'noise_weights':rng.normal(0,.7,q).tolist(),
                'pairs':[[a,b,float(rng.choice([-1,1])*.4)] for a in range(q) for b in range(a+1,q) if rng.random()<.5],
                'sigma':float(rng.uniform(.4,.7)),'intercept':float(rng.uniform(-.2,.2))})

    def sample(self,n,seed,assignments=None,device='cuda',noises=None):
        gen=torch.Generator(device=device).manual_seed(seed)
        u=torch.randn(n,self.d,generator=gen,device=device) if noises is None else noises
        values=assign_values(assignments or {},n,gen,device,u.dtype);x=torch.zeros_like(u)
        for j in self.graph.order():
            if j in values:x[:,j]=values[j];continue
            spec=self.nodes[j];pa=spec['parents'];q=len(pa);m=torch.zeros(n,device=device)+spec['intercept']
            for a,w,f in zip(pa,spec['weights'],spec['forms']):
                z=x[:,a]
                effect=z if self.family=='linear' else (torch.tanh(z) if f==0 else torch.sin(z) if f==1 else z/(1+z.abs()))
                # Linear sanity systems use contraction along deep paths.
                m=m+(w*(.65 if self.family=='linear' else 1.))*effect/math.sqrt(max(q,1))
            if self.family!='linear':
                for a,b,w in spec['pairs']:m=m+w*torch.tanh(x[:,pa[a]])*torch.tanh(x[:,pa[b]])/max(1,math.sqrt(len(spec['pairs'])))
            scale=spec['sigma']
            if self.family=='heteroscedastic' and q:
                z=sum(w*torch.tanh(x[:,a]) for a,w in zip(pa,spec['noise_weights']))/math.sqrt(q)
                scale=.25+.65*torch.sigmoid(z)
            x[:,j]=m+scale*u[:,j]
        return x

    def json(self):return {'d':self.d,'family':self.family,'profile':self.profile,'seed':self.seed,'graph':self.graph.json(),'nodes':self.nodes}

def graph_stats(g):
    net=g.networkx();ins=np.array([net.in_degree(j) for j in range(g.d)]);outs=np.array([net.out_degree(j) for j in range(g.d)])
    return {'nodes':g.d,'edges':len(g.edges),'mean_indegree':float(ins.mean()),'max_indegree':int(ins.max()),
        'depth':nx.dag_longest_path_length(net),'weak_components':nx.number_weakly_connected_components(net),
        'largest_component':max(map(len,nx.weakly_connected_components(net))),
        'max_outdegree':int(outs.max()),'outdegree_cv':float(outs.std()/max(outs.mean(),1e-10)),
        'top_decile_outgoing_fraction':float(np.sort(outs)[-max(1,math.ceil(.1*g.d)):].sum()/max(len(g.edges),1))}

def prepare(task,config):
    d,seed,family,profile=(task[k] for k in ('d','seed','family','profile'))
    budget=task.get('budget',config['budget_per_target']);ident=f'p3-{profile}-{family}-d{d}-s{seed}-B{budget}'
    folder=root()/'data/processed'/ident;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'manifest.json').exists():return folder
    scm=System(d,family,profile,seed)
    obs=scm.sample(OBS_COUNTS['fit'],seed_for(seed,'fit','obs')).cpu().numpy()
    sd=obs.std(0);mu=obs.mean(0)
    criteria={'finite':bool(np.isfinite(obs).all()),'minimum_sd':float(sd.min()),'maximum_abs':float(np.abs(obs).max())}
    if not criteria['finite'] or sd.min()<.05 or np.abs(obs).max()>50:
        atomic_json(folder/'rejected_generator.json',{'task':task,'criteria':criteria,'replacement':None})
        raise FloatingPointError('Prespecified generator numerical rejection; preserve seed, no performance-based replacement')
    seen=sorted(map(int,np.random.default_rng(seed_for(seed,'visible')).choice(d,round(.2*d),replace=False)))
    unseen=sorted(set(range(d))-set(seen))
    # T3 uses the same number of uniformly selected unseen targets as visible ones.
    withheld=sorted(map(int,np.random.default_rng(seed_for(seed,'T3-targets')).choice(unseen,len(seen),replace=False)))
    arrays={};splits={}
    for role in ROLES:
        x=obs if role=='fit' else scm.sample(OBS_COUNTS[role],seed_for(seed,role,'obs')).cpu().numpy()
        key=role+'_obs';arrays[key]=((x-mu)/sd).astype('float32')
        splits[role]=[{'name':'obs','array':key,'assignments':{},'row_ids':[f'{seed}:{role}:obs:{i}' for i in range(len(x))]}]
        for j in seen:
            n=int(round(budget*FRACTIONS[role]));law={j:{'kind':'normal','mean':float(mu[j]+sd[j]),'scale':float(sd[j]*.25)}}
            # Nested role prefixes for the prespecified fixed-total sensitivity.
            full_n=int(round(max(400,budget)*FRACTIONS[role]))
            x=scm.sample(full_n,seed_for(seed,role,j),law).cpu().numpy()[:n];key=f'{role}_do{j}'
            arrays[key]=((x-mu)/sd).astype('float32')
            splits[role].append({'name':f'do{j}+','array':key,'assignments':{str(j):{'kind':'normal','mean':1.,'scale':.25}},
                'row_ids':[f'{seed}:{role}:do{j}:{i}' for i in range(n)]})
    manifest={'id':ident,**task,'budget_per_target':budget,'non_test_intervention_rows':len(seen)*budget,
        'seen_targets':seen,'withheld_targets':withheld,'visible_fraction':len(seen)/d,
        'standardization':{'mean':mu.tolist(),'std':sd.tolist()},'splits':splits,'phase':3,
        'generator_version':1,'numerical_criteria':criteria,'final_rows_loaded':False,'source_sha256':file_hash(__file__)}
    validate_splits(manifest);np.savez_compressed(folder/'learner.npz',**arrays);seal_manifest(manifest,arrays,folder)
    atomic_json(folder/'manifest.json',manifest);atomic_json(folder/'truth.json',scm.json())
    atomic_json(folder/'topology.json',graph_stats(scm.graph))
    return folder

def final_environments(folder,config):
    """Evaluation only: reconstruct generator, never expose truth to learner views."""
    m=read_json(Path(folder)/'manifest.json');s=System(m['d'],m['family'],m['profile'],m['seed'])
    mu=np.array(m['standardization']['mean']);sd=np.array(m['standardization']['std']);groups={}
    for endpoint,targets,center in [('T1',m['seen_targets'],1.),('T2',m['seen_targets'],-1.),('T3',m['withheld_targets'],1.)]:
        groups[endpoint]=[]
        for j in targets:
            physical={j:{'kind':'normal','mean':float(mu[j]+center*sd[j]),'scale':float(.25*sd[j])}}
            x=s.sample(config['evaluation_samples'],seed_for(m['seed'],endpoint,j),physical)
            x=(x-torch.tensor(mu,device='cuda',dtype=x.dtype))/torch.tensor(sd,device='cuda',dtype=x.dtype)
            law={str(j):{'kind':'normal','mean':center,'scale':.25}}
            groups[endpoint].append(Environment(f'{endpoint}-do{j}',x,law,tuple(f'{m["seed"]}:{endpoint}:{j}:{i}' for i in range(len(x)))))
    x=s.sample(config['evaluation_samples'],seed_for(m['seed'],'final-obs'))
    groups['obs']=[Environment('final-obs',(x-torch.tensor(mu,device='cuda'))/torch.tensor(sd,device='cuda'),{},())]
    return groups,s.graph
