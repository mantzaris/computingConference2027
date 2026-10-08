"""Grouped execution of unchanged scalar RQS mechanisms, without parameter sharing."""
import copy
import math
import time
from collections import defaultdict
import networkx as nx
import torch
from torch import nn
from torch.nn import functional as F
from sem_update.flows import Mechanism,GenerativeSCM
from sem_update.training import cache_key,atomic_torch,DEFAULT_TRAIN
from sem_update.runtime import check_budget
from .runtime import root,digest,file_hash

class Group(nn.Module):
    def __init__(self,models):
        super().__init__();self.p=len(models[0].parents);self.bins=models[0].bins;self.transforms=models[0].transforms
        if any(len(m.parents)!=self.p for m in models):raise ValueError('Incompatible group')
        self.parent_indices=torch.tensor([m.parents for m in models],device=next(models[0].parameters()).device,dtype=torch.long)
        if self.p:
            self.weights=nn.ParameterList([nn.Parameter(torch.stack([m.conditioner[i].weight.detach() for m in models])) for i in (0,2,4)])
            self.biases=nn.ParameterList([nn.Parameter(torch.stack([m.conditioner[i].bias.detach() for m in models])) for i in (0,2,4)])
        else:self.constant=nn.Parameter(torch.stack([m.constant.detach() for m in models]))

    def context(self,x):return x[:,self.parent_indices].permute(1,0,2)

    def params(self,x):
        if not self.p:return self.constant[:,None,:].expand(-1,x.shape[1],-1)
        for i,(w,b) in enumerate(zip(self.weights,self.biases)):
            x=torch.bmm(x,w.transpose(1,2))+b[:,None,:]
            if i<2:x=F.silu(x)
        return x

    def transform(self,y,context,inverse):
        from nflows.transforms.splines.rational_quadratic import unconstrained_rational_quadratic_spline
        shape=y.shape;p=self.params(context).flatten(0,1);z=y.flatten();scale=.05+F.softplus(p[:,-1]);step=3*self.bins-1
        ld=torch.zeros_like(z)
        if inverse:z=(z-p[:,-2])/scale;ld=-scale.log()
        for k in (reversed(range(self.transforms)) if inverse else range(self.transforms)):
            t=p[:,k*step:(k+1)*step];b=self.bins
            z,v=unconstrained_rational_quadratic_spline(z,t[:,:b],t[:,b:2*b],t[:,2*b:],inverse=inverse,
                tails='linear',tail_bound=5.,min_bin_width=.001,min_bin_height=.001,min_derivative=.001)
            ld=ld+v
        if not inverse:z=p[:,-2]+scale*z;ld=ld+scale.log()
        return z.view(shape),ld.view(shape)

    def logp(self,y,context):
        u,ld=self.transform(y,context,True)
        return -.5*(u.square()+math.log(2*math.pi))+ld

    def unpack(self,models):
        with torch.no_grad():
            for k,m in enumerate(models):
                if not self.p:m.constant.copy_(self.constant[k])
                else:
                    for i,w,b in zip((0,2,4),self.weights,self.biases):
                        m.conditioner[i].weight.copy_(w[k]);m.conditioner[i].bias.copy_(b[k])

