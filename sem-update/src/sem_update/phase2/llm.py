"""Actual frozen local generations with a validated legal-edit-ID contract."""
import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path
from sem_update.graphs import DAG
from sem_update.llm import LocalProposer,validate_graph,make_prompt,metadata
from .runtime import root,PHASE,PROJECT,setup,require_cuda,job,atomic_json,read_json,digest

CATEGORIES=('malformed_output','invalid_nodes','cycles','duplicate_graphs',
            'valid_no_change','valid_new_edits','score_rejections','accepted_changes')

def parse_menu(raw,menu):
    counts=dict.fromkeys(CATEGORIES,0);graphs=[]
    try:
        value=json.loads(raw[raw.index('{'):raw.rindex('}')+1]);ids=value['edit_ids']
        if not isinstance(ids,list) or len(ids)>3 or any(not isinstance(v,str) for v in ids):raise ValueError('edit_ids must contain at most three strings')
    except (ValueError,KeyError,TypeError):
        counts['malformed_output']+=1;return graphs,counts,False
    lookup={r['id']:r for r in menu};seen=set()
    if not ids:counts['valid_no_change']+=1
    for key in ids:
        if key not in lookup:counts['invalid_nodes']+=1;continue
        graph=DAG.from_json(lookup[key]['graph'])
        if graph.key in seen:counts['duplicate_graphs']+=1;continue
        seen.add(graph.key);graphs.append(graph);counts['valid_new_edits']+=1
    return graphs,counts,not counts['invalid_nodes']

def render(request):
    nodes=[{k:r[k] for k in ('id','name','description')} for r in request['nodes']]
    if request['kind']=='initial':return make_prompt(nodes,request['roots'])
    text=(PHASE/'prompts/edit_menu.txt').read_text()
    public={'variables':nodes,'independently_assigned_roots':[nodes[j]['id'] for j in request['roots']],
            'current_edges':[[f'V{a}',f'V{b}'] for a,b in request['current']['edges']],
            'search_feedback':request['feedback'],
            'legal_edits':[{k:r[k] for k in ('id','operation','source','target')} for r in request['menu']]}
    return text+'\n'+json.dumps(public,sort_keys=True)

def generate(request_path):
    setup();require_cuda();request=read_json(request_path);output=Path(request['output']);prompt=render(request)
    identity={k:v for k,v in request.items() if k!='output'}
    identity['prompt']=prompt;identity['revision']=read_json(PROJECT/'results/curated/llm_revision.json')
    key=digest(identity)
    if output.exists():
        result=read_json(output)
        if result['identity_hash']!=key:raise ValueError('Incompatible LLM resume')
        return result
    with job('llm-'+key[:24],identity,120) as active:
        if not active:raise RuntimeError('Completed generation has no output')
        start=time.monotonic();model=LocalProposer();records=[]
        for p in range(2 if request['kind']=='initial' else 1):
            text=prompt
            for attempt in range(2):
                raw,stats=model.query(text,request['seed']+p*10+attempt)
                folder=root()/'runs'/('llm-'+key[:24]);folder.mkdir(parents=True,exist_ok=True)
                (folder/f'{p}-{attempt}.txt').write_text(raw)
                (folder/f'{p}-{attempt}.prompt.txt').write_text(text)
                counts=dict.fromkeys(CATEGORIES,0);graphs=[];valid=False;error=None
                if request['kind']=='edit':graphs,counts,valid=parse_menu(raw,request['menu'])
                else:
                    try:
                        value=json.loads(raw[raw.index('{'):raw.rindex('}')+1])
                        graphs=[validate_graph(value,request['nodes'],request['roots'])];valid=True
                    except (ValueError,KeyError,TypeError) as exc:
                        error=str(exc);counts['cycles' if 'cyclic' in error else 'invalid_nodes' if 'not in list' in error or 'nodes' in error else 'malformed_output']+=1
                records.append({'proposal':p,'attempt':attempt,'valid':valid,'counts':counts,'error':error,
                    'graphs':[g.json() for g in graphs],'stats':stats,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                    'prompt_sha256':hashlib.sha256(text.encode()).hexdigest()})
                if valid:break
                text+='\nThe response failed validation. Use the exact JSON contract and supplied IDs.'
        result={'identity_hash':key,'records':records,'actual_local_generation':True,
            'revision':model.revision,'model_load_seconds':model.load_seconds,'stage_seconds':time.monotonic()-start,
            'peak_vram_bytes':max(r['stats']['peak_vram_bytes'] for r in records)}
        atomic_json(output,result);return result

def request_process(request,path):
    atomic_json(path,request)
    with open(path.with_suffix('.log'),'a') as log:
        subprocess.run([sys.executable,'-u','-m','sem_update.phase2.llm',str(path)],
                       stdout=log,stderr=subprocess.STDOUT,check=True,cwd=PROJECT)
    return read_json(request['output'])

def initial(study,variant,seed,roots,data_id):
    folder=root()/'runs/proposals';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(data_id+'-'+variant+'.request.json')
    return request_process({'kind':'initial','nodes':metadata(study,variant,seed),'roots':list(roots),
        'seed':seed+87021,'output':str(path.with_name(path.stem+'.result.json'))},path)

def callback(study,variant,seed,roots,run_id):
    def edit(graph,options,state,round_index):
        menu=[{'id':f'E{i:03d}','operation':e['operation'],'source':f'V{e["source"]}',
               'target':f'V{e["target"]}','graph':g.json()} for i,(e,g) in enumerate(options)]
        folder=root()/'runs'/run_id;path=folder/f'llm-{round_index}.request.json'
        feedback=[{'edges':[[f'V{a}',f'V{b}'] for a,b in c['graph']['edges']],
                   'score':c['search']['total']} for c in sorted(state['candidates'].values(),key=lambda c:c['ordinal'])]
        request={'kind':'edit','nodes':metadata(study,variant,seed),'roots':list(roots),'current':graph.json(),
                 'menu':menu,'feedback':feedback,'seed':seed+97021+round_index,
                 'output':str(folder/f'llm-{round_index}.result.json')}
        result=request_process(request,path)
        # Keep validated proposals independently; a different malformed proposal
        # cannot erase a valid graph from the same generated response.
        proposals={DAG.from_json(g).key:DAG.from_json(g) for r in result['records'] for g in r['graphs']}
        return list(proposals.values()),{'path':str(Path(request['output']).relative_to(root())),
            'counts':{k:sum(r['counts'][k] for r in result['records']) for k in CATEGORIES},
            'stage_seconds':result['stage_seconds'],'peak_vram_bytes':result['peak_vram_bytes']}
    return edit

if __name__=='__main__':generate(sys.argv[1])
