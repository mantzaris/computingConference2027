"""Official DCDI-DSF density with the documented phase-two training adapter.

The external MIT implementation is revision-pinned, retained under .artifacts,
and never added to this repository. This is an adaptation, not exact published
hyperparameter reproduction. Only known perfect interventions are supported.
"""
import copy
import math
import sys
import time
from pathlib import Path
import numpy as np
import torch
from sem_update.graphs import DAG
from sem_update.runtime import artifact_root,atomic_json,read_json,digest,command,check_budget
from sem_update.training import atomic_torch

REVISION='594d328eae7795785e0d1a1138945e28a4fec037'
DEFAULT=dict(width=64,layers=2,steps=40000,block_steps=100,batch_size=256,
             learning_rate=.001,reg_coeff=.1,seed=8821,threshold=.5,max_indegree=3)

def official_model(d,config):
    from sem_update.phase2.discovery import official_dsf
    import types
    model=official_dsf(d,config)
    # Algebraically identical to upstream einsums; omit unused nonzero-weight
    # telemetry that synchronizes the device after every layer on every step.
    model.forward_given_params=types.MethodType(batched_forward,model)
    return model

def batched_forward(self,x,weights,biases,mask=None,regime=None):
    from torch.nn import functional as F
    M=self.gumbel_adjacency(len(x))*self.adjacency[None]
    context=(M*x[:,:,None]).permute(2,0,1)
    value=torch.bmm(context,weights[0].transpose(1,2))+biases[0][:,None]
    value=F.leaky_relu(value)
    for i in range(1,self.num_layers+1):
        value=torch.bmm(value,weights[i].transpose(1,2))+biases[i][:,None]
        if i!=self.num_layers:value=F.leaky_relu(value)
    return tuple(value.unbind(0))

