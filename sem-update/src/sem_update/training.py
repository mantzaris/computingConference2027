"""Node-local canonical fitting. Only environment-balanced NLL is optimized."""
import copy
import os
import time
import importlib.metadata
from pathlib import Path
import torch
from .flows import Mechanism, GenerativeSCM
from .runtime import artifact_root, digest, file_hash, check_budget

DEFAULT_TRAIN = dict(width=64,bins=8,transforms=2,steps=1000,batch_size=256,
                     learning_rate=.001,weight_decay=.00001,check_every=50,patience=5,seed=707)

def cache_key(data, node, parents, config, kind):
    return digest({'dataset':data.key,'fit_split':digest(data.manifest['splits']['fit']),
                   'early_split':digest(data.manifest['splits']['early']), 'node':node,
                   'ordered_parents':list(parents),'preprocessing':data.preprocessing_hash,
                   'training':config,'kind':kind,
                   'software':{'torch':torch.__version__,'nflows':importlib.metadata.version('nflows')},
                   'device_type':data.get('fit')[0].x.device.type,
                   'implementation':{p.name:file_hash(p) for p in (Path(__file__),Path(__file__).with_name('flows.py'))}})

def atomic_torch(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    torch.save(value,temp)
    with open(temp,'rb') as f:
        os.fsync(f.fileno())
    os.replace(temp,path)

def fit_node(data, node, parents, config=None, kind='flow', use_cache=True, allow_training=True):
    config = {**DEFAULT_TRAIN,**(config or {})}
    key = cache_key(data,node,parents,config,kind)
    seed = int(key[:8],16) % (2**31-1)
    device = data.get('fit')[0].x.device
    cache_dir = artifact_root()/'checkpoints'/key[:2]
    cache_dir.mkdir(parents=True,exist_ok=True)
    path = cache_dir/(key+'.pt')
    resume_path = cache_dir/(key+'.partial.pt')
    devices = [device.index or 0] if device.type == 'cuda' else []
    with torch.random.fork_rng(devices=devices):
        torch.manual_seed(seed)
        model = Mechanism(parents,config['width'],config['bins'],config['transforms'],kind).to(device)
    if use_cache and path.exists():
        checkpoint = torch.load(path,map_location=device,weights_only=False)
        if checkpoint['key'] != key or not checkpoint['complete']:
            raise ValueError('invalid cached mechanism')
        model.load_state_dict(checkpoint['best_state'])
        return model,{**checkpoint['stats'],'cache_hit':True,'key':key,'actual_seconds':0.,'actual_updates':0}
    if not allow_training:
        raise RuntimeError('final evaluation may only load frozen completed mechanisms: '+key)
    eligible = [e.x for e in data.get('fit') if node not in e.targets]
    early = [e.x for e in data.get('early') if node not in e.targets]
    pool = torch.cat(eligible)
    counts = torch.tensor([len(x) for x in eligible],device=device)
    offsets = counts.cumsum(0)-counts
    gen = torch.Generator(device=device).manual_seed(seed+1)
    optimizer = torch.optim.Adam(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    best,best_state,bad,first = float('inf'),None,0,0
    elapsed,trace = 0.,[]
    if use_cache and resume_path.exists():
        ck = torch.load(resume_path,map_location=device,weights_only=False)
        if ck['key'] != key:
            raise ValueError('incompatible mechanism resume')
        model.load_state_dict(ck['state'])
        optimizer.load_state_dict(ck['optimizer'])
        gen.set_state(ck['batch_rng'].cpu())
        best,best_state,bad,first = ck['best'],ck['best_state'],ck['bad'],ck['step']
        trace,elapsed = ck['trace'],ck['elapsed']
    if device.type == 'cuda':
        torch.cuda.synchronize()
    start = time.monotonic()
    step = first
    payload=ck if use_cache and resume_path.exists() else None
    last_step=first if bad>=config['patience'] else config['steps']
    check_budget()
    for step in range(first+1,last_step+1):
        # Uniform eligible environment, then uniform row: exactly unbiased for eq. (3).
        eid = torch.randint(len(eligible),(config['batch_size'],),generator=gen,device=device)
        idx = (torch.rand(config['batch_size'],generator=gen,device=device)*counts[eid]).long()+offsets[eid]
        x = pool[idx]
        optimizer.zero_grad(set_to_none=True)
        loss = -model.log_probability(x[:,node],x).mean()
        if not torch.isfinite(loss):
            raise FloatingPointError(f'nonfinite fitting loss: {key}, step {step}')
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise FloatingPointError('nonfinite mechanism gradients')
        optimizer.step()
        if step % config['check_every'] == 0 or step == config['steps']:
            check_budget()
            with torch.no_grad():
                score = torch.stack([-model.log_probability(x[:,node],x).mean() for x in early]).mean().item()
            trace.append({'step':step,'fit_batch_nll':loss.item(),'early_nll':score})
            if score < best-1e-5:
                best,best_state,bad = score,copy.deepcopy(model.state_dict()),0
            else:
                bad += 1
            payload = {'key':key,'complete':False,'state':model.state_dict(),'optimizer':optimizer.state_dict(),
                       'best':best,'best_state':best_state,'bad':bad,'step':step,'trace':trace,
                       'batch_rng':gen.get_state(),'cpu_rng':torch.get_rng_state(),
                       'cuda_rng':torch.cuda.get_rng_state_all() if device.type=='cuda' else [],
                       'elapsed':elapsed+time.monotonic()-start,'config':config,'data_hash':data.key}
            if use_cache:
                atomic_torch(resume_path,payload)
            if bad >= config['patience']:
                break
    if device.type == 'cuda':
        torch.cuda.synchronize()
    actual = time.monotonic()-start
    stats = {'updates':step,'canonical_seed':seed,'fit_seconds':elapsed+actual,
             'early_nll':best,'eligible_environments':len(eligible),'node':node,'parents':list(parents),
             'peak_vram_bytes':torch.cuda.max_memory_allocated() if device.type=='cuda' else 0}
    model.load_state_dict(best_state)
    if use_cache:
        atomic_torch(path,{**payload,'complete':True,'best_state':best_state,'stats':stats})
        # Partial checkpoints are retained as evidence, not removed for disk accounting.
    return model,{**stats,'cache_hit':False,'key':key,'actual_seconds':actual,'actual_updates':step-first}

def fit_graph(data, graph, config=None, kind='flow', allow_training=True):
    mechanisms,stats = [],[]
    for j in range(graph.d):
        m,s = fit_node(data,j,graph.parents(j),config,kind,allow_training=allow_training)
        mechanisms.append(m)
        stats.append(s)
    return GenerativeSCM(graph,mechanisms),stats
