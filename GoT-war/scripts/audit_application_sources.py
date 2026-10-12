"""Final source critique of principal schemas, separate from formal validation."""
import hashlib,json
from got_war.generation import Generator
from got_war.fact_pipeline import artifact
from got_war.budget import atomic_json
from got_war.structural_programs import InvalidModel

gen=Generator('.')
for folder in sorted((gen.run/'application').iterdir()):
    files=sorted(folder.glob('alternative_*.json'))
    if not files:continue
    record=json.loads(files[0].read_text());nodes=record['model']['nodes']
    packet=json.loads((gen.root/'.private/packets'/(folder.name+'.json')).read_text())
    segments={s['id']:s for s in packet['segments']}
    all_claims=[{k:n.get(k) for k in ('id','label','definition','time','parents')} for n in nodes]
    reviews=[];failures=[]
    for start in range(0,len(nodes),4):
        batch=nodes[start:start+4];evidence=[]
        for n in batch:
            related=[n]+[p for p in nodes if p['id'] in n['parents']]
            ids={c['segment_id'] for variable in related for c in variable.get('citations',[])}
            evidence.append({'variable':{k:n.get(k) for k in ('id','definition','actor','time','type','values','observed','reference','reference_meaning','status')},
                'actual_passages':[{'id':sid,'text':segments[sid]['text']} for sid in sorted(ids) if sid in segments]})
        prompt='Act as a skeptical final source reviewer. Audit the requested variables against their ACTUAL supplied passages. A name match or a literal quotation does not establish the complete claim. Check actor, action, object, scope, event versus report status, and whether the numerical story-time code (season*100+episode) refers to the event rather than an unrelated later state. Check comparison-state wording agrees with the encoded reference. Check whether any two registry variables duplicate the same event; do not treat repetition as distinct causal stages. Do not use outside memory or silently repair the graph. Return {"audits":[{"id":"requested node ID","event_support":"supported OR partial OR unsupported","story_time":"supported OR contradicted OR unknown","reference_semantics":"consistent OR inconsistent OR unresolved","duplicates":["other node ID, or empty"],"reason":"specific discrepancy or source entailment"}]}. Composite W occurrence can be partial even when reported campaign stages occurred. This audit is automated by the same model, not independent human validation.\nOUTCOME: '+record['case']['outcome']+'\nFULL REGISTRY: '+json.dumps(all_claims)+'\nREQUESTED CLAIMS AND ACTUAL EVIDENCE: '+json.dumps(evidence)
        prompt+='\nAlso include parent_order_flags:["parent ID"] for each audit. Flag a declared parent if the passages place it AFTER its child, including within the same episode. Equal episode codes do not prove causal precedence. The parent passages are included. Use an empty list when no source-backed reversal is found, and explain any uncertainty rather than inventing a chronology.'
        def check(response):
            requested={n['id'] for n in batch}
            rows=[r for r in response['audits'] if r.get('id') in requested]
            if len(rows)!=len(batch) or {r.get('id') for r in rows}!={n['id'] for n in batch}:raise InvalidModel('Exactly one audit for each requested node')
            for row in rows:
                if row.get('event_support') not in ('supported','partial','unsupported'):raise InvalidModel('Invalid event support')
                if row.get('story_time') not in ('supported','contradicted','unknown'):raise InvalidModel('Invalid time assessment')
                if row.get('reference_semantics') not in ('consistent','inconsistent','unresolved'):raise InvalidModel('Invalid reference assessment')
                if not set(row.get('duplicates',[]))<={n['id'] for n in nodes}:raise InvalidModel('Duplicate IDs must be in this registry')
                node=next(n for n in batch if n['id']==row['id'])
                row['parent_order_audit_complete']=not node['parents'] or 'parent_order_flags' in row
                flags=row.get('parent_order_flags',[])
                invalid=list(set(flags)-set(node['parents'])) if isinstance(flags,list) else [flags]
                if invalid:
                    row['invalid_parent_order_flags']=invalid
                    row['parent_order_audit_complete']=False
                    row['parent_order_flags']=[p for p in flags if p in node['parents']] if isinstance(flags,list) else []
            return rows
        key=hashlib.sha256(prompt.encode()).hexdigest()[:12]
        try:reviews.extend(artifact(gen,folder/'final_source_review'/('%02d_%s.json'%(start,key)),'application_final_source_review',prompt,check,2048,True))
        except Exception as error:failures.append({'batch':start,'error':str(error)})
    result={'model_id':record['model']['id'],'audits':reviews,'failures':failures,
        'unresolved_parent_order_fields':[r['id'] for r in reviews if not r.get('parent_order_audit_complete',False)],
        'response_normalization':'Select exactly the requested IDs from a response that may include unsolicited extra claims. Raw responses are preserved. Missing or invalid per-node parent-order fields remain unresolved; a misplaced top-level mapping is not relabeled as a temporal finding. Invalid parent IDs are retained separately, not treated as graph edges.',
        'status':'completed' if len(reviews)==len(nodes) and not failures else 'incomplete',
        'interpretation':'Exploratory same-model critique after construction. Does not change the frozen graph or certify causal identification. Negative findings must accompany diagrams and require researcher review.'}
    atomic_json(folder/'final_source_review.json',result)
    print(folder.name,result['status'],'flagged',sum(bool(r['event_support']!='supported' or r['story_time']=='contradicted' or r['reference_semantics']!='consistent' or r.get('duplicates') or r.get('parent_order_flags')) for r in reviews),flush=True)
