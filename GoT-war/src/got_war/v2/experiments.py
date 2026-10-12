"""Paired v2 components with isolated gold and stage-by-stage checkpoints."""
import copy
import json
from pathlib import Path
import time
from ..budget import atomic_json
from ..experiments import normalize_benchmark
from ..structural_programs import SCM, InvalidModel
from .runtime import paths, V2Generator
from .mechanisms import compatible_family, inspect_mechanism, outcome_sets, fingerprint
from .paths import explain_query
from .explanations import generate as explain, reviewer_controls


def synthesis_prompt(root, case):
    contract=(root/'prompts/ast_contract.txt').read_text()
    return (contract+'\nExtract the variables, dependencies and executable equations from the supplied record. '
        'Return JSON {"outcome":"'+case['queries'][0]['target']+'","nodes":[{"id":"V00","parents":[],"expr":{"noise":"UV00"},'
        '"observed":0,"unknown":false,"segments":["seg_V00"],"event_status":"established",'
        '"function_identification":"identified|unidentified","description":"brief exact rule interpretation",'
        '"assumptions":[],"influences":[{"parent":"V01","direction_status":"explicit|contextually_supported|unsupported",'
        '"segments":["seg_V00"],"contradictions":[],"temporal_status":"consistent","information_status":"consistent"}]}]}. '
        'Use each station ID once. A root retains its explicitly named background setting. A nonroot uses no extra residual. '
        'For an absent rule mark unknown=true, function_identification=unidentified, and put one admissible fixed function of its declared parents DIRECTLY in expr. '
        'The function must reproduce the stated factual row and depend actively on each declared parent. Describe its assumed status in assumptions as text. '
        'Never put a noise/background expression on an internal station, even when its rule is absent. Never put the executable expression only in assumptions. '
        'An explicitly stated dependence can have directional support even if its exact combination rule is absent. '
        'Unsupported connections remain unsupported. Influences list exactly the proposed parents. '
        'Do not include answers to intervention questions or use information beyond the record. Keep JSON compact.\nRECORD:\n'+case['narrative'])


def validate(response, case):
    model=normalize_benchmark(response,case)
    if model['outcome']!=case['queries'][0]['target']:raise InvalidModel('The specified outcome is '+case['queries'][0]['target'])
    expected={s['node_id'] for s in case['segments']}
    if {n['id'] for n in model['nodes']}!=expected:raise InvalidModel('Use every station ID in the supplied record exactly once')
    allowed_segments={s['id'] for s in case['segments']}
    for node in model['nodes']:
        if node['parents'] and node.get('noise'):raise InvalidModel('The controlled record has no unmentioned internal residual/background')
        if not isinstance(node.get('unknown'),bool):raise InvalidModel('unknown must be a Boolean')
        if any(s not in allowed_segments for s in node.get('segments',[])):raise InvalidModel('Unknown source segment identifier')
        influences=node.get('influences',[])
        if sorted(e.get('parent','') for e in influences)!=sorted(node['parents']):raise InvalidModel('Influences must contain each declared parent exactly once')
        for edge in influences:
            if any(s not in allowed_segments for s in edge.get('segments',[])):raise InvalidModel('Unknown influence evidence reference')
    scm=SCM(model)
    for node in model['nodes']:
        node['generated_description']=node.get('description','')
        report=inspect_mechanism(scm,node['id'])
        node['description']=report['derived_description']
        node['behavior_signature']=report['signature']
    model['assumptions']=['The declared deterministic finite mechanism family and fixed factual backgrounds bound this controlled task.']
    return model


