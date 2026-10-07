"""Elementary controls and whole-observation mixtures with exact do semantics."""
import math
import numpy as np
import torch
from torch import nn
from sem_update.graphs import DAG
from sem_update.flows import GenerativeSCM
from sem_update.data import assign_values

class EmpiricalMarginals(nn.Module):
    continuous_density=False
    def __init__(self,observational):
        super().__init__();self.graph=DAG(observational.shape[1])
        self.register_buffer('sorted_values',observational.sort(dim=0).values)
    def sample_intervention(self,noises,assignments):
        p=.5*(1+torch.erf(noises/math.sqrt(2)))
        idx=(p*len(self.sorted_values)).long().clamp(0,len(self.sorted_values)-1)
        x=torch.stack([self.sorted_values[idx[:,j],j] for j in range(self.graph.d)],1)
        for j,value in assignments.items():x[:,int(j)]=value
        return x
    def log_probability(self,*args,**kwargs):
        raise TypeError('Empirical marginals have no Lebesgue density; continuous NLL is unavailable')

class RidgeMechanism(nn.Module):
    def __init__(self,parents,intercept,coefficients,scale):
        super().__init__();self.parents=tuple(parents)
        self.register_buffer('intercept',intercept);self.register_buffer('coefficients',coefficients)
        self.register_buffer('scale',scale)
    def mean(self,x):
        return self.intercept+(x[:,self.parents]@self.coefficients if self.parents else torch.zeros(len(x),device=x.device))
    def forward_noise(self,u,x):return self.mean(x)+self.scale*u,torch.ones_like(u)*self.scale.log()
    def inverse_noise(self,y,x):return (y-self.mean(x))/self.scale,-torch.ones_like(y)*self.scale.log()
    def log_probability(self,y,x):
        u,ld=self.inverse_noise(y,x)
        return -.5*(u.square()+math.log(2*math.pi))+ld

@torch.no_grad()
def ridge_fit(data,graph,alpha=.01,variance_floor=1e-4):
    mechanisms=[]
    for j in range(data.d):
        envs=[e for e in data.get('fit') if j not in e.targets]
        pa=graph.parents(j);device=envs[0].x.device
        matrix=torch.zeros(len(pa)+1,len(pa)+1,device=device,dtype=torch.float64)
        rhs=torch.zeros(len(pa)+1,device=device,dtype=torch.float64)
        for env in envs:
            x=env.x.double();design=torch.cat([torch.ones(len(x),1,device=device,dtype=torch.float64),x[:,pa]],1)
            matrix+=design.T@design/(len(x)*len(envs));rhs+=design.T@x[:,j]/(len(x)*len(envs))
        penalty=torch.eye(len(pa)+1,device=device,dtype=torch.float64)*alpha;penalty[0,0]=0
        beta=torch.linalg.solve(matrix+penalty,rhs)
        variance=torch.stack([((e.x.double()[:,j]-beta[0]-e.x.double()[:,pa]@beta[1:])**2).mean() for e in envs]).mean().clamp_min(variance_floor)
        mechanisms.append(RidgeMechanism(pa,beta[0].float(),beta[1:].float(),variance.sqrt().float()))
    return GenerativeSCM(graph,mechanisms)

class Ensemble(nn.Module):
    continuous_density=True
    def __init__(self,models,weights):
        super().__init__();self.components=nn.ModuleList(models)
        w=torch.as_tensor(weights,dtype=torch.float64,device=next(models[0].buffers(),next(models[0].parameters(),torch.tensor(0.))).device)
        if len(w)!=len(models) or (w<0).any() or abs(w.sum().item()-1)>1e-7:raise ValueError('Invalid mixture weights')
        self.register_buffer('weights',w/w.sum());self.d=models[0].graph.d
        if any(m.graph.d!=self.d for m in models):raise ValueError('Component dimension mismatch')
    @property
    def representative_graph(self):return self.components[int(self.weights.argmax())].graph
    def joint_log_probability(self,x,targets=()):
        logp=torch.stack([m.log_probability(x,targets).sum(1) for m in self.components],1)
        return torch.logsumexp(logp+self.weights.log().to(x.dtype),1)
    def sample_intervention(self,noises,assignments,component_uniform=None):
        if component_uniform is None:raise ValueError('An independent component draw is required')
        component=torch.searchsorted(self.weights.cumsum(0),component_uniform.to(torch.float64),right=True).clamp_max(len(self.components)-1)
        result=torch.empty_like(noises)
        for k,model in enumerate(self.components):
            take=component==k
            if not take.any():continue
            values={int(j):(torch.as_tensor(v,device=noises.device).expand(len(noises))[take]) for j,v in assignments.items()}
            result[take]=model.sample_intervention(noises[take],values)
        return result

def assignment_values(spec,n,generator,device,dtype=torch.float32):
    values=assign_values({k:v for k,v in spec.items() if v['kind']!='recorded_design'},n,generator,device,dtype)
    for key,law in spec.items():
        if law['kind']=='recorded_design':
            pool=torch.tensor(law['values'],device=device,dtype=dtype)
            if not len(pool):raise ValueError('Empty recorded assignment design')
            idx=torch.randint(len(pool),(n,),generator=generator,device=device)
            values[int(key)]=pool[idx]
    return values

@torch.no_grad()
def sample(model,spec,n,seed,device='cuda'):
    d=model.d if isinstance(model,Ensemble) else model.graph.d
    g=torch.Generator(device=device).manual_seed(seed)
    u=torch.randn(n,d,generator=g,device=device)
    values=assignment_values(spec,n,g,device)
    if isinstance(model,Ensemble):
        return model.sample_intervention(u,values,torch.rand(n,generator=g,device=device))
    return model.sample_intervention(u,values)

def joint_nll(model,environments):
    if not getattr(model,'continuous_density',True):return None
    values=[]
    for e in environments:
        d=e.x.shape[1]-len(e.targets)
        if d==0:continue
        lp=model.joint_log_probability(e.x,e.targets) if isinstance(model,Ensemble) else model.log_probability(e.x,e.targets).sum(1)
        values.append(-lp.mean()/d)
    return torch.stack(values).mean()