class FastSCM(GenerativeSCM):
    def __init__(self,graph,mechanisms):
        super().__init__(graph,mechanisms);self._groups={};self.layers=list(nx.topological_generations(graph.networkx()))
    def groups(self,nodes,cache=True):
        key=tuple(nodes)
        if not cache or key not in self._groups:
            parts=defaultdict(list)
            for j in nodes:parts[len(self.mechanisms[j].parents)].append(j)
            groups=[(ids,Group([self.mechanisms[j] for j in ids])) for ids in parts.values()]
            if cache:self._groups[key]=groups
            return groups
        return self._groups[key]
    def log_probability(self,x,targets=()):
        active=[j for j in range(self.graph.d) if j not in targets];values={}
        # Target masks must exclude the target computation, but need not retain
        # a separate full parameter copy for every intervention environment.
        for nodes,group in self.groups(active,cache=False):
            lp=group.logp(x[:,nodes].T,group.context(x))
            values.update({j:lp[k] for k,j in enumerate(nodes)})
        return torch.stack([values[j] for j in active],1)
    def infer_disturbances(self,x,targets=()):
        active=[j for j in range(self.graph.d) if j not in targets];values={}
        for nodes,group in self.groups(active,cache=False):
            u,_=group.transform(x[:,nodes].T,group.context(x),True)
            values.update({j:u[k] for k,j in enumerate(nodes)})
        return values
    def sample_intervention(self,noises,assignments):
        x=torch.zeros_like(noises)
        for j,v in assignments.items():
            if isinstance(v,tuple):
                mask,value=v;x[:,j]=torch.where(mask,value,x[:,j])
            else:x[:,j]=v
        for layer in self.layers:
            active=[j for j in layer if j not in assignments or isinstance(assignments[j],tuple)]
            for nodes,group in self.groups(active):
                out,_=group.transform(noises[:,nodes].T,group.context(x),False)
                for k,j in enumerate(nodes):
                    x[:,j]=torch.where(assignments[j][0],assignments[j][1],out[k]) if j in assignments else out[k]
        return x

def mechanism_key(data,node,parents,cfg):
    return cache_key(data,node,parents,{**cfg,'phase3_grouped_source':file_hash(__file__)},'flow')

def fit_graph(data,graph,config,allow_training=True):
    cfg={**DEFAULT_TRAIN,**config};models=[];stats=[None]*graph.d;missing=defaultdict(list)
    checkpoint=root()/'checkpoints';checkpoint.mkdir(exist_ok=True)
    for j in range(graph.d):
        key=mechanism_key(data,j,graph.parents(j),cfg);seed=int(key[:8],16)%(2**31-1)
        with torch.random.fork_rng(devices=[0]):
            torch.manual_seed(seed);m=Mechanism(graph.parents(j),cfg['width'],cfg['bins'],cfg['transforms']).cuda()
        models.append(m);path=checkpoint/(key+'.pt')
        if path.exists():
            ck=torch.load(path,map_location='cuda',weights_only=False)
            if ck['key']!=key or not ck['complete']:raise ValueError('Invalid completed cache')
            m.load_state_dict(ck['best_state']);stats[j]={**ck['stats'],'cache_hit':True}
        elif allow_training:missing[len(graph.parents(j))].append((j,key,seed))
        else:raise RuntimeError('Evaluation cannot fit missing mechanism '+key)
    for nodes in missing.values():
        for offset in range(0,len(nodes),cfg.get('group_size',32)):
            items=nodes[offset:offset+cfg.get('group_size',32)]
            fitted=train_group(data,items,[models[j] for j,_,_ in items],cfg)
            for (j,key,seed),s in zip(items,fitted):stats[j]=s
    return FastSCM(graph,models),stats

