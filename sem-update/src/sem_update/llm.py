"""Frozen, actual local LLM generations. No ground truth or test input interface."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
import torch
from .graphs import DAG
from .runtime import PROJECT,artifact_root,configure_caches,read_json,atomic_json,digest,Ledger

SEMANTIC_ROLES=[
    ('Source brightness control A','Dimensionless electronically assigned light-source control.'),
    ('Source brightness control B','Dimensionless independently assigned light-source control.'),
    ('Optical filter setting','Independently assigned setting of a filter in an optical assembly.'),
    ('Light sensor A','Noisy intensity measurement at one position in the assembly.'),
    ('Light sensor B','Noisy intensity measurement at a second position in the assembly.')]
REAL_ROLES=[('Red source setting','Assigned brightness setting for red light.'),
            ('Green source setting','Assigned brightness setting for green light.'),
            ('Blue source setting','Assigned brightness setting for blue light.'),
            ('Source current readout','Digitized electrical current measurement.'),
            ('Polarizer motor setting','Assigned angular position of a rotating optical component.'),
            ('Position readout','Digitized voltage from a rotary position sensor.')]

def metadata(kind,variant,seed):
    roles=SEMANTIC_ROLES if kind=='semantic' else REAL_ROLES
    if variant=='shuffled':
        rng=np.random.default_rng(seed+102)
        roles=[roles[i] for i in rng.permutation(len(roles))]
    return [{'id':f'V{i}','name':name if variant!='anonymous' else f'Variable {i}',
             'description':description if variant!='anonymous' else 'Continuous observed variable.'}
            for i,(name,description) in enumerate(roles)]

def validate_graph(value,nodes,root_nodes=()):
    ids=[row['id'] for row in nodes]
    if value.get('nodes') != ids:
        raise ValueError('nodes must match the exact ordered ID list')
    edges=value.get('edges')
    if not isinstance(edges,list):
        raise ValueError('edges must be a list')
    mapped=[]
    for edge in edges:
        if not isinstance(edge,dict) or set(edge)!={'source','target','rationale'}:
            raise ValueError('each edge requires source,target,rationale')
        if not isinstance(edge['rationale'],str) or len(edge['rationale'])>600:
            raise ValueError('invalid edge rationale')
        mapped.append((ids.index(edge['source']),ids.index(edge['target'])))
    graph=DAG(len(nodes),tuple(mapped))
    if any(len(graph.parents(j))>3 for j in range(graph.d)):
        raise ValueError('maximum indegree exceeded')
    if any(graph.parents(j) for j in root_nodes):
        raise ValueError('verified independently assigned root has incoming edge')
    return graph

def make_prompt(nodes,root_nodes=(),feedback=None):
    # Whitelist metadata fields, even if a caller supplied a richer object.
    public=[{k:row[k] for k in ('id','name','description')} for row in nodes]
    prompt=(PROJECT/'prompts'/('graph_edit.txt' if feedback else 'graph_proposal.txt')).read_text()
    prompt+='\nVariables: '+json.dumps(public,sort_keys=True)
    prompt+='\nVerified independently assigned roots: '+json.dumps([nodes[j]['id'] for j in root_nodes])
    if feedback:
        prompt+='\nSearch feedback (lower scores are better): '+json.dumps(feedback,sort_keys=True)
    return prompt

class LocalProposer:
    def __init__(self):
        started=time.monotonic()
        configure_caches()
        from transformers import AutoTokenizer,AutoModelForCausalLM
        if not torch.cuda.is_available():
            raise RuntimeError('actual CUDA LLM inference required')
        self.revision=read_json(PROJECT/'results/curated/llm_revision.json')
        model_name=self.revision['model']
        revision=self.revision['revision']
        self.tokenizer=AutoTokenizer.from_pretrained(model_name,revision=revision,local_files_only=True)
        self.model=AutoModelForCausalLM.from_pretrained(model_name,revision=revision,local_files_only=True,
                         torch_dtype=torch.bfloat16,device_map={'':'cuda:0'},attn_implementation='sdpa').eval()
        self.model.requires_grad_(False)
        if any(p.device.type!='cuda' for p in self.model.parameters()):
            raise RuntimeError('LLM CPU offload is not permitted for this run')
        self.load_seconds=time.monotonic()-started

    def query(self,prompt,seed):
        from transformers import StoppingCriteria,StoppingCriteriaList
        from .runtime import check_budget
        class RuntimeCap(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):
                check_budget()
                return False
        torch.manual_seed(seed)
        text=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,
                                                add_generation_prompt=True,enable_thinking=False)
        tokens=self.tokenizer(text,return_tensors='pt').to('cuda')
        if tokens.input_ids.shape[1]>6000:
            raise ValueError('frozen short-context limit exceeded')
        start=time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            output=self.model.generate(**tokens,max_new_tokens=2048,do_sample=True,temperature=.7,top_p=.8,top_k=20,
                                       stopping_criteria=StoppingCriteriaList([RuntimeCap()]))
        torch.cuda.synchronize()
        raw=self.tokenizer.decode(output[0,tokens.input_ids.shape[1]:],skip_special_tokens=True)
        return raw,{'seed':seed,'seconds':time.monotonic()-start,'input_tokens':tokens.input_ids.shape[1],
                    'output_tokens':output.shape[1]-tokens.input_ids.shape[1],
                    'peak_vram_bytes':torch.cuda.max_memory_allocated(),'device':'cuda:0',**self.revision}

def generate_request(request_path):
    request=read_json(request_path)
    output=Path(request['output'])
    scientific_request={k:v for k,v in request.items() if k!='output'}
    scientific_request['model_revision']=read_json(PROJECT/'results/curated/llm_revision.json')
    scientific_request['rendered_prompt']=make_prompt(request['nodes'],request.get('roots',()),request.get('feedback'))
    request_hash=digest(scientific_request)
    if output.exists():
        old=read_json(output)
        if old['request_hash']!=request_hash:
            raise ValueError('incompatible LLM request resume')
        return old
    ledger=Ledger()
    job='llm-'+request_hash[:20]
    if not ledger.claim(job,scientific_request,expected_seconds=600):
        raise RuntimeError('completed LLM ledger entry lacks output')
    records=[]
    try:
        with ledger.device_interval(job):
            started=time.monotonic()
            proposer=LocalProposer()
            for p in range(request.get('count',2)):
                prompt=make_prompt(request['nodes'],request.get('roots',()),request.get('feedback'))
                for attempt in range(2):
                    raw,stats=proposer.query(prompt,request['seed']+p*10+attempt)
                    raw_path=artifact_root()/'runs'/job/f'proposal-{p}-attempt-{attempt}.txt'
                    raw_path.parent.mkdir(exist_ok=True,parents=True)
                    raw_path.write_text(raw)
                    raw_path.with_suffix('.prompt.txt').write_text(prompt)
                    record={'proposal':p,'attempt':attempt,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                            'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'stats':stats}
                    try:
                        value=json.loads(raw[raw.index('{'):raw.rindex('}')+1])
                        if request.get('feedback'):
                            # One query returns at most three single-edit candidate graphs.
                            values=value['graphs'][:3]
                        else:
                            values=[value]
                        graphs=[validate_graph(v,request['nodes'],request.get('roots',())) for v in values]
                        record.update(valid=True,graphs=[g.json() for g in graphs],proposals=values)
                    except (ValueError,KeyError,TypeError) as error:
                        record.update(valid=False,error=str(error))
                    records.append(record)
                    if record['valid']:
                        break
                    prompt+='\nYour preceding response failed validation: '+record['error']+'. Return valid JSON only.'
            result={'request_hash':request_hash,'request_identity_version':2,'records':records,'metadata':request['nodes'],
                    'revision':proposer.revision,'actual_local_generation':True,
                    'model_load_seconds':proposer.load_seconds,'stage_seconds':time.monotonic()-started,
                    'query_attempts':len(records),'invalid_attempts':sum(not r['valid'] for r in records)}
            atomic_json(output,result)
        ledger.finish(job)
        return result
    except Exception as error:
        ledger.finish(job,str(error))
        raise

def edit_callback(nodes,root_nodes,run_id):
    def callback(graph,edits,candidates,round_index):
        folder=artifact_root()/'runs'/run_id
        output=folder/f'llm-edit-{round_index}.json'
        request=folder/f'llm-request-{round_index}.json'
        feedback={'incumbent':graph.json(),'history':edits,
                  'evaluated':[{'graph':c['graph'],'score':c['search']} for c in sorted(candidates.values(),key=lambda c:c['ordinal'])]}
        atomic_json(request,{'nodes':nodes,'roots':list(root_nodes),'seed':87021+round_index,
                    'feedback':feedback,'count':1,'output':str(output)})
        with open(folder/f'llm-stage-{round_index}.log','w') as log:
            subprocess.run([sys.executable,'-m','sem_update.llm',str(request)],check=True,stdout=log,stderr=subprocess.STDOUT)
        result=read_json(output)
        return [DAG.from_json(g) for row in result['records'] if row['valid'] for g in row['graphs']]
    return callback

if __name__=='__main__':
    configure_caches()
    parser=argparse.ArgumentParser()
    parser.add_argument('request')
    args=parser.parse_args()
    generate_request(args.request)