def discover(data,config=None,root_nodes=()):
    if data.get('fit')[0].x.device.type!='cuda':
        raise RuntimeError('DCDI neural baseline must run on CUDA')
    cfg={**DEFAULT,**(config or {})}
    identity={'data':data.key,'config':cfg,'roots':list(root_nodes),'source':REVISION,'adapter_version':3,'adapter_sha256':__import__('sem_update.runtime',fromlist=['file_hash']).file_hash(__file__)}
    key=digest(identity)
    folder=artifact_root()/'runs'/('dcdi-'+key[:20])
    folder.mkdir(exist_ok=True,parents=True)
    result_path=folder/'discovery.json'
    if result_path.exists():
        result=read_json(result_path)
        if 'h_normalized' not in result:
            # Preserve the original development record; correct its reporting
            # in the returned summary without changing any fit or graph.
            last=read_json(folder/'trace.json')[-1]
            result['original_raw_convergence_label']=result['converged']
            result['h_normalized']=result['h_raw']*last['h_normalized']/last['h_raw']
            result['converged']=result['h_normalized']<=1e-8
            result['convergence_reporting_correction']='normalized criterion actually used by optimizer; original discovery.json retained'
        return result
    torch.cuda.reset_peak_memory_stats()
    torch.manual_seed(cfg['seed'])
    np.random.seed(cfg['seed'])
    model=official_model(data.d,cfg)
    for j in root_nodes:
        model.adjacency[:,j]=0
    opt=torch.optim.RMSprop(model.parameters(),lr=cfg['learning_rate'])
    envs=data.get('fit')
    pool=torch.cat([e.x for e in envs])
    counts=torch.tensor([len(e.x) for e in envs],device='cuda')
    offsets=counts.cumsum(0)-counts
    intact=torch.tensor([[j not in e.targets for j in range(data.d)] for e in envs],device='cuda').float()
    node_weights=intact*len(envs)/intact.sum(0)
    normalization=(torch.matrix_exp(model.adjacency.double()).trace()-data.d).item()
    normalization=max(normalization,1.)
    mu,gamma,previous_h=1e-8,0.,float('inf')
    trace=[]
    validation_objectives=[]
    updates_since_multiplier=0
    begin=0
    state_path=folder/'optimizer.pt'
    elapsed=0.
    if state_path.exists():
        ck=torch.load(state_path,weights_only=False)
        if ck['identity']!=identity:
            raise ValueError('incompatible DCDI resume')
        model.load_state_dict(ck['model'])
        opt.load_state_dict(ck['optimizer'])
        torch.set_rng_state(ck['cpu_rng'].cpu())
        torch.cuda.set_rng_state(ck['cuda_rng'].cpu())
        begin,mu,gamma,previous_h=ck['step'],ck['mu'],ck['gamma'],ck['previous_h']
        trace,elapsed=ck['trace'],ck['elapsed']
        validation_objectives=ck.get('validation_objectives',[])
        updates_since_multiplier=ck.get('updates_since_multiplier',0)
    start=time.monotonic()
    for step in range(begin+1,cfg['steps']+1):
        eid=torch.randint(len(envs),(cfg['batch_size'],),device='cuda')
        idx=(torch.rand(cfg['batch_size'],device='cuda')*counts[eid]).long()+offsets[eid]
        x=pool[idx]
        lp=model.compute_log_likelihood(x,*model.get_parameters())
        loss=-(lp*node_weights[eid]).mean()
        a=model.get_w_adj()
        # Same trace-exponential constraint; float64 CUDA avoids cancellation.
        h=(torch.matrix_exp(a.double()).trace()-data.d)/normalization
        reg=cfg['reg_coeff']*a.sum()/data.d**2
        objective=loss+reg+gamma*h+.5*mu*h*h
        if not torch.isfinite(objective):
            raise FloatingPointError('DCDI objective became nonfinite')
        opt.zero_grad(set_to_none=True)
        objective.backward()
        opt.step()
        updates_since_multiplier+=1
        if step%cfg['block_steps']==0:
            check_budget()
            value=h.item()
            # Official stationarity check uses three consecutive early-validation
            # augmented objectives. The original's argument called test_data is
            # mapped here ONLY to early-stop data, never benchmark final tests.
            with torch.no_grad():
                per_node=[[] for _ in range(data.d)]
                for env in data.get('early'):
                    lp=torch.cat([model.compute_log_likelihood(xx,*model.get_parameters()) for xx in env.x.split(256)])
                    for j in range(data.d):
                        if j not in env.targets:
                            per_node[j].append(-lp[:,j].mean())
                early_nll=torch.stack([torch.stack(v).mean() for v in per_node]).mean().item()
            validation_objectives.append(early_nll+reg.item()+gamma*value+.5*mu*value*value)
            trace.append({'step':step,'nll':loss.item(),'h_normalized':value,
                          'early_nll':early_nll,'h_raw':value*normalization,'mu':mu,'gamma':gamma})
            stationary=False
            if len(validation_objectives)>=3 and step%(2*cfg['block_steps'])==0:
                t0,t_half,t1=validation_objectives[-3:]
                monotone=min(t0,t1)<t_half<max(t0,t1)
                slope=(t1-t0)/cfg['block_steps']
                stationary=monotone and (abs(slope)<.001 or slope>0)
            # A bounded plateau fallback prevents stochastic validation wiggles
            # from withholding all multiplier updates indefinitely.
            if stationary or updates_since_multiplier>=4000:
                gamma+=mu*value
                if value>.9*previous_h:
                    mu=min(mu*10,1e12)
                previous_h=value
                opt=torch.optim.RMSprop(model.parameters(),lr=cfg['learning_rate'])
                updates_since_multiplier=0
            binary=(model.get_w_adj().detach().cpu().numpy()>.5)
            try:
                threshold_graph=DAG(data.d,tuple(zip(*np.where(binary))))
                acyclic=True
            except ValueError:
                acyclic=False
            atomic_torch(state_path,{'identity':identity,'model':model.state_dict(),'optimizer':opt.state_dict(),
                        'step':step,'mu':mu,'gamma':gamma,'previous_h':previous_h,'trace':trace,
                        'validation_objectives':validation_objectives,'updates_since_multiplier':updates_since_multiplier,
                        'elapsed':elapsed+time.monotonic()-start,'cpu_rng':torch.get_rng_state(),
                        'cuda_rng':torch.cuda.get_rng_state()})
            atomic_json(folder/'trace.json',trace)
            if (value<=1e-8 and acyclic) or elapsed+time.monotonic()-start>=cfg.get('seconds',float('inf')):
                break
    torch.cuda.synchronize()
    a=model.get_w_adj().detach().cpu().numpy()
    # Prespecified threshold, then remove weakest problematic edge; disclose all
    # cycle/indegree projection rather than misreporting convergence.
    edges=[(int(i),int(j)) for i,j in zip(*np.where(a>cfg['threshold']))]
    import networkx as nx
    threshold_acyclic=nx.is_directed_acyclic_graph(nx.DiGraph(edges))
    threshold_edges=len(edges);removed=[];projection_details=[]
    while True:
        try:
            graph=DAG(data.d,tuple(edges))
            excess=[j for j in range(data.d) if len(graph.parents(j))>cfg['max_indegree']]
            if not excess:
                break
            options=[e for e in edges if e[1] in excess]
            reason='indegree'
        except ValueError:
            import networkx as nx
            raw=nx.DiGraph(edges)
            cycle=nx.find_cycle(raw)
            options=[(i,j) for i,j in cycle]
            reason='cycle'
        weakest=min(options,key=lambda e:(a[e[0],e[1]],e))
        edges.remove(weakest)
        removed.append(list(weakest))
        projection_details.append({'edge':list(weakest),'reason':reason})
    h_raw=float((torch.matrix_exp(model.get_w_adj().double()).trace()-data.d).item())
    stop_reason=('step_cap' if step>=cfg['steps'] else
                 'time_cap' if elapsed+time.monotonic()-start>=cfg.get('seconds',float('inf')) else 'legacy_stopping_rule')
    result={'graph':graph.json(),'identity':identity,'seconds':elapsed+time.monotonic()-start,
            'h_raw':h_raw,'h_normalized':h_raw/normalization,'converged':h_raw/data.d<=1e-8,'legacy_converged':h_raw/normalization<=1e-8,'h_per_node':h_raw/data.d,
            'convergence_criterion':'raw trace-exponential / d <= 1e-8; legacy optimizer stopping rule retained separately',
            'projection_removed_edges':removed,
            'projection_details':projection_details,'threshold_acyclic':threshold_acyclic,'threshold_edges':threshold_edges,
            'optimization_steps':step,'peak_vram_bytes':torch.cuda.max_memory_allocated(),
            'native_probabilities':a.tolist(),'implementation':'DCDI-DSF + common flows; validated batched upstream conditioner; phase-two optimizer adaptation',
            'status':('converged' if h_raw/data.d<=1e-8 else 'valid_legacy_stop_not_strict' if stop_reason=='legacy_stopping_rule' else 'valid_capped_prediction'),
            'stop_reason':stop_reason,'time_cap_seconds':cfg.get('seconds'), 'upstream_revision':REVISION}
    atomic_json(result_path,result)
    return result
