"""Bounded actual CUDA semantic prior, with no measured outcomes or reference DAG."""
import hashlib
import json
import time
from sem_update.llm import LocalProposer, validate_graph
from app_data import VARS, ROOTS
from app_runtime import ROOT, RESULTS, atomic_json, read_json, job, cuda, digest

DESCRIPTIONS = [
    'Inlet fan PWM duty command, fraction 0 to 1; externally assigned.',
    'Outlet fan PWM duty command, fraction 0 to 1; externally assigned.',
    'Hatch opening command, degrees 0 closed to 45 open; externally assigned.',
    'Measured inlet fan rotational speed, revolutions per minute.',
    'Measured outlet fan rotational speed, revolutions per minute.',
    'Measured inlet fan electrical current, calibrated amperes; not electrical power.',
    'Measured outlet fan electrical current, calibrated amperes; not electrical power.',
    'Upwind barometer reading minus ambient barometer reading, pascals; not airflow.',
    'Downwind barometer reading minus ambient barometer reading, pascals; not airflow.',
    'Intake barometer reading minus ambient barometer reading, pascals; not airflow.',
    'Ambient barometric pressure, pascals; assumed exogenous environmental context.'
]

def canonicalize_nodes(value,nodes):
    """Accept metadata objects only when their ordered IDs match exactly.

    This serialization adapter changes no proposed edge, ID or rationale.
    """
    value=dict(value)
    if isinstance(value.get('nodes'),list) and all(isinstance(v,dict) for v in value['nodes']):
        value['nodes']=[v.get('id') for v in value['nodes']]
    return validate_graph(value,nodes,ROOTS)

def recover_metadata_schema():
    original=read_json(ROOT/'runs/llm-prior.json')
    nodes=[{'id':f'V{i}','name':name,'description':DESCRIPTIONS[i]} for i,name in enumerate(VARS)]
    recovered=[]
    for record in original['records']:
        raw=(ROOT/'runs'/f'llm-prior-{record["attempt"]}.txt').read_text()
        value=json.loads(raw[raw.index('{'):raw.rindex('}')+1])
        try:
            graph=canonicalize_nodes(value,nodes)
            recovered.append({'attempt':record['attempt'],'graph':graph.json(),'rationales':value['edges'],
                              'edge_payload_sha256':digest(value['edges'])})
        except (ValueError,KeyError,TypeError):pass
    result={**original,'strict_parser_original_sha256':file_hash_local(ROOT/'runs/llm-prior.json'),
        'serialization_recovery':'extract exact ordered IDs from returned node metadata objects; no edge changes; no new generations',
        'recovered_proposals':recovered,'graph':recovered[0]['graph'] if recovered else None,
        'fallback':None if recovered else original['fallback'],'selection_rule':'first valid original generation, before outcome access'}
    atomic_json(RESULTS/'llm_prior.json',result)
    atomic_json(ROOT/'runs/llm-prior-normalized.json',result)
    return result

def file_hash_local(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def generate():
    cuda(); path=ROOT/'runs/llm-prior.json'
    nodes=[{'id':f'V{i}','name':name,'description':DESCRIPTIONS[i]} for i,name in enumerate(VARS)]
    prompt=('Propose a sparse predictive structural DAG for a physical open-loop wind tunnel with two fans and a hatch. '
            'The intended task is quasi-steady response prediction. This is a fallible semantic prior, not established physics. '
            'No measured outcomes or reference graph are supplied. Do not claim causal discovery. Maximum three parents per node. '
            'No incoming edges to V0,V1,V2,V10. Return only JSON with nodes equal to the exact ordered IDs and edges a list '
            'of objects with exactly source,target,rationale. Give a brief physical hypothesis per edge. Avoid cycles. Variables: '+json.dumps(nodes))
    with job('llm-prior', {'prompt_sha256':digest(prompt),'seed':44201}) as active:
        if active:
            start=time.monotonic(); model=LocalProposer(); records=[]; graph=None
            for attempt in range(2):
                raw,stats=model.query(prompt,44201+attempt)
                (ROOT/'runs'/f'llm-prior-{attempt}.txt').write_text(raw)
                (ROOT/'runs'/f'llm-prior-{attempt}.prompt.txt').write_text(prompt)
                error=None; category='valid_new_graph'
                try:
                    value=json.loads(raw[raw.index('{'):raw.rindex('}')+1]); graph=validate_graph(value,nodes,ROOTS)
                except (ValueError,KeyError,TypeError) as e:
                    error=str(e); category='cycles' if 'cyclic' in error else 'invalid_nodes' if 'nodes' in error or 'not in list' in error else 'malformed_or_constraint'
                records.append({'attempt':attempt,'category':category,'error':error,'stats':stats,
                    'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'proposal':value if graph else None})
                if graph: break
                prompt+='\nValidation failed. Return the exact contract, all node IDs, at most three parents, and no incoming root edges.'
            atomic_json(path, {'actual_local_generation':True,'records':records,'graph':None if graph is None else graph.json(),
                'fallback':'training-only initialization' if graph is None else None,'revision':model.revision,
                'seconds':time.monotonic()-start,'model_load_seconds':model.load_seconds,'held_out_measurements_supplied':False,
                'reference_adjacency_supplied':False,'possible_pretraining_knowledge':True})
    return recover_metadata_schema()
