"""Paired text/graph/SCM comparisons; test labels never enter generation prompts."""
import copy, itertools, json, math, time
from pathlib import Path
import networkx as nx
from .generation import Generator
from .structural_programs import SCM, InvalidModel
from .budget import atomic_json
from .attribution import select_paths, coalitions


def leaf_keys(expr,key):
    if not isinstance(expr,dict): raise InvalidModel('Every expression and argument must be an object leaf {ref:id}, {noise:id}, {const:value}, or {op,args}; raw strings/numbers are invalid: '+repr(expr)[:180])
    if key in expr:return {expr[key]}
    return set().union(*(leaf_keys(a,key) for a in expr.get('args',[]))) if expr.get('args') else set()


def normalize_benchmark(output,case):
    nodes=[];background={}
    for row in output['nodes']:
        row=copy.deepcopy(row);row.setdefault('label',row['id']);row['type']='bool';row['time']=None;row['reference']=0
        row['noise']=sorted(leaf_keys(row['expr'],'noise'))
        for key in row['noise']:background[key]={'type':'bool','observed':row['observed']}
        row.setdefault('parents',[]);row.setdefault('unknown',False);row.setdefault('segments',[])
        nodes.append(row)
    return {'id':case['id'],'nodes':nodes,'background':background,'outcome':output['outcome'],
            'reference_policy':'inactive binary state=0 as declared controlled-benchmark contrast'}


def model_prompt(root,case):
    contract=(Path(root)/'prompts/ast_contract.txt').read_text()
    return contract+'\nThe specified outcome is '+case['queries'][0]['target']+'. Reconstruct every station and all mechanisms from this record. Return {"outcome":"last station ID","nodes":[{"id":"V00","parents":[],"expr":{"noise":"UV00"},"observed":0,"unknown":false,"segments":["seg_V00"]},... ]}. Use IDs from the text. For a root, retain its explicitly named external setting as noise. Set unknown=true only when the mechanism is missing and provide one plausible equation compatible with factual observations. Do not supply gold answers. Keep JSON compact. Record:\n'+case['narrative']


def query_packet(case):return [{'id':q['id'],'question':q['text']} for q in case['queries']]


def execute_answers(model,case, cautious=False):
    scm=SCM(model);answers=[];unknown={n['id'] for n in model['nodes'] if n.get('unknown')}
    compatible=[scm]
    if cautious and len(unknown)==1:
        index=next(i for i,n in enumerate(model['nodes']) if n['id'] in unknown)
        node=model['nodes'][index]
        if len(node['parents'])==2 and all(scm.nodes[p]['type']=='bool' for p in node['parents']):
            a,b=[{'ref':p} for p in node['parents']];compatible=[]
            for table in itertools.product((0,1),repeat=4):
                expression={'op':'if','args':[a,{'op':'if','args':[b,{'const':table[3]},{'const':table[2]}]},{'op':'if','args':[b,{'const':table[1]},{'const':table[0]}]}]}
                candidate=copy.deepcopy(model);candidate['nodes'][index]['expr']=expression
                try:compatible.append(SCM(candidate))
                except InvalidModel:pass
        else:compatible=[]
    for q in case['queries']:
        k=q['kind'];out=q['target'];assumed=False
        if k=='ancestry': vals=[int(nx.has_path(scm.graph,q['source'],out))]
        elif k=='evidence':vals=[int(out not in unknown)]
        else:
            for u in unknown:
                affected=u not in q['do'] and any(nx.has_path(scm.graph,x,u) for x in q['do'])
                assumed |= affected and (u==out or nx.has_path(scm.graph,u,out))
            vals=[int(scm.solve(interventions=q['do'])[out])]
            if cautious and compatible:
                vals=sorted({int(s.solve(interventions=q['do'])[out]) for s in compatible});assumed=len(vals)>1
        abstain=bool(cautious and assumed and not compatible)
        answers.append({'id':q['id'],'values':None if abstain else vals,'abstain':abstain,'uses_assumption':assumed})
    return answers


