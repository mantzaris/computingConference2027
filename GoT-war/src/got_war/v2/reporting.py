"""Measured component reports and a source-linked, unadjudicated review packet."""
import collections
import csv
import html
import json
from pathlib import Path
from ..budget import atomic_json
from ..structural_programs import SCM,equation
from ..attribution import select_paths
from .runtime import paths,application_record


def ci(row):
    if row['estimate'] is None:return 'not evaluable'
    return '%.3f [%.3f, %.3f]'%(row['estimate'],row['lower'],row['upper'])


def tex(text):
    """Escape generated prose/labels, never silently insert them as TeX code."""
    mapping={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#',
             '_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(mapping.get(c,c) for c in str(text))


def table_ci(row):
    if row['estimate'] is None:return r'---'
    return r'\shortstack{%.3f\\{[%.3f, %.3f]}}'%(row['estimate'],row['lower'],row['upper'])


def manuscript_tables(root):
    """Populate measured manuscript sections only after the fixed test completes."""
    root,run,result=paths(root)
    summary=json.loads((result/'test_summary.json').read_text())
    if summary['completed_records']!=summary['planned_scms']:
        raise ValueError('The manuscript must not describe a partial test as complete')
    app=json.loads(application_record(root,run).read_text())
    principal=app['records'][0];paper=root/'paper/v2';paper.mkdir(exist_ok=True)
    rows={r['method']:r for r in summary['tables'] if r['condition']=='all'}
    macros=[]
    for name,method in [('Direct','B0'),('Graph','B1'),('Single','B2'),('Alt','ALT')]:
        macros.append(r'\newcommand{\Acc'+name+'}{%.1f\%%}'%(100*rows[method]['metrics']['identified_correct']['estimate']))
    macros += [r'\newcommand{\AppNodes}{%d}'%len(principal['model']['nodes']),
               r'\newcommand{\AppModels}{%d}'%len(app['records'])]
    usage_file=result/'usage.json'
    if usage_file.exists():
        usage=json.loads(usage_file.read_text())
        for name,key,format_spec in (
            ('RunElapsedHours','elapsed_hours','.2f'),
            ('RunGPUHours','sampled_utilization_weighted_gpu_hours','.2f'),
            ('RunResidentHours','sampled_resident_hours_above_1gib','.2f'),
            ('RunOutputTokens','output_tokens_from_server',',.0f'),
            ('RunRequests','requests',',d'),
            ('RunRequestErrors','request_errors','d'),
            ('RunPeakMemory','peak_sampled_vram_mib',',.0f')):
            value=usage.get(key)
            macros.append('\\newcommand{\\'+name+'}{'+(format(value,format_spec) if value is not None else 'unavailable')+'}')
    (paper/'measured_macros.tex').write_text('\n'.join(macros)+'\n')
    lines=[r'All 72 planned held-out SCM records completed. Table~\ref{tab:primary} reports SCM means with descriptive 95\% bootstrap intervals. Failed synthesis remains in each relevant primary denominator. FULL and ALT have identical outcome answers by construction; the additional FULL components are assessed separately.',
        'Eligible independent SCM counts are %d for identified questions, %d for outcome changes, %d for preserved outcomes and %d for underidentified questions. Eligibility follows the fixed questions, never method success.'%tuple(rows['B0']['metrics'][m]['scms'] for m in ('identified_correct','changed_correct','unchanged_correct','uncertainty_appropriate')),
        r'\begin{table}[t]\centering\small\setlength{\tabcolsep}{3pt}',
        r'\caption{Identified and underidentified questions; estimates and 95\% intervals.}\label{tab:primary}',
        r'\begin{tabular}{lrrrr}\toprule Method & Identified & Changes & Preserves & Uncertainty\\\midrule']
    for method in ('B0','B1','B2','ALT','CARRY','ORACLE_FAMILY'):
        values=[table_ci(rows[method]['metrics'][m]) for m in ('identified_correct','changed_correct','unchanged_correct','uncertainty_appropriate')]
        lines.append(tex(method)+' & '+' & '.join(values)+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{table}',
        r'\begin{table}[t]\centering\small\setlength{\tabcolsep}{3pt}',
        r'\caption{Complete versus incomplete mechanisms. Changed and preserved strata are scored separately.}\label{tab:missing}',
        r'\begin{tabular}{llrrr}\toprule Condition & Method & Changes & Preserves & Uncertainty\\\midrule']
    for condition in ('complete','missing_intermediate','missing_outcome','multiple_missing'):
        for method in ('B0','B2','ALT'):
            row=next(r for r in summary['tables'] if r['condition']==condition and r['method']==method)
            values=[table_ci(row['metrics'][m]) for m in ('changed_correct','unchanged_correct','uncertainty_appropriate')]
            lines.append(tex(condition.replace('missing_','omit ').replace('_',' '))+' & '+method+' & '+' & '.join(values)+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{table}',r'\paragraph{Paired comparisons.}']
    for pair in summary['paired_differences']:
        lines.append(tex(pair['left']+' minus '+pair['right'])+': identified accuracy '+tex(ci(pair['metrics']['identified_correct']))+
            '; outcome-changing accuracy '+tex(ci(pair['metrics']['changed_correct']))+'; appropriate uncertainty '+tex(ci(pair['metrics']['uncertainty_appropriate']))+'.')
    lines += [r'\paragraph{Separate synthesis, grounding, and explanation components.}',
        r'\begin{table}[t]\centering\small\begin{tabular}{lr}\toprule Component & Estimate [95\% interval]\\\midrule']
    for key,value in summary['components'].items():
        lines.append(tex(key.replace('_',' '))+' & '+tex(ci(value))+r'\\')
    lines += [r'\bottomrule\end{tabular}\caption{Components use all planned test SCMs. Same-model semantic review is dependent.}\label{tab:components}\end{table}',
        r'\paragraph{Source prioritization.}']
    for method,score in summary['source_priority'].items():
        lines.append(tex(method)+' nDCG@5: '+tex(ci(score))+'.')
    for method,score in summary['source_priority_paired'].items():
        lines.append('Paired FULL minus '+tex(method)+': '+tex(ci(score))+'.')
    lines.append('The independently fixed relevance labels describe the affected-mechanism slice, not human reading value. A zero modeled contrast can yield no ranking even when passages help explain invariance. The uniform-support ablation shares the same paths and allocations. Full results, conditional successful-synthesis estimates, error records, and all completeness strata accompany the release.')
    if usage_file.exists():
        usage=json.loads(usage_file.read_text());costs=usage.get('controlled_component_costs',{}).get('test',{})
        if costs and not usage.get('prompt_scope_audit',{}).get('private_prompt_missing'):
            lines += [r'\paragraph{Held-out computation.}',
                'The %d held-out requests used %s response-reported output tokens, identified by exact narrative matching. Summed request durations are %.2f hours and overlap across workers; they are not elapsed GPU time. Synthesis requests are shared by B1, B2, ALT and FULL. The release separates incremental costs by request role, including prose generation, review and controls.'%(sum(v['requests'] for v in costs.values()),format(sum(v['output_tokens'] for v in costs.values()),','),sum(v['request_seconds'] for v in costs.values())/3600)]
    (paper/'measured_results.tex').write_text('\n\n'.join(lines)+'\n')
    game=principal['attribution'];supports=[p['evidence_support'] for p in principal['evidence_priority']['paths']]
    app_lines=[tex(app['case']['outcome'])+r' We acquired ten first-season episode transcriptions from ScreenScripts~\cite{screenscripts}. They are traceable documentary material, not authenticated official scripts; transcription fidelity and interpretation require researcher review.',
        tex(app.get('construction_context',{}).get('scope','Fresh source-derived construction.')),
        'The LLM retained %d variables and %d directed influences. This application has one functional hypothesis, one intervention-outcome vector and one retained local-option combination. There is no demonstrated agreement across alternatives, and singleton outcome sets are consequences of that hypothesis, not identification from the sources.'%(len(principal['model']['nodes']),SCM(principal['model']).graph.number_of_edges()),
        'Four retained variables are fixed scope boundaries with unexplained upstream causes; only two functions connect endogenous variables. The ten-node target was not met. All seven directional judgments are unsupported. Targeted assistant inspection additionally flags planned versus realized actions, event timing, an inconsistent outcome audit, and reference-policy ambiguity. These are unresolved review issues, not independently adjudicated error labels.',
        'The six-path game has %d coalitions with outcome zero and %d with outcome one. Two minimal full-outcome coalitions provide substitute routes, so the full set of six paths is unnecessary. It has %d negative coalition marginal; its pair-interaction range is %s, exposing both joint enabling and substitution within the assumed program.'%(game['coalition_histogram'].get('0',0),game['coalition_histogram'].get('1',0),game['negative_marginals'],tex(str(game['pair_interaction_range']))),
        r'Table~\ref{tab:applicationpaths} identifies the selected paths and their signed allocations. Evidence-weighted source ranking was '+('available as a provisional automated priority' if principal['ranking_available'] else 'unavailable because all scores were zero')+'. No unsupported score was raised to create an ordering.',
        'The application explanation '+('passed the deterministic and same-model semantic checks' if app['explanation']['displayable'] else 'failed the displayability checks')+'. It contains six actual sentences instead of at most four and cites nonexistent numerical field names. The reviewer covers all six actual IDs but labels their text supported. Its controls score three of four: the probability claim is marked unverifiable rather than unsupported, with no false acceptance. Valid sentence coverage does not establish narrative entailment.',
        'Both factual-null and domain-endpoint reference checks yield zero allocations. Here their seven edge-reference assignments are identical: they are one null contrast, not two distinct robustness scenarios or defensible alternative histories. A four-path collection is a unanimity game: fifteen coalitions yield zero and one yields one, with four equal one-quarter shares. For the aligned scout-to-capture-to-war path, changing from six to four players changes its share from minus one-thirtieth to one-quarter without changing any equation. In the four-path game, mobilization-to-capture remains outside the selected union and active; the scout path bundles the necessary capture-to-outcome edge. Its positive allocation is therefore not an individual effect of the scout action. The factual intervention removing that action instead leaves the outcome unchanged. None of these quantities is a probability or historical responsibility.',
        'The source/equation audit, full-context private review packet, and blank independent review form remain available. These artifacts do not imply completed human adjudication. Local function behavior and shared outcome queries are reported separately; unresolved source compatibility remains a hypothesis.']
    path_table=[r'\begin{table}[t]\centering\small\setlength{\tabcolsep}{5pt}',
        r'\caption{The six-path global game. Node IDs map to the event labels in Fig.~\ref{fig:flagship}; $c_p$ is weakest directional support.}\label{tab:applicationpaths}',
        r'\begin{tabular}{llrr}\toprule Path & Node sequence & $\phi_p$ & $c_p$\\\midrule']
    for i,sequence in enumerate(principal['selection']['paths']):
        path_table.append('p%d & '%(i+1)+r' $\to$ '.join(r'\texttt{'+tex(n)+'}' for n in sequence)+' & $%.5f$ & %.1f'%(game['phi'][i],supports[i])+r'\\')
    path_table.append(r'\bottomrule\end{tabular}\end{table}')
    app_lines.insert(6,'\n'.join(path_table))
    (paper/'application_results.tex').write_text('\n\n'.join(app_lines)+'\n')


def benchmark_reports(root):
    root,run,result=paths(root);summary=json.loads((result/'test_summary.json').read_text())
    rows=summary['tables'];all_rows=[r for r in rows if r['condition']=='all']
    text=['# Version 2 measured results','',
        'Completed %d of %d planned held-out SCM records. All planned test SCMs remain in the primary denominator. Questions are repeated measurements within SCMs. Intervals are 95%% SCM bootstrap intervals.'%(summary['completed_records'],summary['planned_scms']),'',
        '| Method | Valid answers | Identified accuracy | Outcome changes | Outcome preserved | Appropriate uncertainty | Unsupported confident answers |',
        '|---|---:|---:|---:|---:|---:|---:|']
    metrics=('identified_correct','changed_correct','unchanged_correct','uncertainty_appropriate','unsupported_confident')
    for row in all_rows:text.append('| '+row['method']+' | '+' | '.join(ci(row['metrics'][m]) for m in ('valid_answer',)+metrics)+' |')
    text += ['', 'B0: direct LLM; B1: same text plus generated graph; B2: one synthesized model; ALT: compatible mechanisms; FULL: ALT answers plus separately assessed path/evidence/explanation outputs. CARRY retains the factual outcome. ORACLE_FAMILY receives the declared compatible family. ORACLE_TRUE receives the hidden generating model and is a point-prediction diagnostic, not an uncertainty oracle.', '',
        'Eligible SCM counts: '+', '.join(m+'='+str(all_rows[0]['metrics'][m]['scms']) for m in metrics[:4])+'. Eligibility is defined by the fixed questions, not method success.', '',
        'Zero-width bootstrap intervals at zero or one reflect resampling of the observed SCM scores; they do not guarantee identical performance on new SCMs. These are descriptive intervals, without multiplicity-adjusted discovery claims.', '',
        'Unsupported confident answers are nonabstaining singleton responses that are wrong or not identified by the record, divided by all questions within each SCM. Missing answers cannot be confident, so this rate must be read together with valid-answer coverage and synthesis failures; low coverage must not be mistaken for safe reasoning.', '',
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
    for f in sorted((run/'benchmark').glob('*.json')):
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
    usage_file=result/'usage.json'
    if usage_file.exists():
        usage=json.loads(usage_file.read_text());costs=usage.get('controlled_component_costs',{}).get('test',{})
        if costs:
            text += ['', '## Held-out component costs', '',
                usage['controlled_cost_interpretation'], '',
                'Prompt mapping status: `'+json.dumps(usage.get('prompt_scope_audit',{}),sort_keys=True)+'`. First held-out request: `'+str(usage.get('heldout_first_request_at'))+'`; all matched held-out requests follow the freeze: `'+str(usage.get('heldout_requests_after_freeze'))+'`.', '',
                '| Request role | Requests | Distinct SCMs | Input tokens | Output tokens | Sum request seconds | API/JSON errors |','|---|---:|---:|---:|---:|---:|---:|']
            for role,cost in sorted(costs.items()):
                text.append('| '+role+' | '+' | '.join(str(cost[k]) for k in ('requests','scms','input_tokens','output_tokens'))+' | %.1f | %d |'%(cost['request_seconds'],cost['errors']))
            text += ['', 'B0 requires direct answering. B1 additionally uses the shared synthesis stage; B2 and ALT execute that shared program without another answering request. FULL adds explanation generation and review. Reviewer controls are evaluation overhead. CPU solver costs are not isolated from complete case durations. Development/application work is accounted separately in `usage.json`; these totals must not be summed as independent per-method GPU costs.']
    (result/'RESULTS.md').write_text('\n'.join(text)+'\n')
    source=['# Source-priority evaluation','',summary['source_relevance_definition'],'',
        '| Method | nDCG@5 [95% SCM interval] | Eligible SCMs |','|---|---:|---:|']
    for method,score in summary['source_priority'].items():source.append('| '+method+' | '+ci(score)+' | '+str(score['scms'])+' |')
    source += ['', '| Paired FULL difference | nDCG@5 difference |','|---|---:|']
    for method,score in summary['source_priority_paired'].items():source.append('| versus '+method+' | '+ci(score)+' |')
    eligible=[r for r in json.loads((run/'analysis/test_ranking_scores.json').read_text()) if r['method']=='FULL' and r['ndcg_at_5'] is not None]
    availability=collections.Counter()
    for row in eligible:
        record=json.loads((run/'benchmark'/(row['id']+'.json')).read_text())
        availability['available' if row['ranking_available'] else 'failed_synthesis' if not record.get('model') else 'admitted_but_unavailable']+=1
    source += ['', 'Among the %d eligible SCMs, FULL ranking availability is: %s. These counts separate synthesis rejection from an unavailable ranking after formal admission.'%(len(eligible),json.dumps(dict(availability),sort_keys=True))]
    source += ['', 'The labels describe a potentially relevant structural slice, not a minimal sufficient evidence set, episode desirability or human reading benefit. Factual-value controls can be answered from the known factual states and intervention semantics even when downstream rules retain positive slice labels. FULL can have no ranking when its selected-path contrast is zero even though rule passages explain the invariance. Those cases receive zero if independent relevance labels are positive. Uniform support uses the same paths and structural allocations; with correctly extracted explicit directional statements, its weights can coincide with FULL even when exact functions are unknown. The explicit-rule corpus does not manipulate source reliability; such equality does not demonstrate a benefit from weighting heterogeneous evidence. Application priorities have no independently adjudicated relevance labels and are reported as provisional review priorities only.', '',
        'Controlled FULL computes paths and priorities from the single retained model. Its explanation record includes the family outcome set, but its source ranking is not averaged or bounded across compatible mechanisms. In an underidentified case, a zero contrast under that single assumption can therefore miss evidence relevant to the family uncertainty. This is a limitation of the frozen component, not a robustness guarantee. Application games are computed per retained global model, but this campaign retains only one.']
    (result/'SOURCE_PRIORITY.md').write_text('\n'.join(source)+'\n')
    explain=['# Explanation generation and reviewer quality','',
        'Software creates the outcome/intervention record before prose generation. The LLM uses supplied values, and software assigns fixed sentence IDs before review. Invalid IDs are reviewer failures; unsupported or numerically invalid prose is an explanation failure. A schema-valid reviewer can still be wrong.', '',
        '| Component | Estimate [95% SCM interval] |','|---|---:|']
    for key,value in summary['components'].items():
        if key.startswith(('explanation','reviewer')):explain.append('| '+key+' | '+ci(value)+' |')
    explain += ['', 'Each controlled reviewer probe includes a true factual value, a flipped factual value, an invalid probability interpretation, and an explicit model/reference-dependence statement. Expected labels are withheld from its prompt. These software-defined controls evaluate simple trace fidelity and interpretation, not subtle literary entailment. Numeric checks verify allowed values, declared field/value claims, identifiers and tie qualifications; they are not a complete natural-language theorem prover. The same model generates and reviews prose, so its judgments are dependent. Independent researcher review remains pending unless a separately recorded response says otherwise.']
    confusion=collections.Counter();checks=collections.Counter();format_errors=collections.Counter()
    generated=valid_review=accepted_invalid=controls_run=over_word_limit=0
    conditional_control_matches=conditional_control_total=conditional_false_accepts=conditional_unsupported_total=0
    for case in sorted((run/'benchmark').glob('*.json')):
        record=json.loads(case.read_text())
        if record['split']!='test':continue
        e=record.get('explanation',{});control=record.get('reviewer_controls',{})
        generated+=bool(e.get('sentences'));valid_review+=bool(e.get('review',{}).get('reviewer_valid'))
        accepted_invalid+=bool(e.get('review',{}).get('all_supported')) and not e.get('deterministic_check',{}).get('passed',False)
        # Post-hoc descriptive audits: they never modify frozen primary scores.
        over_word_limit+=sum(len(s['text'].split()) for s in e.get('sentences',[]))>110
        checks.update({x['type'] for x in e.get('deterministic_check',{}).get('errors',[])})
        format_errors.update({a['error'] for a in e.get('generation_attempts',[]) if a.get('error')})
        controls_run+=bool(control.get('review',{}).get('reviewer_valid'))
        verdicts={r['sentence_id']:r['verdict'] for r in control.get('review',{}).get('reviews',[])}
        for ident,expected in control.get('expected',{}).items():
            confusion[(ident,expected,verdicts.get(ident,'missing'))]+=1
            if control.get('review',{}).get('reviewer_valid'):
                conditional_control_total+=1
                conditional_control_matches+=verdicts.get(ident)==expected
                if expected=='unsupported':
                    conditional_unsupported_total+=1
                    conditional_false_accepts+=verdicts.get(ident)=='supported'
    explain += ['', '## Conditional and diagnostic counts', '',
        '%d explanations contain retained prose; %d have valid review IDs; %d control reviews have valid IDs. The primary component table keeps all %d planned SCMs, including unrun stages. In particular, missing reviews are not false acceptances: read that rate together with reviewer-control missingness.'%(generated,valid_review,controls_run,summary['planned_scms']), '',
        'Among ID-valid control reviews only, strict agreement is %d/%d judgments and false acceptance is %d/%d deliberately unsupported judgments. These are secondary descriptive counts conditional on reaching review, with four repeated controls per SCM; they are not independent-sample confidence estimates.'%(conditional_control_matches,conditional_control_total,conditional_false_accepts,conditional_unsupported_total), '',
        '%d explanations were semantically accepted by the same model despite failing deterministic/format checks. This is a disagreement between limited checks, not an independently measured semantic error rate. A post-hoc whitespace word count finds %d explanations above the requested 110-word cap; the frozen displayability code does not enforce that cap and its reported scores are unchanged.'%(accepted_invalid,over_word_limit), '',
        'Final deterministic error types (one count per SCM/type): `'+json.dumps(dict(checks),sort_keys=True)+'`. Generation-attempt format errors (one count per SCM/message): `'+json.dumps(dict(format_errors),sort_keys=True)+'`.', '',
        '| Control ID | Expected verdict | Returned verdict | SCM count |','|---|---|---|---:|']
    for (ident,expected,verdict),count in sorted(confusion.items()):
        explain.append('| '+ident+' | '+expected+' | '+verdict+' | '+str(count)+' |')
    explain += ['', 'The expected verdicts distinguish an unsupported claim from an unverifiable one. Treating the invalid probability interpretation as unverifiable reduces strict accuracy but does not count as falsely accepting it. These controls are repeated measurements, not four independent samples per SCM.', '',
        'The conditional Five Kings explanation is rejected: six actual sentences exceed the four-sentence request, and numerical claim keys do not exist in the structured record. Its reviewer covers every actual sentence ID and marks all text supported. It scores 3/4 on the separate controls, with no false acceptance. See `application_explanation_audit.json`; source entailment remains unadjudicated.']
    (result/'EXPLANATION_REPORT.md').write_text('\n'.join(explain)+'\n')


def application_reports(root,case='five_kings'):
    root,run,result=paths(root)
    record_path=application_record(root,run) if case=='five_kings' else run/'application'/case/'final.json'
    app=json.loads(record_path.read_text());principal=app['records'][0]
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
        app['case']['outcome'],'',app['source_review'],'',app.get('construction_context',{}).get('scope','Fresh source-derived construction.'),'',
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
    audit += ['', '## Construction and mechanism limits', '',
        '%d of %d retained variables are parentless scope boundaries; their upstream causes are unexplained. Only %d retained equations connect endogenous variables. The ten-node reporting target is %s. No nodes are added to meet it.'%(sum(not n['parents'] for n in model['nodes']),len(nodes),sum(bool(n['parents']) for n in model['nodes']),'met' if len(nodes)>=10 else 'not met'), '',
        'The fresh source-construction attempt failed and remains separately recorded in `development_audit.json`. Conditional refinement does not demonstrate fresh concept or dependency discovery. Its literal-operand parser recovery preserved an already generated equality predicate and category value; it supplied no story function.', '',
        'Functionally distinct retained interpretations: %d. %s'%(len(app['records']),'A single interpretation cannot establish robust agreement across interpretations. The apparent singleton outcome sets below are single-hypothesis consequences, not source identification.' if len(app['records'])==1 else 'Agreement is limited to the retained, bounded candidate set.'), '',
        'Displayed figure mechanism summaries are derived from actual behavior. Original generated descriptions/short labels remain in the records; an upstream causal phrase attached to a retracted constant boundary is not displayed as an operative mechanism.']
    inspection=result/'source_inspection.json'
    variant=app.get('construction_context',{}).get('variant','fresh')
    flagged_items=[]
    if inspection.exists():
        flagged=json.loads(inspection.read_text())
        audit += ['', '## Targeted inspection flags', '', flagged['review_type'], '', flagged['model_policy'], '']
        for item in flagged['items']:
            if item.get('variant','fresh')==variant and item['node'] in nodes:
                flagged_items.append(item)
                audit += ['- **'+item['id']+' / '+item['node']+'**: '+item['observation']+' '+item['unresolved_question']]
    (result/(case+'_APPLICATION_AUDIT.md')).write_text('\n'.join(audit)+'\n')
    path=['# '+app['case']['name']+': path-coalition behavior','',
        'Paths are shared-edge coalition players with explicit parent references. Edge union activates a shared edge once; allocations are neither independent event effects nor natural path-specific effects. Cross-model comparisons align the same node meanings and path sequences. The separately labeled path-set sensitivity changes the player collection and therefore the estimand.','',
        '| Model | Coalition outcome histogram | All paths required | Substitute path sets | Negative marginals | Allocation vector |','|---|---|---|---|---:|---|']
    for record in app['records']:
        a=record['attribution'];path.append('| '+record['model']['id']+' | `'+json.dumps(a['coalition_histogram'])+'` | '+str(a['all_paths_required'])+' | '+str(a['substitute_path_sets'])+' | '+str(a['negative_marginals'])+' | `'+str([round(x,5) for x in a['phi']])+'` |')
    path += ['', '## Principal evidence-weighted paths','', '| Path | Node sequence | Signed allocation | Weakest directional support |','|---|---|---:|---:|']
    for p in principal['evidence_priority']['paths']:
        path.append('| '+p['path_id']+' | '+' → '.join(p['nodes'])+' | %.6f | %.2f |'%(p['signed_contribution'],p['evidence_support']))
    path += ['', 'Ranking status: **'+('available, provisional automated evidence assessment' if principal['ranking_available'] else 'unavailable: every evidence-weighted priority is zero')+'**.', '',
        'High-influence, weak-evidence paths remain visible in the table; zero evidence weights are never raised to create an ordering. Equal allocations are a model consequence, not automatically an informative explanation. In particular, unanimity and substitutable-path games can both have equal Shapley shares, so their coalition distributions must also be inspected.', '',
        '## Reference and path selection sensitivity','', '| Scenario | Baseline | Full | Coalition histogram | All selected paths required | Shares |','|---|---:|---:|---|---|---|']
    for label,a in [('declared',principal['attribution'])]+list(principal['reference_sensitivity'].items())+list(principal['path_selection_sensitivity'].items()):
        path.append('| '+label+' | '+str(a['baseline'])+' | '+str(a['full'])+' | `'+json.dumps(a['coalition_histogram'])+'` | '+str(a['all_paths_required'])+' | `'+str([round(v,5) for v in a['phi']])+'` |')
    path += ['', 'Factual-null and domain-endpoint references are explicit sensitivity checks, not necessarily meaningful alternative histories. Restricting the player set changes the estimand. A full selected-path coalition need not cover every explanatory route in a larger graph.', '',
        'The factual-null and domain-endpoint edge-reference assignments are '+('identical in this retained model. Their zero allocations are the same null-contrast result, not two distinct robustness scenarios. Only the declared versus null reference assignments differ here.' if principal['reference_sensitivity']['factual_null']['references']==principal['reference_sensitivity']['domain_endpoint_stress']['references'] else 'different in this retained model; their recorded values define each contrast.')+' No additional reference history was selected after inspecting allocations.', '',
        'Principal minimal full-outcome coalitions: `'+json.dumps(principal['attribution']['minimal_full_outcome_coalitions'])+'`. Pair-interaction range: `'+str(principal['attribution']['pair_interaction_range'])+'`.', '',
        '## Aligned path-set sensitivity', '', '| Shared node sequence | Full collection share | Four-path collection share |','|---|---:|---:|']
    four=select_paths(scm,maximum=4)['paths'];four_game=principal['path_selection_sensitivity']['four_paths']
    for i,sequence in enumerate(principal['selection']['paths']):
        if sequence in four:
            path.append('| '+' → '.join(sequence)+' | %.6f | %.6f |'%(principal['attribution']['phi'][i],four_game['phi'][four.index(sequence)]))
    path += ['', 'These comparisons match the same node sequences within the fixed model. Changing the collection also changes which edges are coalition-controlled; edges outside the selected union retain their normal mechanisms. Shared-edge activation can consequently change an allocation or its sign without changing an equation. This sensitivity is a property of the defined coalition estimand, not a discovery that a narrative event changes historical causal responsibility.', '',
        'Edges outside the four-path union: `'+json.dumps(sorted(set(scm.graph.edges)-{e for p in four for e in zip(p,p[1:])}))+'`. The four-path game has no substitute full-outcome coalition and requires all its players. The scout path bundles a needed downstream edge even when the scout input itself is screened off by another active parent. This explains why a positive bundled-path allocation need not imply a positive event effect.', '',
        'A negative allocation concerns coalition contexts. It need not equal the effect of removing that event in the factual world. The intervention table supplies that distinct event-effect diagnostic. Neither quantity is a probability.', '',
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
    if flagged_items:
        packet_text += ['', 'Additional flags in `source_inspection.json`: '+', '.join(i['id'] for i in flagged_items)+'. These targeted assistant observations are not completed independent review.']
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
        'source_review':app['source_review'],'construction_context':app.get('construction_context',{}),
        'scope_boundaries':sum(not n['parents'] for n in model['nodes']),
        'substantive_connected_functions':sum(bool(n['parents']) for n in model['nodes']),
        'multiple_interpretations_available':len(app['records'])>1,'source_robustness_established':False,
        'explanation_failure':app['explanation']['explanation_failure'],'reviewer_failure':app['explanation']['reviewer_failure']})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--case',default='five_kings');p.add_argument('--application-only',action='store_true');a=p.parse_args()
    if not a.application_only:benchmark_reports(a.root)
    application_reports(a.root,a.case)
