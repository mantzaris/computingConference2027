"""Measured component reports and a source-linked, unadjudicated review packet."""
import collections
import csv
import html
import json
from pathlib import Path
from ..budget import atomic_json
from ..structural_programs import SCM,equation
from .runtime import paths


def ci(row):
    if row['estimate'] is None:return 'not evaluable'
    return '%.3f [%.3f, %.3f]'%(row['estimate'],row['lower'],row['upper'])


def benchmark_reports(root):
    root,run,result=paths(root);summary=json.loads((result/'test_summary.json').read_text())
    rows=summary['tables'];all_rows=[r for r in rows if r['condition']=='all']
    text=['# Version 2 measured results','',
        'Completed %d of %d planned held-out SCM records. All planned test SCMs remain in the primary denominator. Questions are repeated measurements within SCMs. Intervals are 95%% SCM bootstrap intervals.'%(summary['completed_records'],summary['planned_scms']),'',
        '| Method | Identified accuracy | Outcome changes | Outcome preserved | Appropriate uncertainty | Unsupported confident answers |',
        '|---|---:|---:|---:|---:|---:|']
    metrics=('identified_correct','changed_correct','unchanged_correct','uncertainty_appropriate','unsupported_confident')
    for row in all_rows:text.append('| '+row['method']+' | '+' | '.join(ci(row['metrics'][m]) for m in metrics)+' |')
    text += ['', 'B0: direct LLM; B1: same text plus generated graph; B2: one synthesized model; ALT: compatible mechanisms; FULL: ALT answers plus separately assessed path/evidence/explanation outputs. CARRY retains the factual outcome. ORACLE_FAMILY receives the declared compatible family. ORACLE_TRUE receives the hidden generating model and is a point-prediction diagnostic, not an uncertainty oracle.', '',
        '## Mechanism completeness','', '| Condition | Method | Identified accuracy | Changed | Preserved | Appropriate uncertainty |','|---|---|---:|---:|---:|---:|']
    for row in rows:
        if row['condition']=='all' or row['method'] not in ('B0','B1','B2','ALT'):continue
        text.append('| '+row['condition']+' | '+row['method']+' | '+' | '.join(ci(row['metrics'][m]) for m in metrics[:4])+' |')
    text += ['', '## Paired differences','', '| Comparison | Identified accuracy difference | Changed accuracy difference | Uncertainty difference |','|---|---:|---:|---:|']
    for row in summary['paired_differences']:
        text.append('| '+row['left']+' − '+row['right']+' | '+' | '.join(ci(row['metrics'][m]) for m in ('identified_correct','changed_correct','uncertainty_appropriate'))+' |')
    text += ['', '## Separate components','', '| Component | Estimate [95% interval] |','|---|---:|']
    for key,value in summary['components'].items():text.append('| '+key+' | '+ci(value)+' |')
    text += ['', 'These are controlled explicit-rule texts. Their known functional semantics support equation and intervention scoring, but do not validate narrative concept discovery or Game of Thrones counterfactuals. Displayable prose has passed software checks and same-model review; it is not independently adjudicated. Successful-synthesis-only statistics are secondary and stored in `test_summary.json`.', '',
        '## Error inventory','']
    attempts=collections.Counter();stages=collections.Counter();failed=[]
    for f in (run/'benchmark').glob('*.json'):
        record=json.loads(f.read_text())
        if record['split']!='test':continue
        if not record.get('model'):failed.append(record['id'])
        for a in record['synthesis_attempts']:
            if not a.get('valid'):attempts[a.get('error','unknown').split('[')[0].split(':')[0].strip()]+=1
        for s in record['stage_failures']:stages[s['stage']+': '+s['error'].split(':')[0]]+=1
    text += ['Failed-synthesis SCMs: '+(', '.join(failed) if failed else 'none')+'.', '',
        'Attempt-level formal failures (multiple attempts can belong to one SCM): `'+json.dumps(dict(attempts),sort_keys=True)+'`.', '',
        'Other recorded stage failures: `'+json.dumps(dict(stages),sort_keys=True)+'`.', '',
        'Interpretation: a graph/input mismatch rejects an equation that omits or adds a declared input; a factual mismatch rejects a function that fails its supplied factual row. Finite-table repairs expose those local behaviors explicitly. Valid equations can still misread a stated rule, misclassify missing-function uncertainty, or support unfaithful prose; the separate metrics retain those errors.']
    (result/'RESULTS.md').write_text('\n'.join(text)+'\n')
    source=['# Source-priority evaluation','',summary['source_relevance_definition'],'',
        '| Method | nDCG@5 [95% SCM interval] |','|---|---:|']
    for method,score in summary['source_priority'].items():source.append('| '+method+' | '+ci(score)+' |')
    source += ['', '| Paired FULL difference | nDCG@5 difference |','|---|---:|']
    for method,score in summary['source_priority_paired'].items():source.append('| versus '+method+' | '+ci(score)+' |')
    source += ['', 'The labels concern structural information needed to resolve a query, not the desirability of an episode or human reading benefit. FULL can have no ranking when its selected-path contrast is zero even though rule passages explain the invariance. Those cases receive zero if independent relevance labels are positive. Uniform support uses the same paths and structural allocations; with correctly extracted explicit directional statements, its weights can coincide with FULL even when exact functions are unknown. Such equality does not demonstrate a benefit from evidence weighting. Application priorities have no independently adjudicated relevance labels and are reported as provisional review priorities only.']
    (result/'SOURCE_PRIORITY.md').write_text('\n'.join(source)+'\n')
    explain=['# Explanation generation and reviewer quality','',
        'Software creates the outcome/intervention record before prose generation. The LLM uses supplied values, and software assigns fixed sentence IDs before review. Invalid IDs are reviewer failures; unsupported or numerically invalid prose is an explanation failure. A schema-valid reviewer can still be wrong.', '',
        '| Component | Estimate [95% SCM interval] |','|---|---:|']
    for key,value in summary['components'].items():
        if key.startswith(('explanation','reviewer')):explain.append('| '+key+' | '+ci(value)+' |')
    explain += ['', 'Each controlled reviewer probe includes a true factual value, a flipped factual value, an invalid probability interpretation, and an explicit model/reference-dependence statement. Expected labels are withheld from its prompt. These software-defined controls evaluate simple trace fidelity and interpretation, not subtle literary entailment. Numeric checks verify allowed values, declared field/value claims, identifiers and tie qualifications; they are not a complete natural-language theorem prover. The same model generates and reviews prose, so its judgments are dependent. Independent researcher review remains pending unless a separately recorded response says otherwise.']
    (result/'EXPLANATION_REPORT.md').write_text('\n'.join(explain)+'\n')


