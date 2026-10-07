"""Capped CUDA kernel diagnostics, permutation-normalized scheduling only."""
import torch

def kernel(x, bandwidths=(.5,1.,2.)):
    if x.ndim==1:
        x=x[:,None]
    distances=torch.cdist(x,x).square()
    return torch.stack([torch.exp(-distances/(2*b*b)) for b in bandwidths]).mean(0)

def centered(k):
    return k-k.mean(0,keepdim=True)-k.mean(1,keepdim=True)+k.mean()

def normalized(observed, null):
    return ((observed-null.mean())/(null.std(unbiased=False)+1e-6)).clamp_min(0.)

def hsic(x,y,generator,permutations=32,parent=False):
    k = centered(kernel(x))
    # Standardized parent bandwidth sqrt(number of parents), fixed before candidates.
    bandwidths = (max(1,y.shape[1])**.5,) if parent and y.ndim>1 else (.5,1.,2.)
    l = centered(kernel(y,bandwidths))
    n=len(x)
    stat=(k*l).sum()/max(1,(n-1)**2)
    indices=torch.stack([torch.randperm(n,generator=generator,device=x.device) for _ in range(permutations)])
    null=(k[None]*l[indices[:,:,None],indices[:,None,:]]).sum((1,2))/max(1,(n-1)**2)
    return stat,normalized(stat,null)

def mmd(x,y,generator,permutations=32):
    k=kernel(torch.cat([x,y]))
    n,m=len(x),len(y)
    weights=torch.cat([torch.ones(n,device=x.device)/n,-torch.ones(m,device=x.device)/m])
    stat=weights@k@weights # Biased nonnegative empirical MMD^2.
    indices=torch.stack([torch.randperm(n+m,generator=generator,device=x.device) for _ in range(permutations)])
    w=weights[indices]
    null=(w@k*w).sum(1)
    return stat.clamp_min(0.),normalized(stat,null)

@torch.no_grad()
def disturbances(model,environments,seed=491,cap=256,permutations=32,marginal_only=False):
    device=environments[0].x.device
    g=torch.Generator(device=device).manual_seed(seed)
    residuals=[]
    xs=[]
    for env in environments:
        idx=torch.randperm(len(env.x),generator=g,device=device)[:cap]
        x=env.x[idx]
        xs.append(x)
        residuals.append(model.infer_disturbances(x,env.targets))
    reference=next(i for i,e in enumerate(environments) if not e.targets)
    result=[]
    for j in range(model.graph.d):
        terms={'marginal':[],'parents':[],'pairs':[]}
        detail=[]
        for i,env in enumerate(environments):
            if j not in residuals[i]:
                detail.append({'environment':env.name,'targeted':True,'n':len(xs[i])})
                continue
            u=residuals[i][j]
            entry={'environment':env.name,'targeted':False,'n':len(u)}
            if i!=reference:
                stat,z=mmd(u,residuals[reference][j],g,permutations)
                terms['marginal'].append(z)
                entry.update(mmd=stat.item(),mmd_z=z.item())
            pa=model.graph.parents(j)
            if pa and not marginal_only:
                stat,z=hsic(u,xs[i][:,pa],g,permutations,parent=True)
                terms['parents'].append(z)
                entry.update(parent_hsic=stat.item(),parent_z=z.item())
            pairs=[]
            if not marginal_only:
                for k,v in residuals[i].items():
                    if k!=j:
                        stat,z=hsic(u,v,g,permutations)
                        pairs.append(z)
                if pairs:
                    terms['pairs'].append(torch.stack(pairs).mean())
                    entry['pair_z']=torch.stack(pairs).mean().item()
            detail.append(entry)
        means={key:torch.stack(v).mean().item() if v else 0. for key,v in terms.items()}
        result.append({'node':j,'priority':sum(means.values()),'components':means,
                       'normalization_interpretation':'descriptive row permutations; temporal dependence may remain' if any(e.blocks for e in environments) else 'permutation-standardized scheduling heuristic, not a p-value',
                       'available':{key:bool(v) for key,v in terms.items()},'environments':detail})
    return result
