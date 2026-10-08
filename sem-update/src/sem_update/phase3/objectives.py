"""Batched sampling, exact score decomposition, and bounded distributional work."""
import math
import numpy as np
import torch
from sem_update.data import assign_values
from sem_update.metrics import wasserstein
from sem_update.search import DEFAULT_SEARCH
from sem_update.phase2.models import sample,joint_nll,Ensemble
from sem_update.phase2.objectives import select,fit_weights
from .flows import FastSCM

@torch.no_grad()
def sample_many(model,environments,n,seed=491,offset=0):
    if not isinstance(model,FastSCM):
        return [sample(model,e.assignments,n,seed+(i+1)*19+offset,str(e.x.device)) for i,e in enumerate(environments)]
    chunks=[];laws=[]
    for i,e in enumerate(environments):
        gen=torch.Generator(device=e.x.device).manual_seed(seed+(i+1)*19+offset)
        chunks.append(torch.randn(n,model.graph.d,device=e.x.device,generator=gen))
        laws.append(assign_values(e.assignments,n,gen,e.x.device))
    noise=torch.cat(chunks);assignments={}
    for j in set(j for law in laws for j in law):
        mask=torch.zeros(len(noise),device=noise.device,dtype=torch.bool);values=torch.zeros(len(noise),device=noise.device)
        for i,law in enumerate(laws):
            if j in law:mask[i*n:(i+1)*n]=True;values[i*n:(i+1)*n]=law[j]
        assignments[j]=(mask,values)
    return list(model.sample_intervention(noise,assignments).split(n))

@torch.no_grad()
def score(model,environments,config=None):
    cfg={**DEFAULT_SEARCH,**(config or {})};d=model.graph.d
    interventions=[e for e in environments if e.targets];K=len(interventions)
    counts=torch.tensor([sum(j not in e.targets for e in environments) for j in range(d)],device=environments[0].x.device)
    shared=0.;terms=[]
    for env in environments:
        intact=[j for j in range(d) if j not in env.targets]
        lp=model.log_probability(env.x,env.targets)
        value=float((-lp.mean(0)/counts[intact]/d).sum())
        if not env.targets:shared+=value
        else:terms.append(K*value)
    generated=sample_many(model,interventions,cfg['samples'],cfg['seed']);distances=[]
    for i,(env,y) in enumerate(zip(interventions,generated)):
        keep=[j for j in range(d) if j not in env.targets]
        distances.append(float(wasserstein(env.x[:,keep],y[:,keep],cfg['projections'],cfg['seed']+(i+1)*19)))
    penalty=cfg['edge_penalty']*len(model.graph.edges)/d;nll=shared+float(np.mean(terms))
    per=[shared+v+cfg['beta']*w+penalty for v,w in zip(terms,distances)]
    return {'nll':nll,'sw1':float(np.mean(distances)),'edge_penalty':penalty,'total':float(np.mean(per)),
        'environment_scores':per,'environment_sw1':distances,'shared_observational_term':shared,'environment_names':[e.name for e in interventions]}

@torch.no_grad()
def audit_score(model,environments,config=None):
    cfg={**DEFAULT_SEARCH,**(config or {})};envs=[e for e in environments if e.targets]
    predictions=sample_many(model,envs,cfg['samples'],cfg['seed'],20000);ws=[]
    for i,(e,y) in enumerate(zip(envs,predictions)):
        keep=[j for j in range(e.x.shape[1]) if j not in e.targets]
        ws.append(float(wasserstein(e.x[:,keep],y[:,keep],cfg['projections'],cfg['seed']+(i+1)*19+20000)))
    nll=joint_nll(model,environments)
    return {'sw1':float(np.mean(ws)),'nll':None if nll is None else float(nll),'environment_sw1':ws}

def distance_mean(x,y,chunk=256):
    total=torch.zeros((),device=x.device,dtype=torch.float64)
    for a in x.split(chunk):
        for b in y.split(chunk):total+=torch.cdist(a,b).double().sum()
    return total/(len(x)*len(y))

@torch.no_grad()
def energy_matrices(models,environments,samples=512,seed=62281):
    envs=[e for e in environments if e.targets]
    predictions=[sample_many(m,envs,samples,seed) for m in models];a=[];b=[];arrays={}
    for i,e in enumerate(envs):
        keep=[j for j in range(e.x.shape[1]) if j not in e.targets];q=math.sqrt(len(keep));z=[v[i][:,keep] for v in predictions]
        a.append(torch.stack([distance_mean(v,e.x[:,keep])/q for v in z]))
        b.append(torch.stack([torch.stack([distance_mean(v,w)/q for w in z]) for v in z]))
        for k,v in enumerate(z):arrays[f'{e.name}_component{k}']=v.cpu().numpy()
    return torch.stack(a).mean(0).cpu().numpy(),torch.stack(b).mean(0).cpu().numpy(),arrays