def train_group(data,items,models,cfg):
    started=time.monotonic();group=Group(models).cuda();nodes=[r[0] for r in items];k=len(nodes)
    gid=digest([r[1] for r in items]);path=root()/'checkpoints'/('group-'+gid+'.partial.pt')
    fit=data.get('fit');early=data.get('early');pool=torch.cat([e.x for e in fit])
    sizes=torch.tensor([len(e.x) for e in fit],device='cuda');offsets=sizes.cumsum(0)-sizes
    eligible=[torch.tensor([i for i,e in enumerate(fit) if j not in e.targets],device='cuda') for j in nodes]
    gens=[torch.Generator(device='cuda').manual_seed(seed+1) for _,_,seed in items]
    opt=torch.optim.Adam(group.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    best=torch.full((k,),float('inf'),device='cuda');bad=torch.zeros(k,device='cuda',dtype=torch.long)
    steps=torch.zeros(k,device='cuda',dtype=torch.long);active=torch.ones(k,device='cuda',dtype=torch.bool)
    best_state=copy.deepcopy(group.state_dict());first=0;elapsed=0.;trace=[]
    if path.exists():
        ck=torch.load(path,map_location='cuda',weights_only=False)
        if ck['keys']!=[r[1] for r in items]:raise ValueError('Incompatible grouped resume')
        group.load_state_dict(ck['state']);opt.load_state_dict(ck['optimizer'])
        best,bad,steps,active,best_state=ck['best'],ck['bad'],ck['steps'],ck['active'],ck['best_state']
        first,elapsed,trace=ck['step'],ck['seconds'],ck['trace']
        for gen,state in zip(gens,ck['rng']):gen.set_state(state.cpu())
    # Exact equal-environment validation, with no target mechanism evaluated.
    def validation():
        values=torch.zeros(k,device='cuda');counts=torch.zeros_like(values)
        with torch.no_grad():
            for env in early:
                intact=[i for i,j in enumerate(nodes) if j not in env.targets]
                if not intact:continue
                # Group slices carry only intact node mechanisms, preserving masking.
                group.unpack(models)
                sub=Group([models[i] for i in intact])
                nids=[nodes[i] for i in intact]
                values[intact]+=-sub.logp(env.x[:,nids].T,sub.context(env.x)).mean(1);counts[intact]+=1
        return values/counts
    for block in range(first,cfg['steps'],cfg['check_every']):
        check_budget()
        if not active.any():break
        width=min(cfg['check_every'],cfg['steps']-block);indices=[]
        for ix,gen in zip(eligible,gens):
            eid=ix[torch.randint(len(ix),(width,cfg['batch_size']),generator=gen,device='cuda')]
            indices.append(offsets[eid]+(torch.rand(width,cfg['batch_size'],generator=gen,device='cuda')*sizes[eid]).long())
        idx=torch.stack(indices,1)
        for si in range(width):
            x=pool[idx[si]];y=x[torch.arange(k,device='cuda')[:,None],torch.arange(cfg['batch_size'],device='cuda')[None,:],torch.tensor(nodes,device='cuda')[:,None]]
            context=torch.gather(x,2,group.parent_indices[:,None,:].expand(-1,cfg['batch_size'],-1))
            opt.zero_grad(set_to_none=True);loss=-group.logp(y,context).mean(1)
            total=(loss*active).sum()
            if not torch.isfinite(total):raise FloatingPointError('Nonfinite grouped flow likelihood')
            total.backward();opt.step();steps+=active
        val=validation();improved=active & (val<best-1e-5)
        if not torch.isfinite(val).all():raise FloatingPointError('Nonfinite grouped validation')
        best=torch.where(improved,val,best);bad=torch.where(improved,0,bad+active)
        for name,value in group.state_dict().items():best_state[name][improved]=value[improved]
        active=active & (bad<cfg['patience']);trace.append({'step':block+width,'early':val.tolist(),'active':active.tolist()})
        torch.cuda.synchronize()
        atomic_torch(path,{'keys':[r[1] for r in items],'state':group.state_dict(),'optimizer':opt.state_dict(),
            'rng':[g.get_state() for g in gens],'best':best,'bad':bad,'steps':steps,'active':active,'best_state':best_state,
            'step':block+width,'seconds':elapsed+time.monotonic()-started,'trace':trace})
    group.load_state_dict(best_state);group.unpack(models);torch.cuda.synchronize();seconds=elapsed+time.monotonic()-started
    result=[];total_updates=max(1,int(steps.sum()))
    for i,((j,key,seed),model) in enumerate(zip(items,models)):
        s={'key':key,'node':j,'parents':list(model.parents),'canonical_seed':seed,'updates':int(steps[i]),
            'fit_seconds':seconds*int(steps[i])/total_updates,'group_seconds':seconds,'group_id':gid,'group_size':k,
            'early_nll':float(best[i]),'peak_vram_bytes':torch.cuda.max_memory_allocated(),'cache_hit':False,
            'cost_allocation':'measured grouped elapsed apportioned by active mechanism updates; not serial-equivalent seconds'}
        atomic_torch(root()/'checkpoints'/(key+'.pt'),{'key':key,'complete':True,'best_state':model.state_dict(),'stats':s,'config':cfg})
        result.append(s)
    return result
