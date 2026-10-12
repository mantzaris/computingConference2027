"""Re-execute frozen artifacts and expose source/trace limits without GPU calls."""
import csv,json
from pathlib import Path
from .budget import atomic_json
from .structural_programs import SCM
from .attribution import coalitions


def verify(root):
    root=Path(root);run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
    rows=[];review=[]
    for file in sorted((run/'application').glob('*/alternative_*.json')):
        record=json.loads(file.read_text());scm=SCM(record['model'])
        attr=coalitions(scm,record['selection']['paths'],exact=record['attribution']['method']=='exact')
        difference=max([abs(a-b) for a,b in zip(attr['phi'],record['attribution']['phi'])]+[abs(attr['baseline']-record['attribution']['baseline']),abs(attr['full']-record['attribution']['full'])])
        query_matches=all(scm.solve(interventions=q['intervention'])[scm.model['outcome']]==q['modeled_outcome'] for q in record['queries'])
        packet_path=root/'.private/packets'/(record['case']['id']+'.json')
        citation_checks=[]
        if packet_path.exists():
            packet=json.loads(packet_path.read_text());segments={s['id']:s for s in packet['segments']}
            for citation in record['source_audit']:
                segment=segments.get(citation['segment_id']);quote=citation.get('quote','')
                offset=segment['text'].find(quote) if segment and quote else -1
                citation_checks.append(offset>=0 and citation['start']==segment['start']+offset and citation['end']==segment['start']+offset+len(quote))
        rows.append({'case':record['case']['id'],'model':scm.model['id'],'structural_validation':True,
                     'maximum_attribution_recompute_difference':difference,'efficiency_residual':attr['efficiency_residual'],
                     'query_recompute_matches':query_matches,'exact_source_offset_checks':len(citation_checks),
                     'exact_source_offset_valid':sum(citation_checks),'semantic_entailment':'not independently verified'})
        if record['model']['alternative']==min(int(p.stem.split('_')[-1]) for p in file.parent.glob('alternative_*.json')):
            for node in record['model']['nodes']:
                review.append({'case':record['case']['id'],'model_id':scm.model['id'],'record_type':'event','node_or_edge_id':node['id'],
                               'statement':node['definition'],'source_ids':';'.join(c['segment_id'] for c in node.get('verified_citations',[])),
                               'automatic_assessment':node.get('event_assessment','unassessed')})
            for edge_id,edge in record['edge_evidence'].items():
                review.append({'case':record['case']['id'],'model_id':scm.model['id'],'record_type':'mechanism','node_or_edge_id':edge_id,
                               'statement':edge.get('reason',''),'source_ids':';'.join(edge.get('segments',[])),
                               'automatic_assessment':edge.get('status','unassessed')})
    result={'models':rows,'all_recomputed':bool(rows) and all(r['maximum_attribution_recompute_difference']<1e-12 and r['query_recompute_matches'] and r['exact_source_offset_checks']>0 and r['exact_source_offset_valid']==r['exact_source_offset_checks'] for r in rows),
            'interpretation':'Re-execution and byte-offset checks, not independent validation of literary causal claims.'}
    atomic_json(root/'results/artifact_verification.json',result)
    destination=root/'docs/REVIEW_FORM_GENERATED.csv'
    # Do not overwrite any actual review someone may have subsequently supplied.
    if destination.exists():
        with destination.open() as f:
            if any(r.get('reviewer_id') for r in csv.DictReader(f)):return result
    columns=['case','model_id','record_type','node_or_edge_id','statement','source_ids','automatic_assessment','reviewer_id','event_supported','mechanism_supported','temporal_order_valid','continuity_valid','unsupported_assumption','notes']
    with destination.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');writer.writeheader();writer.writerows(review)
    return result
