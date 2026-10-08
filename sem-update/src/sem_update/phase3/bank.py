"""Immutable, calibration-blind candidate banks using the historical repair policy."""
import time
import numpy as np
import torch
from sem_update.flows import GenerativeSCM
from .flows import fit_graph
from sem_update.graphs import DAG
from .diagnostics import disturbances
from .graphs import edit_descriptors,apply
from sem_update.search import DEFAULT_SEARCH
from .runtime import root,atomic_json,read_json,digest,file_hash
from .objectives import score


def cost(candidates):
    fits={s['key']:s for c in candidates.values() for s in c['fits']}
    return {'fitting_updates':sum(s['updates'] for s in fits.values()),
        'fit_seconds':sum(s['fit_seconds'] for s in fits.values()),
        'input_weighted_updates':sum(s['updates']*(len(s['parents'])+1) for s in fits.values()),
        'parent_sets':len(fits)}

def build(data,starts,run_id,config,policy='diagnostic',root_nodes=(),llm_callback=None):
    if any(r in data.allowed for r in ('calibration','audit','final')):
        raise ValueError('Bank construction requires a restricted fit/early/search view')
    cfg={**DEFAULT_SEARCH,**config['search']}
    identity={'data':data.key,'starts':[g.json() for g in starts],'policy':policy,
              'train':config['train'],'search':cfg,'roots':list(root_nodes),'bank_version':4,
              'search_data_hash':data.manifest.get('partition_hashes',{}).get('search',data.manifest['arrays_sha256'])}
    folder=root()/'runs'/run_id;folder.mkdir(parents=True,exist_ok=True)
    path=folder/'bank.json';state_path=folder/'bank_state.json'
    if path.exists():
        value=read_json(path)
        if value['identity']!=identity:raise ValueError('Incompatible immutable bank')
        return value
    started=time.monotonic();models={};rng=np.random.default_rng(cfg['seed'])
    state={'identity':identity,'candidates':{},'diagnostics':{},'edits':[],
           'next_round':0,'stalls':0,'slots':0,'elapsed_seconds':0.,'overhead_seconds':0.}
    if state_path.exists():
        state=read_json(state_path)
        if state['identity']!=identity:raise ValueError('Incompatible bank resume')
        rng.bit_generator.state=state['rng_state']
    candidates=state['candidates'];carried=state['elapsed_seconds']
    def save():
        state['rng_state']=rng.bit_generator.state
        state['elapsed_seconds']=carried+time.monotonic()-started
        atomic_json(state_path,state)
    def evaluate(graph,edit=None):
        if graph.key not in models:
            model,fits=fit_graph(data,graph,config['train']);models[graph.key]=model
            if graph.key not in candidates:
                cp=folder/('candidate-'+graph.key+'.json')
                if cp.exists():candidates[graph.key]=read_json(cp)
                else:
                    begin=time.monotonic();scored=score(model,data.get('search'),cfg)
                    seconds=time.monotonic()-begin
                    candidates[graph.key]={'graph':graph.json(),'fits':fits,'search':scored,
                        'edit':edit,'ordinal':len(candidates)+1,'score_seconds':seconds,
                        'peak_vram_bytes':torch.cuda.max_memory_allocated()}
                    candidates[graph.key]['prefix_cost']=cost(candidates)
                    candidates[graph.key]['prefix_cost']['gpu_job_seconds']=(
                        candidates[graph.key]['prefix_cost']['fit_seconds']+
                        sum(c['score_seconds'] for c in candidates.values())+state['overhead_seconds'])
                    atomic_json(cp,candidates[graph.key])
        return models[graph.key]
    if 'initial' not in state:
        for graph in starts[:cfg['candidate_budget']]:evaluate(graph)
        state['initial']=state['incumbent']=min(candidates,key=lambda k:(candidates[k]['search']['total'],k))
        save()
    if policy!='fixed':
        for ri in range(state['next_round'],cfg['rounds']):
            if len(candidates)>=cfg['candidate_budget']:break
            if cost(candidates)['fitting_updates']>=cfg['update_limit'] or state['elapsed_seconds']>=cfg['seconds']:
                state['resource_capped']=True;break
            incumbent=evaluate(DAG.from_json(candidates[state['incumbent']]['graph']))
            begin=time.monotonic()
            descriptors=edit_descriptors(incumbent.graph,cfg['max_indegree'])
            options=descriptors
            if not options:break
            proposal_record=None
            if policy=='diagnostic':
                details=disturbances(incumbent,data.get('search'),cfg['seed']+ri,cfg['diagnostic_cap'],cfg['permutations'],cfg['pair_cap'],cfg['environment_cap'])
                state['diagnostics'][str(ri)]=details
                priorities={r['node']:r['priority'] for r in details}
                rng.shuffle(options);options.sort(key=lambda item:-sum(priorities[j] for j in item[3]))
            elif policy=='random':rng.shuffle(options)
            else:raise ValueError('Unknown bank policy')
            round_overhead=time.monotonic()-begin
            state['overhead_seconds']+=round_overhead
            chosen=[]
            limit=min(cfg['per_round'],cfg['candidate_budget']-len(candidates))
            if len(candidates)<cfg['fixed_candidates']:limit=min(limit,cfg['fixed_candidates']-len(candidates))
            while options and len(chosen)<limit:
                index=int(rng.integers(len(options))) if policy=='diagnostic' and state['slots']%4==3 else 0
                move=options.pop(index);graph=apply(incumbent.graph,move)
                if graph.key in candidates:continue
                edit=dict(zip(('operation','source','target','affected'),move))
                chosen.append((edit,graph));state['slots']+=1
            previous=state['incumbent'];evaluated=[]
            for edit,graph in chosen:evaluate(graph,edit);evaluated.append(graph.key)
            if evaluated:
                best=min(evaluated,key=lambda k:(candidates[k]['search']['total'],k))
                if candidates[best]['search']['total']<=candidates[previous]['search']['total']-cfg['improvement']:
                    state['incumbent']=best
            accepted=state['incumbent']!=previous
            state['edits'].append({'round':ri,'before':previous,'after':state['incumbent'],
                'overhead_seconds':round_overhead,
                'evaluated':evaluated,'accepted':accepted,'proposal_record':proposal_record,
                'score_rejections':len(evaluated)-int(accepted)})
            state['stalls']=0 if accepted else state['stalls']+1;state['next_round']=ri+1
            if 'fixed_count' not in state and (state['stalls']>=2 or len(candidates)>=cfg['fixed_candidates']):state['fixed_count']=len(candidates)
            save()
    save()
    value={**state,'fixed_count':state.get('fixed_count',len(candidates)),'cost':cost(candidates),'flow_peak_vram_bytes':torch.cuda.max_memory_allocated(),
           'peak_vram_bytes':max(torch.cuda.max_memory_allocated(),
               max((e['proposal_record']['peak_vram_bytes'] for e in state['edits'] if e['proposal_record']),default=0)),
           'construction_partitions':list(data.allowed),'immutable':True,
           'cost_definition':'unique canonical parent-set fits, plus measured candidate scoring and policy overhead'}
    value['logical_seconds']=value['cost']['fit_seconds']+sum(c['score_seconds'] for c in candidates.values())+value['overhead_seconds']
    value['bank_hash']=digest(value);atomic_json(path,value)
    return value

