"""Read-only, dependency-free audit of the preserved failed LLM edit interface."""
import collections
import hashlib
import json
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[3]

def acyclic(d,edges):
    remaining=set(range(d))
    while remaining:
        roots={j for j in remaining if not any(a in remaining and b==j for a,b in edges)}
        if not roots:return False
        remaining-=roots
    return True

def classify(value,request,seen):
    ids=[r['id'] for r in request['nodes']];d=len(ids)
    if not isinstance(value,dict):return 'malformed_output',None
    if value.get('nodes')!=ids:return 'invalid_nodes',None
    if not isinstance(value.get('edges'),list):return 'malformed_output',None
    edges=[]
    for edge in value['edges']:
        if not isinstance(edge,dict) or set(edge)!={'source','target','rationale'} or not isinstance(edge['rationale'],str):
            return 'malformed_output',None
        if edge['source'] not in ids or edge['target'] not in ids:return 'invalid_nodes',None
        edges.append((ids.index(edge['source']),ids.index(edge['target'])))
    if len(set(edges))!=len(edges):return 'duplicate_edges',None
    edges=frozenset(edges)
    if not acyclic(d,edges):return 'cycles',None
    if any(b in request.get('roots',()) for a,b in edges) or any(sum(b==j for a,b in edges)>3 for j in range(d)):
        return 'design_constraint_violation',None
    initial=frozenset(map(tuple,request['feedback']['incumbent']['edges']))
    if edges==initial:return 'valid_no_change',edges
    if edges in seen:return 'duplicate_graphs',edges
    seen.add(edges)
    difference=edges^initial
    legal=len(difference)==1 or (len(difference)==2 and all((b,a) in difference for a,b in difference))
    return ('valid_new_edits' if legal else 'valid_graph_not_single_edit'),edges

def audit():
    base=PROJECT/'.artifacts';counts=collections.Counter();rows=[];attempts=0;raw_hashes={}
    run_paths=sorted((base/'runs').glob('*-llm_edit-*/selection.json'))
    for selected_path in run_paths:
        selection=json.loads(selected_path.read_text());folder=selected_path.parent
        counts['score_rejections']+=sum(len(e['evaluated'])-int(e['accepted']) for e in selection['edits'])
        counts['accepted_changes']+=sum(e['accepted'] for e in selection['edits'])
        for path in sorted(folder.glob('llm-edit-*.json')):
            ri=path.stem.rsplit('-',1)[-1]
            request=json.loads((folder/f'llm-request-{ri}.json').read_text());result=json.loads(path.read_text())
            for record in result['records']:
                attempts+=1
                raw_path=base/'runs'/('llm-'+result['request_hash'][:20])/f'proposal-{record["proposal"]}-attempt-{record["attempt"]}.txt'
                raw=raw_path.read_text();raw_sha=hashlib.sha256(raw.encode()).hexdigest()
                if raw_sha!=record['raw_sha256']:raise ValueError('Historical raw generation changed')
                raw_hashes[str(raw_path.relative_to(base))]=raw_sha
                try:
                    payload=json.loads(raw[raw.index('{'):raw.rindex('}')+1]);proposals=payload['graphs'][:3]
                    if not isinstance(proposals,list):raise ValueError('graphs must be a list')
                except (ValueError,TypeError,KeyError):counts['malformed_output']+=1;continue
                seen={frozenset(map(tuple,c['graph']['edges'])) for c in request['feedback']['evaluated']}
                for i,value in enumerate(proposals):
                    category,graph=classify(value,request,seen);counts[category]+=1
                    rows.append({'run_id':folder.name,'round':int(ri),'attempt':record['attempt'],'proposal':i,
                        'category':category,'legacy_batch_valid':record['valid'],'edge_count':None if graph is None else len(graph),
                        'raw_sha256':raw_sha})
    for name in ('malformed_output','invalid_nodes','cycles','duplicate_graphs','valid_no_change','valid_new_edits','score_rejections','accepted_changes'):
        counts.setdefault(name,0)
    report={'historical_commit':'ad21e604ef37f65e20ce32d78b0c2d04a0737cd7','runs':len(run_paths),
        'query_attempts':attempts,'individually_classified_proposals':len(rows),'counts':dict(counts),
        'counting':'Proposal-level mutually exclusive validation category; malformed unparseable batches count once. Score/accept counts are verifier events.',
        'diagnosis':'The full-DAG contract was interpreted as isolated edge commands. Numeric incumbent IDs and V-prefixed response IDs made the interface ambiguous; batch validation discarded otherwise valid proposals when a sibling failed.',
        'historical_findings_preserved':True,'not_evidence_of_llm_ineffectiveness':True,'raw_file_hashes':raw_hashes,'proposals':rows}
    path=PROJECT/'phase2/results/historical_llm_audit.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('proposals','raw_file_hashes')},indent=2))
    return report

if __name__=='__main__':audit()
