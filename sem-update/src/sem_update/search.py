"""Common verifier, bounded search and exactly one audit. No final-test access."""
import time
from pathlib import Path
import numpy as np
import torch
from .data import assign_values
from .diagnostics import disturbances
from .flows import balanced_nll
from .graphs import DAG
from .metrics import wasserstein
from .runtime import artifact_root, atomic_json, read_json, digest
from .training import fit_graph

DEFAULT_SEARCH = dict(candidate_budget=12,rounds=4,per_round=3,beta=1.,edge_penalty=.02,
                      improvement=.005,audit_w_factor=1.05,audit_w_slack=.001,audit_nll_slack=.05,
                      samples=512,projections=64,seed=491,diagnostic_cap=256,permutations=32)

@torch.no_grad()
def score(model, environments, config=None, role='search'):
    config={**DEFAULT_SEARCH,**(config or {})}
    nll=balanced_nll(model,environments).item()
    distances=[]
    device=environments[0].x.device
    for i,env in enumerate(environments):
        if not env.targets:
            continue
        seed=config['seed']+i*19+{'search':0,'audit':10000}[role]
        g=torch.Generator(device=device).manual_seed(seed)
        u=torch.randn(config['samples'],model.graph.d,generator=g,device=device)
        values=assign_values(env.assignments,len(u),g,device)
        y=model.sample_intervention(u,values)
        keep=[j for j in range(model.graph.d) if j not in env.targets]
        distances.append(wasserstein(env.x[:,keep],y[:,keep],config['projections'],seed).item())
    w=float(np.mean(distances)) if distances else 0.
    penalty=config['edge_penalty']*len(model.graph.edges)/model.graph.d
    return {'nll':nll,'sw1':w,'edge_penalty':penalty,'total':nll+config['beta']*w+penalty,
            'environment_sw1':distances}

def audit_pass(initial,selected,config):
    return (selected['sw1'] <= config['audit_w_factor']*initial['sw1']+config['audit_w_slack'] and
            selected['nll'] <= initial['nll']+config['audit_nll_slack'])