def run_case(root, case, seed=2701, controls=True):
    root,run,result=paths(root);gen=V2Generator(root)
    destination=run/'benchmark'/(case['id']+'.json')
    if destination.exists():
        existing=json.loads(destination.read_text())
        if existing.get('completed'):return existing
    started=time.time()
    record={'id':case['id'],'scm_id':case['scm_id'],'split':case['split'],'condition':case['condition'],
        'size':case['size'],'seed':seed,'methods':{},'synthesis_attempts':[],'stage_failures':[],'started_at':started}
    q_index=case['seed']%len(case['queries']);selected=case['queries'][q_index]
    packet=[{'id':q['id'],'question':q['text']} for q in case['queries']]
    common=('Use ONLY the supplied record. Return all supported binary values for each query, or explicit abstention if underidentified. '
        'Return {"answers":[{"id":"q00","values":[0],"abstain":false}],"ranked_sources":["segment_ID"]}. '
        'ranked_sources ranks up to FIVE passages relevant to resolving the outcome or its uncertainty for query '+selected['id']+'. '
        'Do not confuse observed states with complete missing rules.\nRECORD:\n'+case['narrative']+'\nQUESTIONS:\n'+json.dumps(packet))
    def checkpoint():atomic_json(destination,record)
    def call_baseline(method,prompt):
        try:record['methods'][method]=gen.call('v2_'+method,prompt,2048,seed)
        except Exception as error:
            record['methods'][method]={'error':str(error)};record['stage_failures'].append({'stage':method,'error':str(error)})
        checkpoint()
    call_baseline('B0',common)
    prompt=synthesis_prompt(root,case);model=None
    for attempt in range(3):
        response=None
        try:
            response=gen.call('v2_synthesis' if not attempt else 'v2_synthesis_repair',prompt,4096,seed+attempt)
            model=validate(response,case)
            record['synthesis_attempts'].append({'attempt':attempt,'valid':True,'response':response})
            break
        except Exception as error:
            record['synthesis_attempts'].append({'attempt':attempt,'valid':False,'response':response,'error':str(error)})
            prompt=synthesis_prompt(root,case)+'\nFORMAL/RECORD DIAGNOSTIC: '+str(error)+'\nRegenerate a complete compact candidate using only the supplied text. No gold function or counterfactual answer is provided.'
        finally:checkpoint()
    graph=[{'id':n['id'],'parents':n['parents']} for n in model['nodes']] if model else []
    call_baseline('B1',common+'\nEXTRACTED GRAPH (may be imperfect; contains no equations):\n'+json.dumps(graph))
    record['explanation_query']=selected['id']
    if model:
        record['model']=model
        record['methods']['B2']={'answers':outcome_sets([model],case['queries'])}
        try:
            family=compatible_family(model)
            record['family']=family['summary']
            record['methods']['ALT']={'answers':outcome_sets(family['models'],case['queries'])}
            trace=explain_query(model,selected,family['models'])
            record['trace']=trace
            # Same structural answers; additional outputs are scored separately.
            record['methods']['FULL']={'answers':record['methods']['ALT']['answers'],
                'ranked_sources':[s['segment_id'] for s in trace['evidence_priority']['segments'] if s['priority']>0],
                'ranking_available':trace['ranking_available']}
            record['methods']['UNIFORM']={'ranked_sources':[s['segment_id'] for s in trace['uniform_priority']['segments'] if s['priority']>0]}
            checkpoint()
            record['explanation']=explain(gen,trace,seed)
            checkpoint()
            if controls:record['reviewer_controls']=reviewer_controls(gen,trace,seed)
        except Exception as error:
            record['stage_failures'].append({'stage':'family_or_explanation','error':type(error).__name__+': '+str(error)})
    else:
        for method in ('B2','ALT','FULL'):record['methods'][method]={'error':'No admissible model after two repairs'}
    record['elapsed_seconds']=time.time()-started;record['completed']=True
    checkpoint()
    atomic_json(run/'inference_usage.json',gen.summary())
    return record


def run(root, split='development', pilot=False):
    root,folder,result=paths(root)
    cases=[json.loads(line) for line in (folder/'benchmark_cases.jsonl').read_text().splitlines()]
    if split=='test' and not (root/'configs/v2_frozen_protocol.json').exists():
        raise RuntimeError('Test inference requires the pilot gate and frozen protocol')
    selected=[c for c in cases if c['split']==split]
    if pilot:
        selected=[next(c for c in selected if c['condition']==condition and c['size']==8) for condition in ('complete','missing_intermediate','missing_outcome','multiple_missing')]
    for case in selected:
        print('V2_BEGIN',case['id'],case['condition'],flush=True)
        record=run_case(root,case)
        print('V2_DONE',case['id'],'valid',bool(record.get('model')),'seconds',round(record['elapsed_seconds'],1),flush=True)
    return len(selected)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--split',default='development',choices=['development','calibration','test']);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    print('Records processed',run(a.root,a.split,a.pilot))
