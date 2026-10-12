"""Replay construction after correcting the outcome-stage evidence omission."""
import json,shutil
import requests
from got_war.budget import Budget,atomic_json
from got_war.application import run_application

b=Budget('.')
for case in json.loads((b.root/'configs/experiment.json').read_text())['cases']:
    folder=b.run/'application'/case['id']
    marker=b.run/'outcome_packet_correction'/(case['id']+'.json')
    if marker.exists():continue
    archive=b.run/'application_before_outcome_packet_fix'/case['id']
    if not archive.exists():
        archive.parent.mkdir(exist_ok=True)
        folder.rename(archive);folder.mkdir()
        for pattern in ('facts_*.json','fact_audit_*.json','state_schema_*.json','coverage_*.json'):
            for file in archive.glob(pattern):shutil.copy2(file,folder/file.name)
        if (archive/'ordered_graph').exists():shutil.copytree(archive/'ordered_graph',folder/'ordered_graph')
    print('OUTCOME PACKET CORRECTION',case['id'],flush=True)
    run_application('.',case_ids=[case['id']],alternatives=[0])
    accepted=list(folder.glob('alternative_*.json'))
    if not accepted:
        run_application('.',case_ids=[case['id']],alternatives=[1])
        accepted=list(folder.glob('alternative_*.json'))
    atomic_json(marker,{'case':case['id'],'accepted_models':[str(p.relative_to(b.root)) for p in accepted],
        'previous_protocol':str(archive.relative_to(b.root)),
        'selection':'Use the corrected outcome evidence input, independent of node count or numerical results. If no model validates, report that failure; do not silently substitute the incomplete-input model.'})

# First finish all case schemas. Extra alternatives must preserve the audit and
# explanation allowance; this gate uses the service counter, including aborts.
for case in json.loads((b.root/'configs/experiment.json').read_text())['cases']:
    response=requests.get('http://127.0.0.1:8765/metrics',timeout=10);response.raise_for_status()
    used=sum(float(line.rsplit(' ',1)[1]) for line in response.text.splitlines() if line.startswith('vllm:generation_tokens_total'))
    if used>850000:
        atomic_json(b.run/'alternative_scope_reduction.json',{'generated_tokens':used,'reason':'Reserve at least 150,000 tokens of the initial ceiling for remaining core validation, source audits, explanations and recovery. Prior-protocol alternatives remain archived.'})
        break
    folder=b.run/'application'/case['id']
    if list(folder.glob('alternative_*.json')):run_application('.',case_ids=[case['id']],alternatives=[1,2])