def application_reports(root,case='five_kings'):
    root,run,result=paths(root)
    app=json.loads((run/'application'/case/'final.json').read_text());principal=app['records'][0]
    model=principal['model'];scm=SCM(model);packet=json.loads((root/('.private/v2/'+case+'_packet.json')).read_text())
    segments={s['id']:s for s in packet['segments']};nodes={n['id']:n for n in model['nodes']}
    rows=[]
    for key,e in principal['edge_evidence'].items():
        rows.append({'edge':key,'parent_event':nodes[e['parent']]['definition'],'child_event':nodes[e['child']]['definition'],
            'parent_status':e['parent_event_status'],'child_status':e['child_event_status'],'direction_status':e['status'],
            'direction_weight':e['score'],'function_identification':e['function_identification'],
            'function_equation':equation(nodes[e['child']]['expr']),'source_ids':';'.join(e.get('segments',[])),
            'source_urls':';'.join(segments[s]['url'] for s in e.get('segments',[]) if s in segments),
            'temporal_status':e.get('temporal_status'),'information_status':e.get('information_status'),
            'contradictions':json.dumps(e.get('contradictions',[])),'unresolved_questions':json.dumps(e.get('review_questions',[])),
            'direction_reason':e.get('direction_reason',''),'human_adjudication':'pending'})
    with (result/(case+'_evidence_audit.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    audit=['# '+app['case']['name']+': evidence and mechanism audit','',
        app['case']['outcome'],'',app['source_review'],'',
        '%d variables, %d edges, %d retained functionally distinct models, and %d distinct intervention-outcome vectors.'%(len(nodes),scm.graph.number_of_edges(),len(app['records']),app['alternatives']['distinct_query_vectors']),'',
        'Alternative coverage: '+app['alternatives']['coverage'],'',
        '| Variable | Operational definition | Factual state | Event status | Function status |','|---|---|---|---|---|']
    for n in model['nodes']:
        audit.append('| '+n['id']+' | '+n['definition'].replace('|','/')+' | '+str(n['observed'])+' | '+n.get('event_status','unassessed')+' | '+n.get('function_identification','unidentified')+' |')
    audit += ['', 'All source references, directional judgments, exact equations and unresolved questions appear in `'+case+'_evidence_audit.csv`. Endpoint event support does not establish a causal direction; directional support does not identify the function. Repeated transcriptions/summaries of one episode do not count as independent corroboration. A retained unresolved hypothesis is not an established evidence-compatible mechanism.', '',
        '## Mechanism behavior','']
    for n in model['nodes']:
        b=n['behavior'];audit += ['- **'+n['id']+'**: `'+equation(n['expr'])+'`; '+b['coverage']+'. Necessary conditions for output one: `'+json.dumps(b['necessary_for_one'])+'`; individually sufficient: `'+json.dumps(b['sufficient_for_one'])+'`.']
    audit += ['', 'These necessity/sufficiency statements concern the assumed function over its declared domain. They do not assert what would historically have happened in the narrative. Truth tables and all candidate expressions are retained for reproduction and reviewer inspection.']
    (result/(case+'_APPLICATION_AUDIT.md')).write_text('\n'.join(audit)+'\n')
    path=['# '+app['case']['name']+': path-coalition behavior','',
        'Paths are shared-edge coalition players with explicit parent references. Edge union activates a shared edge once; allocations are neither independent event effects nor natural path-specific effects. All comparisons below align the same node meanings and path sequences.','',
        '| Model | Coalition outcome histogram | All paths required | Substitute path sets | Negative marginals | Allocation vector |','|---|---|---|---|---:|---|']
    for record in app['records']:
        a=record['attribution'];path.append('| '+record['model']['id']+' | `'+json.dumps(a['coalition_histogram'])+'` | '+str(a['all_paths_required'])+' | '+str(a['substitute_path_sets'])+' | '+str(a['negative_marginals'])+' | `'+str([round(x,5) for x in a['phi']])+'` |')
    path += ['', '## Principal evidence-weighted paths','', '| Path | Node sequence | Signed allocation | Weakest directional support |','|---|---|---:|---:|']
    for p in principal['evidence_priority']['paths']:
        path.append('| '+p['path_id']+' | '+' → '.join(p['nodes'])+' | %.6f | %.2f |'%(p['signed_contribution'],p['evidence_support']))
    path += ['', 'Ranking status: **'+('available, provisional automated evidence assessment' if principal['ranking_available'] else 'unavailable: every evidence-weighted priority is zero')+'**.', '',
        'High-influence, weak-evidence paths remain visible in the table; zero evidence weights are never raised to create an ordering. Equal allocations are a model consequence, not automatically an informative explanation. In particular, unanimity and substitutable-path games can both have equal Shapley shares, so their coalition distributions must also be inspected.', '',
        '## Reference and path selection sensitivity','', '| Scenario | Baseline | Full | Shares |','|---|---:|---:|---|']
    for label,a in [('declared',principal['attribution'])]+list(principal['reference_sensitivity'].items())+list(principal['path_selection_sensitivity'].items()):
        path.append('| '+label+' | '+str(a['baseline'])+' | '+str(a['full'])+' | `'+str([round(v,5) for v in a['phi']])+'` |')
    path += ['', 'Factual-null and domain-endpoint references are explicit sensitivity checks, not necessarily meaningful alternative histories. Restricting the player set changes the estimand. A full selected-path coalition need not cover every explanatory route in a larger graph.', '',
        '## Shared outcome queries','', '| Intervention | Outcome set across retained mechanisms |','|---|---|']
    by_id={q['id']:q for q in app['queries']}
    for a in app['outcome_sets']:path.append('| `'+json.dumps(by_id[a['id']]['do'])+'` | `'+str(a['values'])+'` |')
    (result/(case+'_PATH_BEHAVIOR.md')).write_text('\n'.join(path)+'\n')
    # Reviewer sees source context locally; the Git packet contains traceable links
    # and claims, not redistributed full episode transcripts.
    selected=sorted(rows,key=lambda r:(r['direction_weight'],r['edge']))[:6]
    packet_text=['# Independent review packet: '+app['case']['name'],'','Status: **pending; no human adjudication is claimed**.','',
        'Read the full contextual passages in the local private HTML packet or the source links. For each item assess separately (1) event/state establishment, (2) directional causal influence, and (3) constraints on the exact function. Check time, who knew what, contradiction, and whether a statement is fact, report or belief. A function may fit the observed row without being identified.', '',
        'The items below are selected by lowest directional weight then stable edge ID for a compact skeptical review, not as independent relevance gold labels. Full audits include all edges.']
    page=['<!doctype html><meta charset="utf-8"><title>Independent source review</title><style>body{max-width:1000px;margin:2em auto;font:16px/1.5 sans-serif}pre{white-space:pre-wrap;background:#f5f5f5;padding:1em}section{border-top:2px solid #777;margin-top:2em}</style><h1>Independent source review — pending</h1>']
    annotations=[]
    for i,row in enumerate(selected,1):
        ident='R%02d'%i;edge=principal['edge_evidence'][row['edge']];child=nodes[edge['child']]
        packet_text += ['', '## '+ident+': '+row['edge'],'',row['parent_event']+' → '+row['child_event'], '',
            'Proposed equation: `'+row['function_equation']+'`. Direction: '+row['direction_status']+'; function: '+row['function_identification']+'.', '',
            'Sources: '+', '.join('['+s+']('+segments[s]['url']+')' for s in edge.get('segments',[]) if s in segments)+'.', '',
            'Open questions: '+row['unresolved_questions']+'.']
        page += ['<section><h2>'+ident+' '+html.escape(row['edge'])+'</h2><p>'+html.escape(row['parent_event']+' → '+row['child_event'])+'</p>',
            '<pre>'+html.escape(json.dumps({'equation':row['function_equation'],'actual_behavior':child['behavior'],'audit':edge},indent=2))+'</pre>']
        source_ids=list(dict.fromkeys(nodes[edge['parent']]['segments']+child['segments']+edge.get('segments',[])))
        for source in source_ids:
            segment=segments[source];page+=['<h3><a href="'+html.escape(segment['url'])+'">'+html.escape(source)+'</a></h3><pre>'+html.escape(segment['text'])+'</pre>']
        page.append('</section>')
        annotations.append({'item':ident,'edge':row['edge'],'event_judgment':'','direction_judgment':'','function_constraints':'','temporal_information_issues':'','reviewer_notes':'','reviewed_at':''})
    private=root/'.private/v2';(private/(case+'_review_packet.html')).write_text('\n'.join(page))
    (result/(case+'_REVIEW_PACKET.md')).write_text('\n'.join(packet_text)+'\n')
    review_file=result/(case+'_review_form.csv')
    if not review_file.exists():
        with review_file.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(annotations[0]));writer.writeheader();writer.writerows(annotations)
    atomic_json(result/(case+'_application_summary.json'),{'case':app['case'],'nodes':len(nodes),'edges':scm.graph.number_of_edges(),
        'alternatives':app['alternatives'],'event_statuses':dict(collections.Counter(n.get('event_status') for n in nodes.values())),
        'direction_statuses':dict(collections.Counter(e['status'] for e in principal['edge_evidence'].values())),
        'path_supports':[p['evidence_support'] for p in principal['evidence_priority']['paths']],
        'path_shares':principal['attribution']['phi'],'coalition_histogram':principal['attribution']['coalition_histogram'],
        'ranking_available':principal['ranking_available'],'explanation_displayable':app['explanation']['displayable'],
        'source_review':app['source_review']})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--case',default='five_kings');p.add_argument('--application-only',action='store_true');a=p.parse_args()
    if not a.application_only:benchmark_reports(a.root)
    application_reports(a.root,a.case)
