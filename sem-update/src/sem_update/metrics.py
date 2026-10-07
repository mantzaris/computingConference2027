"""Distributional metrics; deterministic projections and common quantile grid."""
import torch

def projections(d, count, seed, device, dtype=torch.float32):
    generator = torch.Generator(device=device).manual_seed(seed)
    v = torch.randn(d,count,generator=generator,device=device,dtype=dtype)
    return v / v.norm(dim=0,keepdim=True).clamp_min(1e-12)

def wasserstein(x,y,count=64,seed=99):
    if x.shape[1] == 0:
        return torch.tensor(0.,device=x.device)
    v = projections(x.shape[1],count,seed,x.device,x.dtype)
    q = (torch.arange(512,device=x.device,dtype=x.dtype)+.5)/512
    xp,yp = x@v,y@v
    return (torch.quantile(xp,q,dim=0)-torch.quantile(yp,q,dim=0)).abs().mean()

def energy(x,y,seed=199,pairs=8192):
    """Independent sampled ordered pairs, distinct indices within each sample."""
    g = torch.Generator(device=x.device).manual_seed(seed)
    def within(z):
        a = torch.randint(len(z),(pairs,),generator=g,device=z.device)
        offset = torch.randint(1,len(z),(pairs,),generator=g,device=z.device)
        return (z[a]-z[(a+offset)%len(z)]).norm(dim=1).mean()
    a = torch.randint(len(x),(pairs,),generator=g,device=x.device)
    b = torch.randint(len(y),(pairs,),generator=g,device=y.device)
    return 2*(x[a]-y[b]).norm(dim=1).mean()-within(x)-within(y)

def distribution_metrics(actual, generated, projections_count=256, seed=99):
    result = {'sw1':wasserstein(actual,generated,projections_count,seed).item(),
              'energy':energy(actual,generated,seed+1).item(),
              'mean_rmse':((actual.mean(0)-generated.mean(0))**2).mean().sqrt().item(),
              'variance_rmse':((actual.var(0)-generated.var(0))**2).mean().sqrt().item()}
    for level in (.5,.9):
        low,high = torch.quantile(generated,torch.tensor([(1-level)/2,(1+level)/2],device=generated.device),dim=0)
        result[f'coverage_{int(level*100)}'] = ((actual>=low)&(actual<=high)).float().mean().item()
        result[f'width_{int(level*100)}'] = (high-low).mean().item()
    result['marginal_w1'] = [wasserstein(actual[:,j:j+1],generated[:,j:j+1],1,seed).item() for j in range(actual.shape[1])]
    return result
