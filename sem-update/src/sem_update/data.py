"""Data roles are explicit; learner views cannot load final test arrays."""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import torch
from .graphs import DAG
from .runtime import digest, atomic_json, artifact_root, file_hash, read_json

ROLES = ('fit', 'early', 'search', 'audit')

@dataclass
class Environment:
    name: str
    x: torch.Tensor
    assignments: dict
    row_ids: tuple
    blocks: tuple = ()

    @property
    def targets(self):
        return tuple(sorted(int(k) for k in self.assignments))

def assign_values(spec, n, generator, device, dtype=torch.float32):
    values = {}
    # For joint assignment laws callers provide one joint draw as fixed vectors.
    for key,law in spec.items():
        j = int(key)
        if law['kind'] == 'normal':
            v = torch.randn(n, generator=generator, device=device, dtype=dtype)*law['scale']+law['mean']
        elif law['kind'] == 'uniform':
            v = torch.rand(n, generator=generator, device=device, dtype=dtype)*(law['high']-law['low'])+law['low']
        elif law['kind'] == 'fixed':
            v = torch.as_tensor(law['value'], device=device, dtype=dtype).expand(n)
        elif law['kind'] == 'discrete_uniform_dequantized':
            v = torch.randint(law['low'],law['high']+1,(n,),generator=generator,device=device).to(dtype)
            v = v+(torch.rand(n,generator=generator,device=device,dtype=dtype)-.5)*law['quantum']
            v = (v-law['location'])/law['spread']
        else:
            raise ValueError('unsupported assignment law')
        values[j] = v
    return values

class SyntheticSCM:
    def __init__(self, d, family, seed, semantic=False):
        self.d, self.family, self.seed = d,family,seed
        self.semantic = semantic
        rng = np.random.default_rng(seed)
        order = rng.permutation(d)
        edges = []
        if semantic:
            # Roles precede graph draws: two actuators, filter, two light sensors.
            order = np.arange(5)
            for a,b in ((0,3),(1,3),(0,4),(1,4),(2,3),(2,4)):
                if rng.random() < .75:
                    edges.append((a,b))
            for sensor in (3,4):
                if not any(a in (0,1) and b==sensor for a,b in edges):
                    edges.append((int(rng.integers(2)),sensor))
        else:
            for k in range(1,d):
                possible = order[:k]
                take = possible[rng.random(k) < min(1.,1.5/k)]
                if len(take)>3:
                    take = rng.choice(take,3,replace=False)
                edges.extend((int(a),int(order[k])) for a in take)
        self.graph = DAG(d,tuple(edges))
        self.weights = rng.choice([-1.,1.],(d,d))*rng.uniform(.5,1.5,(d,d))
        self.c = rng.normal(size=(d,d))
        self.b = rng.choice([-1.,1.], (d,d,d))*rng.uniform(.5,1.5,(d,d,d))
        self.sigma = rng.uniform(.3,.8,d)

    def sample(self, n, seed, assignments=None, device='cpu', noises=None):
        generator = torch.Generator(device=device).manual_seed(seed)
        u = torch.randn(n,self.d,generator=generator,device=device) if noises is None else noises
        x = torch.zeros_like(u)
        values = assign_values(assignments or {},n,generator,device,u.dtype)
        for j in self.graph.order():
            if j in values:
                x[:,j] = values[j]
                continue
            pa = self.graph.parents(j)
            if self.semantic and pa:
                sources=[a for a in pa if a in (0,1)]
                intensity=sum(abs(float(self.weights[a,j]))*torch.sigmoid(x[:,a]) for a in sources)/math.sqrt(len(sources))
                if 2 in pa:
                    intensity=intensity*(.2+.8*torch.sigmoid(-abs(float(self.weights[2,j]))*x[:,2]))
                scale=.3+.4*torch.sigmoid(intensity)
                x[:,j]=intensity+scale*u[:,j]
                continue
            m = torch.zeros(n,device=device,dtype=u.dtype)
            for a in pa:
                val = x[:,a] if self.family == 'linear' else torch.tanh(x[:,a])
                m = m + float(self.weights[a,j])*val/math.sqrt(max(1,len(pa)))
            if self.family != 'linear':
                for i,a in enumerate(pa):
                    for b in pa[i+1:]:
                        m = m+.3*float(self.b[j,a,b])*torch.tanh(x[:,a]*x[:,b])/max(1,len(pa))
            scale = self.sigma[j]
            if self.family == 'heteroscedastic' and pa:
                z = sum(float(self.c[a,j])*x[:,a] for a in pa)/math.sqrt(len(pa))
                scale = .3+.7*torch.sigmoid(z)
            noise = u[:,j]
            if not pa and self.family != 'linear':
                noise = noise+.1*noise**3
            x[:,j] = m+scale*noise
        return x

    def json(self):
        return {'d': self.d, 'family': self.family, 'seed': self.seed, 'semantic':self.semantic,'graph': self.graph.json(),
                'weights': self.weights.tolist(), 'c': self.c.tolist(), 'b': self.b.tolist(), 'sigma': self.sigma.tolist()}

