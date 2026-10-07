"""Scalar conditional RQ splines + affine map with exact parent selection."""
import math
import torch
from torch import nn
from torch.nn import functional as F
from nflows.transforms.splines.rational_quadratic import unconstrained_rational_quadratic_spline

class Mechanism(nn.Module):
    def __init__(self, parents, width=64, bins=8, transforms=2, kind='flow'):
        super().__init__()
        self.parents = tuple(parents)
        self.bins, self.transforms, self.kind = bins,transforms,kind
        size = transforms*(3*bins-1)+2 if kind == 'flow' else 1
        if parents:
            self.conditioner = nn.Sequential(nn.Linear(len(parents),width),nn.SiLU(),
                                             nn.Linear(width,width),nn.SiLU(),nn.Linear(width,size))
            nn.init.zeros_(self.conditioner[-1].weight)
            nn.init.zeros_(self.conditioner[-1].bias)
        else:
            self.constant = nn.Parameter(torch.zeros(size))
        if kind == 'additive':
            self.log_scale = nn.Parameter(torch.tensor(0.))
        else:
            bias = self.conditioner[-1].bias if parents else self.constant
            with torch.no_grad():
                for k in range(transforms):
                    start = k*(3*bins-1)+2*bins
                    bias[start:start+bins-1] = math.log(math.expm1(1-.001))
                bias[-1] = math.log(math.expm1(1-.05))

    def parameters_for(self, x):
        if self.parents:
            return self.conditioner(x[:,self.parents])
        return self.constant.expand(len(x),-1)

    def _spline(self, values, p, inverse):
        k = self.bins
        return unconstrained_rational_quadratic_spline(values,p[:,:k],p[:,k:2*k],p[:,2*k:],
                    inverse=inverse,tails='linear',tail_bound=5.,min_bin_width=.001,
                    min_bin_height=.001,min_derivative=.001)

    def forward_noise(self, u, x):
        p = self.parameters_for(x)
        if self.kind == 'additive':
            scale = self.log_scale.exp().clamp_min(.01)
            return p[:,0]+scale*u, torch.ones_like(u)*scale.log()
        z,logdet = u,torch.zeros_like(u)
        step = 3*self.bins-1
        for k in range(self.transforms):
            z,ld = self._spline(z,p[:,k*step:(k+1)*step],False)
            logdet = logdet+ld
        scale = .05+F.softplus(p[:,-1])
        return p[:,-2]+scale*z,logdet+scale.log()

    def inverse_noise(self, y, x):
        p = self.parameters_for(x)
        if self.kind == 'additive':
            scale = self.log_scale.exp().clamp_min(.01)
            return (y-p[:,0])/scale, -torch.ones_like(y)*scale.log()
        scale = .05+F.softplus(p[:,-1])
        z,logdet = (y-p[:,-2])/scale,-scale.log()
        step = 3*self.bins-1
        for k in reversed(range(self.transforms)):
            z,ld = self._spline(z,p[:,k*step:(k+1)*step],True)
            logdet = logdet+ld
        return z,logdet

    def log_probability(self, y, x):
        u,inverse_logdet = self.inverse_noise(y,x)
        return -.5*(u*u+math.log(2*math.pi))+inverse_logdet

class GenerativeSCM(nn.Module):
    def __init__(self, graph, mechanisms):
        super().__init__()
        self.graph = graph
        self.mechanisms = nn.ModuleList(mechanisms)
        for j,m in enumerate(mechanisms):
            if m.parents != graph.parents(j):
                raise ValueError('mechanism parent mask does not match DAG')

    def log_probability(self, x, targets=()):
        # Target mechanisms are never even evaluated: no masked NaN contamination.
        active = [j for j in range(self.graph.d) if j not in targets]
        return torch.stack([self.mechanisms[j].log_probability(x[:,j],x) for j in active],1)

    def infer_disturbances(self, x, targets=()):
        return {j:self.mechanisms[j].inverse_noise(x[:,j],x)[0] for j in range(self.graph.d) if j not in targets}

    def sample_intervention(self, noises, assignments):
        columns = {}
        for j in self.graph.order():
            if j in assignments:
                columns[j] = torch.as_tensor(assignments[j],device=noises.device,dtype=noises.dtype).expand(len(noises))
            else:
                context = torch.stack([columns.get(k,torch.zeros_like(noises[:,0])) for k in range(self.graph.d)],1)
                columns[j] = self.mechanisms[j].forward_noise(noises[:,j],context)[0]
        return torch.stack([columns[j] for j in range(self.graph.d)],1)

    def sample_observational(self, noises):
        return self.sample_intervention(noises,{})

    def sample_counterfactual(self, factual, assignments):
        u = self.infer_disturbances(factual)
        return self.sample_intervention(torch.stack([u[j] for j in range(self.graph.d)],1),assignments)

def balanced_nll(model, environments):
    node_losses = []
    for j,m in enumerate(model.mechanisms):
        values = [-m.log_probability(e.x[:,j],e.x).mean() for e in environments if j not in e.targets]
        if values:
            node_losses.append(torch.stack(values).mean())
    return torch.stack(node_losses).mean()
