"""Fixed-budget approximation to phase-two MMD/parent/pair HSIC priorities."""
import torch
import numpy as np
from sem_update.diagnostics import mmd,hsic

@torch.no_grad()
def disturbances(model,environments,seed,cap=64,permutations=16,pair_cap=8,environment_cap=4):
    rng=np.random.default_rng(seed);obs=[e for e in environments if not e.targets][0]
    others=[e for e in environments if e.targets]
    chosen=sorted(rng.choice(len(others),min(environment_cap,len(others)),replace=False))
    envs=[obs]+[others[i] for i in chosen];gen=torch.Generator(device=obs.x.device).manual_seed(seed)
    xs=[e.x[torch.randperm(len(e.x),device=e.x.device,generator=gen)[:cap]] for e in envs]
    residuals=[model.infer_disturbances(x,e.targets) for x,e in zip(xs,envs)];result=[]
    for j in range(model.graph.d):
        terms={'marginal':[],'parents':[],'pairs':[]}
        for i,(e,x,rs) in enumerate(zip(envs,xs,residuals)):
            if j not in rs:continue
            u=rs[j]
            if i:terms['marginal'].append(mmd(u,residuals[0][j],gen,permutations)[1])
            pa=model.graph.parents(j)
            if pa:terms['parents'].append(hsic(u,x[:,pa],gen,permutations,True)[1])
            eligible=[k for k in rs if k!=j]
            peers=rng.choice(eligible,min(pair_cap,len(eligible)),replace=False)
            values=[hsic(u,rs[int(k)],gen,permutations)[1] for k in peers]
            if values:terms['pairs'].append(torch.stack(values).mean())
        means={k:float(torch.stack(v).mean()) if v else 0. for k,v in terms.items()}
        result.append({'node':j,'priority':sum(means.values()),'components':means,'environment_names':[e.name for e in envs],
            'pair_cap':pair_cap,'sample_cap':cap,'permutations':permutations})
    return result
