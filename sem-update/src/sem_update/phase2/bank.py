"""Immutable, calibration-blind candidate banks using the historical repair policy."""
import time
import numpy as np
import torch
from sem_update.flows import GenerativeSCM
from sem_update.training import fit_node
from sem_update.graphs import DAG
from sem_update.diagnostics import disturbances
from sem_update.search import DEFAULT_SEARCH
from .runtime import root,atomic_json,read_json,digest,file_hash
from .objectives import score

def fit_graph(data,graph,config,allow_training=True):
    models=[];stats=[]
    for j in range(graph.d):
        start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
        start.record()
        model,s=fit_node(data,j,graph.parents(j),config,allow_training=allow_training)
        end.record();end.synchronize()
        path=root()/'costs'/(s['key']+'.json')
        if not s['cache_hit']:
            # Full canonical elapsed fitting time includes checkpoint/CPU waits;
            # CUDA-event elapsed is separately retained, never called kernel time.
            old=read_json(path) if path.exists() else {}
            atomic_json(path,{'cache_key':s['key'],'fit_seconds':s['fit_seconds'],
                'cuda_stream_elapsed_seconds':old.get('cuda_stream_elapsed_seconds',0.)+start.elapsed_time(end)/1000,
                'updates':s['updates'],'canonical_seed':s['canonical_seed']})
        if not path.exists():raise RuntimeError('Canonical mechanism cost record missing: '+s['key'])
        s={**s,**read_json(path)};models.append(model);stats.append(s)
    return GenerativeSCM(graph,models),stats

def cost(candidates):
    fits={s['key']:s for c in candidates.values() for s in c['fits']}
    return {'fitting_updates':sum(s['updates'] for s in fits.values()),
        'fit_seconds':sum(s['fit_seconds'] for s in fits.values()),
        'cuda_stream_elapsed_seconds':sum(s['cuda_stream_elapsed_seconds'] for s in fits.values()),
        'parent_sets':len(fits)}

def build(data,starts,run_id,config,policy='diagnostic',root_nodes=(),llm_callback=None):
    if any(r in data.allowed for r in ('calibration','audit','final')):
        raise ValueError('Bank construction requires a restricted fit/early/search view')
    cfg={**DEFAULT_SEARCH,**config['search']}
    identity={'data':data.key,'starts':[g.json() for g in starts],'policy':policy,
              'train':config['train'],'search':cfg,'roots':list(root_nodes),'bank_version':2,
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
                        'edit':edit,'ordinal':len(candidates)+1,'score_seconds':seconds}
                    candidates[graph.key]['prefix_cost']=cost(candidates)
                    atomic_json(cp,candidates[graph.key])
        return models[graph.key]
    if 'initial' not in state:
        for graph in starts[:cfg['candidate_budget']]:evaluate(graph)
        state['initial']=state['incumbent']=min(candidates,key=lambda k:(candidates[k]['search']['total'],k))
        save()
    if policy!='fixed':
        for ri in range(state['next_round'],cfg['rounds']):
            if len(candidates)>=cfg['candidate_budget'] or state['stalls']>=2:break
            incumbent=evaluate(DAG.from_json(candidates[state['incumbent']]['graph']))
            options=[(e,g) for e,g in incumbent.graph.valid_edits(root_nodes=root_nodes) if g.key not in candidates]
            if not options:break
            begin=time.monotonic();proposal_record=None
            if policy=='diagnostic':
                details=disturbances(incumbent,data.get('search'),cfg['seed']+ri,cfg['diagnostic_cap'],cfg['permutations'])
                state['diagnostics'][str(ri)]=details
                priorities={r['node']:r['priority'] for r in details}
                rng.shuffle(options);options.sort(key=lambda item:-sum(priorities[j] for j in item[0]['affected']))
            elif policy=='random':rng.shuffle(options)
            elif policy=='llm':
                if llm_callback is None:raise ValueError('An actual local LLM callback is required')
                for m in models.values():m.cpu()
                torch.cuda.empty_cache()
                proposed,proposal_record=llm_callback(incumbent.graph,options,state,ri)
                for m in models.values():m.cuda()
                legal={g.key:(e,g) for e,g in options}
                options=[legal[g.key] for g in proposed if g.key in legal]
            else:raise ValueError('Unknown bank policy')
            state['overhead_seconds']+=time.monotonic()-begin
            chosen=[]
            for _ in range(min(cfg['per_round'],cfg['candidate_budget']-len(candidates),len(options))):
                index=int(rng.integers(len(options))) if policy=='diagnostic' and state['slots']%4==3 else 0
                chosen.append(options.pop(index));state['slots']+=1
            previous=state['incumbent'];evaluated=[]
            for edit,graph in chosen:evaluate(graph,edit);evaluated.append(graph.key)
            if evaluated:
                best=min(evaluated,key=lambda k:(candidates[k]['search']['total'],k))
                if candidates[best]['search']['total']<=candidates[previous]['search']['total']-cfg['improvement']:
                    state['incumbent']=best
            accepted=state['incumbent']!=previous
            state['edits'].append({'round':ri,'before':previous,'after':state['incumbent'],
                'evaluated':evaluated,'accepted':accepted,'proposal_record':proposal_record,
                'score_rejections':len(evaluated)-int(accepted)})
            state['stalls']=0 if accepted else state['stalls']+1;state['next_round']=ri+1;save()
    save()
    value={**state,'cost':cost(candidates),'flow_peak_vram_bytes':torch.cuda.max_memory_allocated(),
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

def prefix_keys(bank,axis,budget):
    rows=sorted(bank['candidates'].items(),key=lambda item:item[1]['ordinal'])
    # Only a prefix of completed fits; no cherry picking cheaper later graphs.
    result=[]
    for key,c in rows:
        if c['prefix_cost'][axis]>budget:break
        result.append(key)
    return result if bank['initial'] in result else []