def load_models(bank,data,config):
    expected=bank['bank_hash'];payload={k:v for k,v in bank.items() if k!='bank_hash'}
    if digest(payload)!=expected:raise ValueError('Candidate bank content changed')
    return {k:fit_graph(data,DAG.from_json(c['graph']),config['train'],False)[0] for k,c in bank['candidates'].items()}

def subbank(bank,keys):
    value={k:v for k,v in bank.items() if k!='bank_hash'}
    value['candidates']={k:v for k,v in bank['candidates'].items() if k in keys}
    value['cost']=cost(value['candidates'])
    value['peak_vram_bytes']=max(c['peak_vram_bytes'] for c in value['candidates'].values())
    last=max(c['ordinal'] for c in value['candidates'].values())
    value['edits']=[e for e in bank['edits'] if all(k in keys for k in e['evaluated'])]
    value['incumbent']=value['edits'][-1]['after'] if value['edits'] else value['initial']
    value['next_round']=len(value['edits'])
    value['overhead_seconds']=sum(e['overhead_seconds'] for e in value['edits'])
    value['logical_seconds']=value['cost']['fit_seconds']+sum(c['score_seconds'] for c in value['candidates'].values())+value['overhead_seconds']
    value['bank_hash']=digest(value)
    return value

def prefix_keys(bank,axis,budget):
    rows=sorted(bank['candidates'].items(),key=lambda item:item[1]['ordinal'])
    # Only a prefix of completed fits; no cherry picking cheaper later graphs.
    result=[]
    for key,c in rows:
        if c['prefix_cost'][axis]>budget:break
        result.append(key)
    return result if bank['initial'] in result else []