class LearnerData:
    def __init__(self, manifest, arrays, device):
        self.manifest = manifest
        self.d = manifest['d']
        self.key = manifest['dataset_hash']
        self.preprocessing_hash = digest(manifest['standardization'])
        self.roles = {}
        for role in ROLES:
            self.roles[role] = []
            for env in manifest['splits'][role]:
                self.roles[role].append(Environment(env['name'], torch.tensor(arrays[env['array']], device=device),
                                                   env['assignments'],tuple(env['row_ids']),tuple(env.get('blocks',[]))))

    def get(self, role):
        if role not in ROLES:
            raise ValueError('learner cannot request final test data')
        return self.roles[role]

def prepare_synthetic(d, family, seed, budget, development=False, semantic=False):
    identity = f'{"dev" if development else "benchmark"}-{family}-d{d}-s{seed}-B{budget}' + ('-semantic' if semantic else '')
    root = artifact_root() / 'data/processed' / identity
    root.mkdir(parents=True,exist_ok=True)
    if (root/'manifest.json').exists():
        return root
    scm = SyntheticSCM(d,family,seed,semantic=semantic)
    # Independent role-specific seeds give nested B=100 / 400 rows within each role.
    obs_counts = dict(fit=4096,early=1024,search=1024,audit=512)
    fit_obs = scm.sample(4096,seed*1000+10).numpy()
    mu,sd = fit_obs.mean(0),fit_obs.std(0).clip(1e-5)
    rng = np.random.default_rng(seed+8723)
    seen = sorted(map(int, rng.choice(d,3 if d==5 else 6,replace=False)))
    if semantic:
        seen = [0,1,2] # Manipulated module controls, policy fixed before generation.
    arrays,splits = {},{}
    for ri,role in enumerate(ROLES):
        splits[role] = []
        nobs = obs_counts[role]
        data = scm.sample(nobs,seed*1000+10+ri).numpy()
        arrkey = role+'_obs'
        arrays[arrkey] = ((data-mu)/sd).astype('float32')
        splits[role].append({'name':'obs','array':arrkey,'assignments':{},
                             'row_ids':[f'{seed}:obs:{role}:{i}' for i in range(nobs)]})
        n = int(budget*dict(fit=.6,early=.1,search=.2,audit=.1)[role])
        for j in seen:
            physical = {j:{'kind':'normal','mean':float(mu[j]+sd[j]),'scale':float(.25*sd[j])}}
            # Always draw maximum budget in a role before taking prefix; target RNG also nests.
            full = scm.sample(400,seed*1000+100+ri*20+j,physical).numpy()[:n]
            arrkey = f'{role}_do{j}'
            arrays[arrkey] = ((full-mu)/sd).astype('float32')
            splits[role].append({'name':f'do{j}+','array':arrkey,
                                 'assignments':{str(j):{'kind':'normal','mean':1.,'scale':.25}},
                                 'row_ids':[f'{seed}:do{j}:{role}:{i}' for i in range(n)]})
    manifest = {'id':identity,'d':d,'family':family,'seed':seed,'budget_per_target':budget,
                'non_test_intervention_rows':len(seen)*budget,'seen_targets':seen,'development':development,
                'standardization':{'mean':mu.tolist(),'std':sd.tolist()},'splits':splits,
                'generator_version':2,'semantic':semantic}
    validate_splits(manifest)
    np.savez_compressed(root/'learner.npz',**arrays)
    manifest['arrays_sha256'] = file_hash(root/'learner.npz')
    manifest['dataset_hash'] = digest(manifest)
    atomic_json(root/'manifest.json',manifest)
    atomic_json(root/'truth.json',scm.json()) # Deliberately separate from learner view/prompts.
    return root

def load_learner(root, device):
    root = Path(root)
    manifest = read_json(root/'manifest.json')
    validate_splits(manifest)
    if file_hash(root/'learner.npz') != manifest['arrays_sha256']:
        raise ValueError('dataset checksum mismatch')
    return LearnerData(manifest,np.load(root/'learner.npz'),device)

def validate_splits(manifest):
    seen = set()
    blocks = set()
    for role,envs in manifest['splits'].items():
        for env in envs:
            ids = set(env['row_ids'])
            if len(ids) != len(env['row_ids']) or ids & seen:
                raise ValueError('overlapping or duplicate row IDs')
            seen |= ids
            b = {(env['name'],v) for v in env.get('blocks',[])}
            if b & blocks:
                raise ValueError('overlapping acquisition blocks')
            blocks |= b
