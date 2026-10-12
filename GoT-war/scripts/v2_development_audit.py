"""Summarize retained development records without changing any scientific label."""
import collections
import hashlib
import json
from pathlib import Path
import sys
import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v2.runtime import paths
from got_war.budget import atomic_json


def main():
    root,run,result=paths(ROOT);variants={}
    for name in ('five_kings','five_kings_refinement'):
        folder=run/'application'/name
        if not folder.exists():continue
        info={'completed':(folder/'final.json').exists(),'failure_records':[],'nodes':[]}
        for file in sorted(folder.glob('*failure*.json')):
            data=json.loads(file.read_text())
            info['failure_records'].append({'path':str(file.relative_to(root)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                'error':str(data.get('error',data))[:1000]})
        graph=folder/'graph.json'
        if graph.exists():
            data=json.loads(graph.read_text());info['graph_sha256']=hashlib.sha256(graph.read_bytes()).hexdigest()
            info['nodes']=[{k:n.get(k) for k in ('id','label','definition','type','time','parents','event_status','reference','reference_meaning')} for n in data['nodes']]
            info['event_times']=dict(collections.Counter(str(n.get('time')) for n in data['nodes']))
            info['proposition_kinds']=dict(collections.Counter(n.get('proposition_kind') for n in data['nodes']))
        variants[name]=info
    ledger=[json.loads(line) for line in (run/'requests.jsonl').read_text().splitlines()]
    roles=collections.Counter(r['role'] for r in ledger)
    cases=[json.loads(line) for line in (run/'benchmark_cases.jsonl').read_text().splitlines()]
    design={}
    for split in ('development','calibration','test'):
        selected=[c for c in cases if c['split']==split]
        shared=0
        for c in selected:
            graph=nx.DiGraph((p,n['id']) for n in c['gold']['nodes'] for p in n['parents'])
            shared+=any(degree>1 for _,degree in graph.out_degree())
        design[split]={'scms':len(selected),'scms_with_shared_causes':shared,
            'generating_rule_occurrences':dict(collections.Counter(n['generated_family'] for c in selected for n in c['gold']['nodes'] if n['parents'])),
            'topology_redraws':sum(c['topology_retries'] for c in selected),
            'interpretation':'Rule occurrences and questions are not independent samples; SCMs are the independent units. Topology redraws enforce the predeclared omission feasibility criterion, not method scores.'}
    report={'version':2,'scope':'Development and source-construction provenance; repeated/cached repairs and snapshots are not independent experiments.',
        'variants':variants,'requests_by_role':dict(roles),'controlled_design_audit':design,
        'source_inspection':'Targeted assistant flags remain in results/v2/source_inspection.json, separately scoped to fresh and conditional-refinement variants. No human adjudication or error-rate sample.',
        'methodological_consequences':[
            'Fresh concept selection can concentrate on early events and composite states despite later outcome evidence. More corpus volume alone did not produce an adequate operational model.',
            'Acyclic ordering prevents formally cyclic dependencies but does not establish the temporal or informational truth of an edge. Unknown/composite timing remains unresolved.',
            'Categorical domains exposed failures masked by all-Boolean prototypes. Finite tables make the actual function inspectable but do not make its inputs or causal claim correct.',
            'Factual-row compatibility and active-input diagnostics expose model inconsistency. Retractions are generated and invariance-certified; manually forcing a proposed dependency to matter would manufacture a mechanism.',
            'An inherited LLM graph can diagnose downstream refinement only. It cannot rescue or establish fresh source-based concept discovery.',
            'Automated contextual acceptance can overlook operational ambiguity; event, direction and exact-function judgments still require separate independent adjudication.'],
        'unrun_scope':'No second model, extra application seeds or reader study. Northern and Daenerys v1 failure cases are preserved; no v2 transfer claim is made.'}
    atomic_json(result/'development_audit.json',report)
    print(json.dumps({'variants':{k:{'completed':v['completed'],'failure_records':len(v['failure_records'])} for k,v in variants.items()}}))


if __name__=='__main__':main()