def run_case(root,case,seed=2027):
    root=Path(root);gen=Generator(root);destination=gen.run/'benchmark'/(case['id']+'_s%d.json'%seed)
    if destination.exists():return json.loads(destination.read_text())
    record={'id':case['id'],'scm_id':case['scm_id'],'split':case['split'],'condition':case['condition'],'size':case['size'],'variant':case['variant'],'seed':seed,'methods':{},'attempts':[],'started_at':time.time()}
    # Baselines share the full evidence and the same answer output budget.
    common='Answer from this record only. Missing rules can make a query underdetermined: abstain or return all supported binary values. Return {"answers":[{"id":"q0","values":[0],"abstain":false},...]}.\nRECORD:\n'+case['narrative']+'\nQUESTIONS:\n'+json.dumps(query_packet(case))
    try:record['methods']['B0']=gen.call('benchmark_B0',common,2048,seed)
    except Exception as e:record['methods']['B0']={'error':str(e)}
    prompt=model_prompt(root,case);model=None;initial=None
    for attempt in range(3):
        try:
            response=gen.call('benchmark_synthesis' if attempt==0 else 'benchmark_repair',prompt,4096,seed+attempt)
            proposed=normalize_benchmark(response,case)
            expected={s['node_id'] for s in case['segments']}
            if {n['id'] for n in proposed['nodes']}!=expected:raise InvalidModel('Missing/extra station IDs relative to record')
            scm=SCM(proposed)
            record['attempts'].append({'attempt':attempt,'valid':True,'model':proposed,'diagnostics':scm.diagnostics})
            model=proposed;initial=model;break
        except Exception as e:
            failed=locals().get('response')
            record['attempts'].append({'attempt':attempt,'valid':False,'error':str(e),'response':failed})
            prompt=model_prompt(root,case)+'\nYour prior candidate failed validation: '+str(e)+'\nPrevious JSON: '+json.dumps(failed)+'\nRegenerate the full compact candidate; correct only using the supplied record.'
            # Keep repair input within total context. If prior output is long omit it, retain diagnostic.
            if len(prompt)>17000:prompt=model_prompt(root,case)+'\nValidation diagnostic to correct: '+str(e)
    graph=[{'id':n['id'],'parents':n['parents']} for n in model['nodes']] if model else []
    try: record['methods']['B1']=gen.call('benchmark_B1',common+'\nExtracted graph (possibly imperfect; no equations):\n'+json.dumps(graph),2048,seed)
    except Exception as e:record['methods']['B1']={'error':str(e)}
    if model:
        record['methods']['B2']={'answers':execute_answers(model,case),'model':model}
        record['methods']['P']={'answers':execute_answers(model,case,True),'model':model,'retention':'same first admissible candidate; all observationally compatible active binary truth tables for a single missing two-parent rule, otherwise conservative abstention'}
        paths=select_paths(SCM(model));record['paths']=paths
        if paths['paths']:record['attribution']=coalitions(SCM(model),paths['paths'])
    else:
        record['methods']['B2']=record['methods']['P']={'error':'No admissible SCM after two repairs'}
    record['elapsed_seconds']=time.time()-record['started_at']
    atomic_json(destination,record)
    atomic_json(gen.run/'inference_usage.json',gen.summary())
    return record


def pilot(root):
    root=Path(root);gen=Generator(root);cases=[json.loads(x) for x in (root/'benchmark/cases.jsonl').read_text().splitlines() if json.loads(x)['split']=='development']
    trials=[]
    for i in range(20):
        case=cases[i%len(cases)]
        if i<8: prompt=model_prompt(root,case);role='pilot_synthesis';limit=4096
        elif i<14:
            prompt='From this record answer the questions as JSON with answers:[{id,values:[0 or 1],abstain:boolean}].\n'+case['narrative']+'\n'+json.dumps(query_packet(case));role='pilot_answers';limit=2048
        elif i<17:
            prompt='Assess whether each paragraph explicitly states a mechanism. Return JSON with assessments:[{segment_id,explicit:boolean,score:0 to 1,reason}]. Score evidence support, not causal probability.\n'+case['narrative'];role='pilot_evidence';limit=2048
        else:
            prompt='Explain in JSON {explanations:[{query_id,text}]} how fixed mechanisms should be evaluated for these questions. Never invent absent rules.\n'+case['narrative']+'\n'+json.dumps(query_packet(case));role='pilot_explanation';limit=2048
        start=time.time();row={'index':i,'role':role,'case':case['id']}
        try:
            out=gen.call(role,prompt,limit,2027+i);row['json_valid']=True
            if role=='pilot_synthesis':
                try: SCM(normalize_benchmark(out,case));row['executable']=True
                except Exception as e:row['executable']=False;row['validation_error']=str(e)
        except Exception as e:row.update(json_valid=False,error=str(e))
        row['seconds']=time.time()-start;trials.append(row);atomic_json(gen.run/'pilot.json',trials)
        print(json.dumps(row),flush=True)
    usage=gen.summary();atomic_json(gen.run/'inference_usage.json',usage)
    times=sorted(t['seconds'] for t in trials)
    report={'requests':20,'json_valid':sum(x['json_valid'] for x in trials),'p50_seconds':times[10],'p90_seconds':times[18],
            'synthesis_executable':sum(t.get('executable',False) for t in trials),'synthesis_trials':8,
            'output_tokens':sum(u['output_tokens'] or 0 for u in usage),'request_seconds':sum(u['seconds'] or 0 for u in usage),
            'prefill_timing':'streamed time-to-first-content recorded per request; includes scheduling/network and is not pure prefill',
            'decision':'retain Qwen3-14B-AWQ if validity and conservative projection fit; no second model required'}
    atomic_json(gen.run/'pilot_summary.json',report);return report


def run_benchmark(root,split=None,seed=2027):
    root=Path(root);cases=[json.loads(x) for x in (root/'benchmark/cases.jsonl').read_text().splitlines()]
    for case in cases:
        if split and case['split']!=split:continue
        print('BEGIN',case['id'],case['split'],flush=True)
        record=run_case(root,case,seed)
        print('DONE',case['id'],round(record['elapsed_seconds'],1),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['pilot','benchmark']);p.add_argument('--root',default='.');p.add_argument('--split');a=p.parse_args()
    print(pilot(a.root) if a.action=='pilot' else run_benchmark(a.root,a.split))
