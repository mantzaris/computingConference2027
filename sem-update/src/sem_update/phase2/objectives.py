"""Exact average-score decomposition and fixed-sample energy mixture fitting."""
import math
import numpy as np
import torch
from scipy.optimize import minimize
from sem_update.flows import balanced_nll
from sem_update.metrics import wasserstein
from sem_update.search import DEFAULT_SEARCH,audit_pass
from .models import sample,joint_nll

@torch.no_grad()
def score(model,environments,config=None,seed_offset=0):
    cfg={**DEFAULT_SEARCH,**(config or {})};d=model.graph.d
    interventions=[e for e in environments if e.targets];K=len(interventions)
    counts={j:sum(j not in e.targets for e in environments) for j in range(d)}
    shared=0.;terms=[]
    for e in environments:
        value=sum(-model.mechanisms[j].log_probability(e.x[:,j],e.x).mean().item()/counts[j]/d
                  for j in range(d) if j not in e.targets)
        if not e.targets:shared+=value
        else:terms.append(K*value)
    distances=[]
    for i,e in enumerate(interventions):
        seed=cfg['seed']+(i+1)*19+seed_offset
        y=sample(model,e.assignments,cfg['samples'],seed,str(e.x.device))
        keep=[j for j in range(d) if j not in e.targets]
        distances.append(wasserstein(e.x[:,keep],y[:,keep],cfg['projections'],seed).item())
    penalty=cfg['edge_penalty']*len(model.graph.edges)/d
    per=[shared+v+cfg['beta']*w+penalty for v,w in zip(terms,distances)]
    nll=balanced_nll(model,environments).item()
    total=nll+cfg['beta']*float(np.mean(distances))+penalty
    if not np.isclose(np.mean(per),total,atol=2e-6):raise AssertionError('Per-environment score fails aggregate reconstruction')
    return {'nll':nll,'sw1':float(np.mean(distances)),'edge_penalty':penalty,'total':total,
            'environment_sw1':distances,'environment_scores':per,'shared_observational_term':shared,
            'environment_names':[e.name for e in interventions]}

def select(scores,initial,rho=.0,tolerance=.005):
    base=np.asarray(scores[initial]['environment_scores'])
    values={key:float((1-rho)*np.mean(np.asarray(s['environment_scores'])-base)+rho*np.max(np.asarray(s['environment_scores'])-base))
            for key,s in scores.items()}
    best=min(values,key=lambda key:(values[key],key))
    return (best if values[best]<=-tolerance else initial),values

@torch.no_grad()
def audit_score(model,environments,config=None):
    cfg={**DEFAULT_SEARCH,**(config or {})};distances=[]
    for i,e in enumerate([e for e in environments if e.targets]):
        seed=cfg['seed']+(i+1)*19+20000
        y=sample(model,e.assignments,cfg['samples'],seed,str(e.x.device))
        keep=[j for j in range(e.x.shape[1]) if j not in e.targets]
        distances.append(wasserstein(e.x[:,keep],y[:,keep],cfg['projections'],seed).item())
    nll=joint_nll(model,environments)
    return {'sw1':float(np.mean(distances)),'nll':None if nll is None else nll.item(),
            'environment_sw1':distances,'normalization':'mean across environments of whole-joint NLL / number of intact nodes'}

@torch.no_grad()
def energy_matrices(models,environments,samples=512,seed=62281):
    a=[];b=[];arrays={}
    for i,e in enumerate([e for e in environments if e.targets]):
        keep=[j for j in range(e.x.shape[1]) if j not in e.targets]
        z=[sample(m,e.assignments,samples,seed+i*31,str(e.x.device))[:,keep] for m in models]
        q=math.sqrt(len(keep));observed=e.x[:,keep]
        av=torch.stack([torch.cdist(v,observed).mean()/q for v in z])
        bv=torch.stack([torch.stack([torch.cdist(v,w).mean()/q for w in z]) for v in z])
        a.append(av.double());b.append(bv.double())
        arrays.update({f'{e.name}_component{k}':v.cpu().numpy() for k,v in enumerate(z)})
    return torch.stack(a).mean(0).cpu().numpy(),torch.stack(b).mean(0).cpu().numpy(),arrays

def weight_objective(w,a,b,tau=.01):
    return float(w@a-.5*w@b@w+tau*(1-w[0])**2)

def simplex_grid(k,steps=200):
    if k==1:return np.ones((1,1))
    if k==2:return np.array([[i/steps,1-i/steps] for i in range(steps+1)])
    if k!=3:raise ValueError('At most three components are supported')
    return np.array([[i/steps,j/steps,(steps-i-j)/steps] for i in range(steps+1) for j in range(steps-i+1)])

def fit_weights(a,b,tau=.01,validate_grid=False):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);b=(b+b.T)/2;k=len(a)
    if k==1:return np.ones(1),{'success':True,'objective':weight_objective(np.ones(1),a,b,tau),'grid_gap':0.}
    def objective(w):return weight_objective(w,a,b,tau)
    def jac(w):
        value=a-b@w;value[0]-=2*tau*(1-w[0]);return value
    solutions=[]
    for start in [np.ones(k)/k,*np.eye(k)]:
        fit=minimize(objective,start,jac=jac,method='SLSQP',bounds=[(0,1)]*k,
                     constraints={'type':'eq','fun':lambda w:w.sum()-1,'jac':lambda w:np.ones(k)},
                     options={'ftol':1e-12,'maxiter':300})
        if fit.success and abs(fit.x.sum()-1)<1e-7:
            w=np.clip(fit.x,0,1);w/=w.sum();solutions.append((objective(w),w))
    fallback=not solutions
    grid=simplex_grid(k) if validate_grid or fallback else None
    grid_values=None if grid is None else grid@a-.5*np.einsum('bi,ij,bj->b',grid,b,grid)+tau*(1-grid[:,0])**2
    if fallback:solutions=[(float(grid_values.min()),grid[grid_values.argmin()])]
    value,w=min(solutions,key=lambda row:(row[0],tuple(row[1])))
    gap=None if grid is None else value-float(grid_values.min())
    if gap is not None and gap>1e-8:raise RuntimeError('Weight optimizer worse than deterministic simplex grid')
    return w,{'success':not fallback,'grid_fallback':fallback,'objective':value,'grid_gap':gap,
              'simplex_sum':float(w.sum()),'tau':tau,'starts':k+1}