def repair(data, starts, run_id, policy='diagnostic',train_config=None,search_config=None,
           kind='flow',root_nodes=(),llm_callback=None):
    config={**DEFAULT_SEARCH,**(search_config or {})}
    identity={'data':data.key,'starts':[g.json() for g in starts], 'policy':policy,
              'train':train_config,'search':config,'kind':kind,'root_nodes':list(root_nodes)}
    folder=artifact_root()/'runs'/run_id
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'selection.json'
    state_path=folder/'search_state.json'
    identity_path=folder/'identity.json'
    if identity_path.exists() and read_json(identity_path)!=identity:
        raise ValueError('incompatible task identity')
    atomic_json(identity_path,identity)
    if path.exists():
        record=read_json(path)
        if record['identity_hash'] != digest(identity):
            raise ValueError('incompatible completed search resume')
        return record
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    candidates, models, diagnostic_records, edits = {},{},{},[]
    round_start,stalls,slots,start_time=0,0,0,time.monotonic()
    carried_seconds=0.
    if (folder/'diagnostics.json').exists():
        diagnostic_records=read_json(folder/'diagnostics.json')
    initial_key,incumbent_key=None,None
    rng=np.random.default_rng(config['seed'])
    if state_path.exists():
        state=read_json(state_path)
        if state['identity_hash']!=digest(identity):
            raise ValueError('incompatible search resume')
        candidates=state['candidates']
        edits=state['edits']
        initial_key,incumbent_key=state['initial'],state['incumbent']
        round_start,stalls,slots=state['next_round'],state['stalls'],state['slots']
        rng.bit_generator.state=state['rng_state']
        carried_seconds=state['elapsed_seconds']

    def evaluate(graph, edit=None):
        key=graph.key
        if key not in models:
            model,fit_stats=fit_graph(data,graph,train_config,kind)
            models[key]=model
            if key not in candidates:
                candidate_path=folder/f'candidate-{key}.json'
                if candidate_path.exists():
                    candidates[key]=read_json(candidate_path)
                else:
                    candidates[key]={'graph':graph.json(),'search':score(model,data.get('search'),config),
                                     'fits':fit_stats,'edit':edit,'ordinal':len(candidates)+1}
                    atomic_json(candidate_path,candidates[key])
        return candidates[key]['search']['total']

    if not candidates:
        for graph in starts[:config['candidate_budget']]:
            evaluate(graph)
        initial_key=incumbent_key=min(candidates,key=lambda k:(candidates[k]['search']['total'],k))
    else:
        evaluate(DAG.from_json(candidates[incumbent_key]['graph']))

    if policy!='fixed':
        for round_index in range(round_start,config['rounds']):
            if len(candidates)>=config['candidate_budget'] or stalls>=2:
                break
            incumbent=models[incumbent_key]
            options=[(edit,g) for edit,g in incumbent.graph.valid_edits(root_nodes=root_nodes) if g.key not in candidates]
            if not options:
                break
            proposal_rejections=[]
            if policy in ('diagnostic','marginal'):
                details=disturbances(incumbent,data.get('search'),config['seed']+round_index,
                                     config['diagnostic_cap'],config['permutations'],policy=='marginal')
                diagnostic_records[str(round_index)]=details
                priorities={row['node']:row['priority'] for row in details}
                rng.shuffle(options)
                options.sort(key=lambda item:-sum(priorities[j] for j in item[0]['affected']))
            elif policy=='random':
                rng.shuffle(options)
            elif policy=='llm':
                if llm_callback is None:
                    raise ValueError('actual LLM proposals are required; no fabricated fallback')
                # Release flow GPU storage for the separate LLM process/stage.
                device=data.get('fit')[0].x.device
                for m in models.values():
                    m.cpu()
                torch.cuda.empty_cache()
                proposed=llm_callback(incumbent.graph,edits,candidates,round_index)
                for m in models.values():
                    m.to(device)
                legal={g.key:(e,g) for e,g in options}
                proposal_rejections=[{'graph':g.json(),'reason':'previously evaluated' if g.key in candidates else 'not a legal single edit'}
                                     for g in proposed if g.key not in legal]
                options=list({g.key:legal[g.key] for g in proposed if g.key in legal}.values())
            else:
                raise ValueError('unknown repair policy')
            selected=[]
            for _ in range(min(config['per_round'],config['candidate_budget']-len(candidates),len(options))):
                # Every fourth proposal is globally random, accumulated across rounds.
                take=int(rng.integers(len(options))) if policy in ('diagnostic','marginal') and slots%4==3 else 0
                selected.append(options.pop(take))
                slots+=1
            previous=incumbent_key
            evaluated=[]
            for edit,graph in selected:
                evaluate(graph,edit)
                evaluated.append(graph.key)
            if evaluated:
                best=min(evaluated,key=lambda k:(candidates[k]['search']['total'],k))
                if candidates[best]['search']['total'] <= candidates[incumbent_key]['search']['total']-config['improvement']:
                    incumbent_key=best
            accepted=incumbent_key!=previous
            edits.append({'round':round_index,'before':previous,'after':incumbent_key,
                          'evaluated':evaluated,'accepted':accepted,
                          'proposal_rejections':proposal_rejections,
                          'score_change':candidates[incumbent_key]['search']['total']-candidates[previous]['search']['total']})
            stalls=0 if accepted else stalls+1
            atomic_json(folder/'diagnostics.json',diagnostic_records)
            atomic_json(state_path,{'identity_hash':digest(identity),'candidates':candidates,'edits':edits,
                        'initial':initial_key,'incumbent':incumbent_key,'next_round':round_index+1,
                        'stalls':stalls,'slots':slots,'rng_state':rng.bit_generator.state,
                        'elapsed_seconds':carried_seconds+time.monotonic()-start_time})

    # Commit the two audit candidates before opening audit observations.
    audit_candidates={'initial':initial_key,'selected':incumbent_key,'identity_hash':digest(identity)}
    frozen_audit=folder/'audit_candidates.json'
    if frozen_audit.exists() and read_json(frozen_audit)!=audit_candidates:
        raise RuntimeError('audit candidates cannot be changed after freeze')
    atomic_json(frozen_audit,audit_candidates)
    evaluate(DAG.from_json(candidates[initial_key]['graph']))
    audit_path=folder/'audit.json'
    if audit_path.exists():
        audit=read_json(audit_path)
    else:
        a=score(models[initial_key],data.get('audit'),config,'audit')
        b=a if initial_key==incumbent_key else score(models[incumbent_key],data.get('audit'),config,'audit')
        audit={'initial':a,'selected':b,'pass':audit_pass(a,b,config)}
        atomic_json(audit_path,audit)
    selected_key=incumbent_key if audit['pass'] else initial_key
    unique_fits={s['key']:s for c in candidates.values() for s in c['fits']}
    llm_records=[row for p in sorted(folder.glob('llm-edit-*.json')) for row in read_json(p)['records']]
    flow_peak=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
    llm_peak=max((row['stats']['peak_vram_bytes'] for row in llm_records),default=0)
    record={'run_id':run_id,'identity':identity,'identity_hash':digest(identity),'initial':initial_key,
            'before_audit':incumbent_key,'selected':selected_key,'audit':audit,'candidates':candidates,
            'edits':edits,'candidate_count':len(candidates),'wall_seconds':carried_seconds+time.monotonic()-start_time,
            'unique_parent_sets':len({s['key'] for c in candidates.values() for s in c['fits']}),
            'new_parent_sets':sum(not s['cache_hit'] for c in candidates.values() for s in c['fits']),
            'optimizer_updates':sum(s['actual_updates'] for c in candidates.values() for s in c['fits']),
            'canonical_optimizer_updates':sum(s.get('updates',0) for s in unique_fits.values()),
            'canonical_fit_seconds':sum(s.get('fit_seconds',0.) for s in unique_fits.values()),
            'cost_interpretation':'wall time reflects shared cache execution order; canonical totals count each required parent set once',
            'flow_peak_vram_bytes':flow_peak,'llm_edit_peak_vram_bytes':llm_peak,
            'peak_vram_bytes':max(flow_peak,llm_peak),'llm_edit_attempts':len(llm_records),
            'llm_edit_invalid_attempts':sum(not row['valid'] for row in llm_records),
            'llm_edit_rejected_graphs':sum(len(e.get('proposal_rejections',[])) for e in edits)}
    atomic_json(path,record)
    return record
