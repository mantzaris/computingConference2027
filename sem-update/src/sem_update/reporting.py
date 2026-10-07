"""Evidence-first reporting. No author approval or unexecuted results implied."""
import csv
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from .runtime import PROJECT,artifact_root,read_json,atomic_json,file_hash,source_state,Ledger,verify_artifacts

def llm_edit_failures(edits):
    """Audit the frozen output contract; never reinterpret or repair proposals."""
    reasons,errors,edge_counts=Counter(),Counter(),Counter()
    records=[]
    for row in edits.to_dict('records'):
        path=artifact_root()/'runs'/row['run_id']/'selection.json'
        selection=read_json(path)
        rejections=[r for step in selection['edits'] for r in step['proposal_rejections']]
        for rejection in rejections:
            reasons[rejection['reason']]+=1
            edge_counts[str(len(rejection['graph']['edges']))]+=1
        for generation in sorted(path.parent.glob('llm-edit-*.json')):
            for attempt in read_json(generation)['records']:
                if not attempt['valid']:
                    errors[attempt['error']]+=1
        records.append({'run_id':row['run_id'],'selection_sha256':file_hash(path),
            'initial_edge_count':len(selection['candidates'][selection['initial']]['graph']['edges']),
            'newly_evaluated_candidates':sum(len(e['evaluated']) for e in selection['edits']),
            'accepted_edits':sum(e['accepted'] for e in selection['edits']),
            'returned_initial_graph':selection['selected']==selection['initial']})
    audit={'runs':records,'rejection_reasons':dict(reasons),'invalid_attempt_errors':dict(errors),
           'rejected_graph_edge_counts':dict(edge_counts),
           'interpretation':'Full edited DAG required by the frozen prompt; one-edge outputs are not applied as edit commands. '
           'The numeric incumbent edge representation differs from requested V-prefixed output IDs. '
           'This interface and model instruction-following failure limits the CauScientist-inspired adaptation; '
           'no post-test prompt tuning or inferred replacement proposals were executed.'}
    atomic_json(PROJECT/'results/curated/llm_edit_failure_audit.json',audit)
    return audit

def cost_table(core):
    columns=['candidate_count','canonical_optimizer_updates','optimizer_updates','unique_parent_sets',
             'new_parent_sets','canonical_fit_seconds','wall_seconds','method_component_seconds']
    rows=[]
    for method in ('fixed','random','diagnostic'):
        group=core[core.method==method]
        for column in columns:
            values=group[column]
            rows.append({'method':method,'quantity':column,'paired_conditions':len(group),
                'independent_scms':len(group[['d','family','seed']].drop_duplicates()),
                'mean':values.mean(),'median':values.median(),'minimum':values.min(),'maximum':values.max()})
    table=pd.DataFrame(rows)
    table.to_csv(PROJECT/'results/curated/achieved_cost_summary.csv',index=False)
    return table

def endpoint_tables(frame):
    """Present the already frozen endpoints separately, retaining paired SCMs."""
    from .evaluation import cluster_interval
    selected=frame[frame.stage=='selected']
    groups=['study','d','family','budget','corruption','metadata_variant','method','endpoint']
    selected.groupby(groups,dropna=False).agg(
        independent_scms=('seed','nunique'),sw1_mean=('sw1','mean'),sw1_sd=('sw1','std'),
        energy_mean=('energy','mean'),mean_effect_rmse=('mean_effect_rmse','mean'),
        coverage_90=('coverage_90','mean'),width_90=('width_90','mean')).reset_index().to_csv(
            PROJECT/'results/curated/endpoint_summary.csv',index=False)
    core=selected[(selected.study=='controlled')&(selected.corruption>0)]
    keys=['study','d','family','seed','budget','corruption','metadata_variant']
    rows=[]
    for endpoint in ('T1','T2','T3'):
        subset=core[core.endpoint==endpoint]
        for comparator in ('fixed','random'):
            paired=subset[subset.method=='diagnostic'].merge(subset[subset.method==comparator],
                on=keys,suffixes=('_method','_comparison'),validate='one_to_one')
            paired['delta']=paired.sw1_method-paired.sw1_comparison
            rows.append({'endpoint':endpoint,'comparison':'diagnostic - '+comparator,
                         'role':'primary' if endpoint=='T2' else 'secondary descriptive',
                         **cluster_interval(paired)})
    result=pd.DataFrame(rows)
    result.to_csv(PROJECT/'results/curated/endpoint_comparisons.csv',index=False)
    return result

def evidence_report(frame,summary):
    from .evaluation import paired_results
    endpoint_comparisons=endpoint_tables(frame)
    selected=frame[(frame.stage=='selected')&(frame.endpoint=='T2')]
    core=selected[(selected.study=='controlled')&(selected.corruption>0)]
    independent=core[['d','family','seed']].drop_duplicates()
    pairs=paired_results(frame[(frame.study=='controlled')&(frame.corruption>0)])
    counts=pairs.outcome.value_counts().to_dict()
    before=paired_results(frame[(frame.study=='controlled')&(frame.corruption>0)],stage='before_audit')
    costs=cost_table(core)
    ledger=Ledger().snapshot()
    hardware=read_json(PROJECT/'results/curated/hardware.json')
    protocol=read_json(PROJECT/'results/curated/frozen_protocol.json')
    lines=['# Evidence report for Alex’s review','',
           'This report summarizes executed computations. Human scientific review and manuscript approval remain pending.','',
           f"Primary controlled study: {len(independent)} independent SCMs; graph sizes {sorted(independent.d.unique().tolist())}; "
           'three mechanism families; two non-test intervention budgets and two nominal corruption levels. '
           'Uncorrupted heteroscedastic controls are reported separately.','',
           '## Primary paired T2 prediction comparisons','']
    claims=[]
    for row in summary.to_dict('records'):
        lines.append(f"- {row['study']}, {row['comparison']}: mean ΔSW₁ {row['mean']:+.5f}; "
                     f"95% paired cluster bootstrap interval [{row['low']:+.5f}, {row['high']:+.5f}]; "
                     f"{int(row['independent_scms'])} independent SCMs. Negative favors diagnostic repair.")
        status='supported' if row['high']<0 else ('unsupported' if row['low']>0 else 'mixed')
        claims.append({'claim':row['comparison']+' reduces T2 SW1 in '+row['study'],'status':status,
                       'evidence':'results/curated/summary.csv; metrics.csv; run_index.json',
                       'qualification':'Measured scope only; modest cluster count; human interpretation pending'})
    lines+=['','Intervals quantify variation across SCMs, retaining budgets, corruptions and metadata variants within clusters. '
            'They are distinct from predictive quantiles in response plots. No unadjusted multiple-comparison p-values are reported.','',
            '## Distinct generalization endpoints','',
            'T1 uses new samples at the fitting setting, T2 uses a new setting on seen targets, and T3 uses unseen targets. '
            'The following T1/T3 comparisons are descriptive secondary results, not replacements for the frozen T2 endpoint. '
            'All endpoint, family, graph-size and budget summaries remain separate in endpoint_summary.csv.','']
    for row in endpoint_comparisons[endpoint_comparisons.endpoint!='T2'].to_dict('records'):
        lines.append(f"- {row['endpoint']}, {row['comparison']}: mean ΔSW₁ {row['mean']:+.5f}; "
                     f"95% paired SCM interval [{row['low']:+.5f}, {row['high']:+.5f}]; "
                     f"n={int(row['independent_scms'])}.")
    lines+=['',
            '## Repair reliability','',f"After-audit counts across paired controlled conditions: {counts}. "
            'These conditions are not independent replications. Harm uses max(0.001, 5% of initial SW₁); beneficial uses the symmetric decrease. '
            'All individual deltas are in paired_repairs.csv. Before-audit results remain in metrics.csv.',
            f"Before-audit counts: {before.outcome.value_counts().to_dict()}. "
            'The audit did not reduce the observed number of harmful T2 repairs in this matrix. '
            'Passing its independent in-setting check does not guarantee safe extrapolation.','',
            '## Local LLM and real case','']
    proposals=[]
    proposal_rows=[]
    for p in sorted((PROJECT/'results/curated/proposals').glob('*.json')):
        generation=read_json(p)
        records=generation['records']
        proposals.extend(records)
        proposal_rows.append({'condition':p.stem,'attempts':len(records),
            'invalid_attempts':sum(not r['valid'] for r in records),
            'valid_proposals':sum(r['valid'] for r in records),
            'unique_valid_graphs':len({str(g) for r in records if r['valid'] for g in r['graphs']}),
            'data_only_fallback':not any(r['valid'] for r in records),
            'stage_seconds':generation['stage_seconds'],
            'generated_tokens':sum(r['stats']['output_tokens'] for r in records),
            'peak_vram_bytes':max(r['stats']['peak_vram_bytes'] for r in records)})
    pd.DataFrame(proposal_rows).to_csv(PROJECT/'results/curated/llm_generation_audit.csv',index=False)
    lines.append(f"Initialization generations: {len(proposals)} recorded attempts, {sum(not p['valid'] for p in proposals)} invalid. "
                 'The pinned local Qwen model, exact revision, seeds, token counts and raw-output hashes are recorded. '
                 'LLM-edit is a CauScientist-inspired continuous-flow adaptation with search feedback and rejection memory, not published reproduction scores.')
    lines.append(f"Conditions with no valid LLM start: {sum(r['data_only_fallback'] for r in proposal_rows)} of {len(proposal_rows)}. "
                 'The predeclared data-only initializer remains available. See llm_generation_audit.csv; '
                 'invalid and duplicate attempts are not relabeled as successful generations. '
                 'Metadata comparisons include both proposal validity and fallback behavior; '
                 'their prediction differences do not isolate the quality of accepted semantic graph knowledge.')
    edits=selected[selected.method=='llm_edit'][['run_id','study','seed','metadata_variant','candidate_count',
        'llm_edit_attempts','llm_edit_invalid_attempts','llm_edit_rejected_graphs','wall_seconds','peak_vram_bytes']]
    edits.to_csv(PROJECT/'results/curated/llm_edit_audit.csv',index=False)
    edit_audit=llm_edit_failures(edits)
    lines.append(f"LLM-edit stage: {int(edits.llm_edit_attempts.sum())} actual generation attempts, "
                 f"{int(edits.llm_edit_invalid_attempts.sum())} invalid attempts and "
                 f"{int(edits.llm_edit_rejected_graphs.sum())} rejected proposed graphs across {len(edits)} conditions. "
                 'Attempt and proposed-graph counts are different units; per-run records are in llm_edit_audit.csv.')
    lines.append(f"All {len(edits)} LLM-edit conditions returned the initial graph, with "
                 f"{sum(r['newly_evaluated_candidates'] for r in edit_audit['runs'])} admissible new candidates evaluated. "
                 f"Rejected parsed graphs by reason: {edit_audit['rejection_reasons']}; "
                 f"their edge counts: {edit_audit['rejected_graph_edge_counts']}. "
                 'Every rejected parsed proposal contained one edge although the prompt requested the complete edited DAG. '
                 'Invalid generations violated assigned-root constraints. The incumbent uses numeric node indices while '
                 'the requested output uses V-prefixed IDs, adding an avoidable interface burden. '
                 'These are actual model outputs, preserved without post-test reinterpretation or prompt repair. '
                 'This failed adaptation is not evidence against CauScientist or evidence of effective LLM editing. '
                 'The semantic comparison is therefore effectively against fixed initial graphs. '
                 'A stronger edit-command interface requires a new prospectively frozen study, not a favorable retry here. '
                 'See llm_edit_failure_audit.json.')
    for name,title in [('metadata_comparisons.csv','Semantic metadata controls'),
                       ('ablation_comparisons.csv','Restricted diagnostic ablations'),
                       ('flow_additive_comparison.csv','Flow versus additive mechanisms')]:
        table=pd.read_csv(PROJECT/'results/curated'/name)
        lines+=['',title+':','']
        for row in table.to_dict('records'):
            lines.append(f"- {row['comparison']}: ΔSW₁ {row['mean']:+.5f}, "
                         f"95% paired SCM interval [{row['low']:+.5f}, {row['high']:+.5f}], "
                         f"n={int(row['independent_scms'])}. Negative favors the first named method.")
            status='supported' if row['high']<0 else ('unsupported' if row['low']>0 else 'mixed')
            claims.append({'claim':row['comparison']+' is negative','status':status,
                           'evidence':'results/curated/'+name,
                           'qualification':'Prespecified secondary comparison; descriptive interval; no multiplicity-adjusted significance claim'})
    uncorrupted=pd.read_csv(PROJECT/'results/curated/uncorrupted_repairs.csv')
    lines+=['',f"Uncorrupted starting-graph control: {uncorrupted.outcome.value_counts().to_dict()} "
            'across the ten paired budget conditions from five heteroscedastic SCMs. '
            'A correct structural starting graph can still receive a predictively harmful edit.']
    real=selected[selected.study=='real']
    if len(real):
        lines+=['','Real T2 results (one apparatus; no real unseen-target claim):','']
        for row in real.to_dict('records'):
            lines.append(f"- {row['method']} / {row['metadata_variant']}: SW₁ {row['sw1']:.5f}; run `{row['run_id']}`.")
        comparison=pd.read_csv(PROJECT/'results/curated/real_block_comparisons.csv')
        r=comparison[(comparison.metadata_variant=='coherent')&(comparison.comparison=='diagnostic - fixed')].iloc[0]
        lines.append(f"Coherent diagnostic − fixed: ΔSW₁ {r.delta:+.5f}, conditional block interval "
                     f"[{r.conditional_block_low:+.5f}, {r.conditional_block_high:+.5f}]. "
                     'Repair worsened the primary real endpoint; the controlled-corruption gain did not generalize to this case.')
    lines+=['','Actual RGB strong regimes are held out as new settings. Raw ADC/PWM data are dequantized; '
            'all relevant included-sensor settings are fixed. Acquisition blocks and gaps are recorded. '
            'Residual serial dependence, shared electronics, imperfect measurement models and extrapolation limit causal interpretation. '
            'Conditional intervals resample ten-row acquisition blocks within each strong regime (200 replicates); '
            'models and generated samples are fixed. They are in real_block_intervals.csv and real_block_comparisons.csv. '
            'No independent-apparatus confidence interval is claimed. '
            'The sample budget counts 6,656 randomized reference rows plus 1,200 additional mid-RGB rows: '
            '7,856 non-test experimental observations. B=400 means rows per additional target regime, not the total real budget.','',
            '## Computational validation and failures','',
            f"Device: {hardware['device']}; driver {hardware['nvidia_smi'].split(',')[2].strip()}; "
            f"PyTorch {hardware['torch']}; CUDA runtime {hardware['cuda_runtime']}; actual CUDA gradients recorded. "
            f"Union of recorded reserved-device intervals: {ledger['used_seconds']/3600:.3f} hours (cap {ledger['cap_seconds']/3600:g}).",
            '',f"Recorded failed jobs: {sum(r['status']=='failed' for r in ledger['jobs'])}. "
            'Initial test-runner setup and development DCDI adapter failures are retained, not converted to zero error or silently omitted. '
            'Inspect dcdi_development.json and run_index.json for baseline convergence and any threshold projection.','',
            '## Limits and interpretation','',
            '- Finite intervention data and flexible flows do not identify every edge. LLM suggestions and residual diagnostics are fallible.',
            '- Node-local caching changes achieved compute. Candidate counts, actual and canonical optimizer updates, parent-set fits, measured times and memory are reported separately. Elapsed times depend on cache execution order and concurrent GPU jobs.',
            '- The equal maximum of 12 candidate DAGs and identical stopping rule do not equalize achieved fitting work. No equal-optimizer-budget or compute-efficiency superiority is established.',
            '- Mean-effect errors use independent test Monte Carlo reference means; these are finite-sample estimates, not exact analytic effects.',
            '- No optimization-repeat graph stability or real individual counterfactual study is claimed.',
            '- General LLM-guided graph editing, flow SCMs and intervention-aware likelihoods are established prior work; novelty wording requires human review.',
            '- Publication, registration, indexing and acceptance have not been performed or guaranteed.','',
            '## Artifacts and reproduction','',
            'Evidence is stored under SEM_UPDATE_ARTIFACT_ROOT (default sem-update/.artifacts). '
            'Run records, model checkpoints, generated samples, raw LLM outputs and failure traces remain there. '
            'Compact metrics, response tables, graph JSON and vector figures are curated under results/curated and paper/figures. '
            'figure_manifest.json identifies the plotting inputs and checksums. See README.md and docs/status.md for tested commands and remaining work.']
    quantities=costs.set_index(['method','quantity'])['mean']
    cost_note=(f"Achieved controlled costs per paired condition: diagnostic versus random used "
               f"{quantities['diagnostic','candidate_count']:.2f} versus {quantities['random','candidate_count']:.2f} DAGs and "
               f"{quantities['diagnostic','canonical_optimizer_updates']:.1f} versus "
               f"{quantities['random','canonical_optimizer_updates']:.1f} canonical optimizer updates. "
               'The latter counts each required node/parent-set once irrespective of cross-method cache hits. '
               'Actual cached updates and timing are in achieved_cost_summary.csv; shared-cache execution order prevents treating wall time as an isolated-method benchmark.')
    where=lines.index('## Computational validation and failures')
    lines[where:where]=['## Achieved fitting budget','',cost_note,'']
    adverse=pairs[pairs.outcome=='harmful'].sort_values(['delta','run_id_method'],ascending=[False,True])
    if len(adverse):
        row=adverse.iloc[0]
        initial=frame[(frame.run_id==row.run_id_method)&(frame.endpoint=='T2')&(frame.stage=='initial')].iloc[0]
        returned=selected[selected.run_id==row.run_id_method].iloc[0]
        where=lines.index('## Local LLM and real case')
        lines[where:where]=[f"Largest adverse example: `{row.run_id_method}`. T2 SW₁ rose from "
            f"{initial.sw1:.6f} to {returned.sw1:.6f} (Δ {row.delta:+.6f}) despite passing the audit. "
            f"SHD changed from {initial.shd:g} to {returned.shd:g}. Figure F2_adverse shows the accepted reversal; "
            'an improvement in graph distance need not improve finite-sample intervention prediction.','']
    discoveries=[r['dcdi_discovery'] for r in read_json(PROJECT/'results/curated/run_index.json')['runs'] if r['method']=='dcdi']
    memory={'gpu_job_hours':ledger['used_seconds']/3600,
            'torch_peak_allocated_bytes':int(selected.peak_vram_bytes.max()),
            'flow_torch_peak_allocated_bytes':int(selected.flow_peak_vram_bytes.max()),
            'dcdi_torch_peak_allocated_bytes':max(r['peak_vram_bytes'] for r in discoveries),
            'method_peak_definition':'Maximum PyTorch allocated CUDA bytes, not total device occupancy',
            'ledger_status_counts':pd.Series([r['status'] for r in ledger['jobs']]).value_counts().to_dict()}
    utilization=artifact_root()/'logs/gpu_utilization.csv'
    if utilization.exists():
        samples=pd.read_csv(utilization,header=None,names=['timestamp','job','utilization_percent','memory_mib','power_w'])
        memory.update(sampled_whole_device_peak_mib=float(samples.memory_mib.max()),
                      device_sample_count=len(samples),device_samples_sha256=file_hash(utilization),
                      device_sampling_note='Approximately 10-second samples per active ledger interval; shared-device occupancy includes CUDA contexts')
    atomic_json(PROJECT/'results/curated/runtime_memory_summary.json',memory)
    lines.extend(['',f"Recorded maximum PyTorch allocation: {memory['torch_peak_allocated_bytes']/1024**3:.3f} GiB; "
                  f"flow-stage maximum {memory['flow_torch_peak_allocated_bytes']/1024**3:.3f} GiB. "
                  'Sampled whole-device occupancy is reported separately in runtime_memory_summary.json; '
                  'it includes contexts and concurrent processes and is not interchangeable with tensor allocation.'])
    baseline_note=(f"DCDI benchmark fits: {len(discoveries)}; "
                   f"{sum(r['converged'] for r in discoveries)} met the strict normalized constraint; "
                   f"{sum(bool(r['projection_removed_edges']) for r in discoveries)} required edge removal for the declared DAG/indegree projection. "
                   'Update-cap results remain included and explicitly flagged. This is the documented official-network CUDA adaptation, not an exact published-score reproduction.')
    where=lines.index('## Limits and interpretation')
    lines[where:where]=[baseline_note,'']
    (PROJECT/'docs/evidence_report.md').write_text('\n'.join(lines)+'\n')
    claims.extend([
        {'claim':'The one-time audit reduces harmful T2 repairs in the controlled matrix','status':'unsupported','evidence':'results/curated/F5_harm_counts.csv','qualification':'10 harmful conditions both before and after audit; no safety guarantee'},
        {'claim':'Diagnostic repair improves the coherent real-case T2 endpoint over fixed graphs','status':'unsupported','evidence':'results/curated/real_block_comparisons.csv','qualification':'Positive error difference; conditional one-apparatus interval'},
        {'claim':'This LLM-edit adaptation executes effective graph edits','status':'unsupported','evidence':'results/curated/llm_edit_failure_audit.json','qualification':'No admissible new candidates; all returned initial graphs; not a faithful CauScientist reproduction'},
        {'claim':'Diagnostic repair is superior at equal achieved optimizer cost','status':'untested','evidence':'results/curated/achieved_cost_summary.csv','qualification':'Equal maximum candidate counts only; achieved canonical updates differ'},
        {'claim':'Correct SCM intervention, masks, inverse/Jacobian and canonical cache behavior','status':'supported','evidence':'results/curated/correctness.json; tests/','qualification':'Tested cases and actual CUDA smoke, not a universal proof'},
        {'claim':'Generated DAGs establish physical causal truth','status':'unsupported','evidence':'docs/novelty.md; docs/dataset_audit.md','qualification':'Not implied by the design or predictions'},
        {'claim':'Individual counterfactual accuracy on real data','status':'untested','evidence':'none','qualification':'Only optional analytic software checks exist'},
        {'claim':'Graph edge stability across optimization seeds','status':'untested','evidence':'none','qualification':'No stability thickness or posterior edge probability is plotted'},
        {'claim':'Human scientific approval or guaranteed acceptance/indexing','status':'unsupported','evidence':'docs/venue.md','qualification':'Human review pending; no submission or guarantee'}])
    pd.DataFrame(claims).to_csv(PROJECT/'results/curated/claim_ledger.csv',index=False)
    audit=verify_artifacts()
    atomic_json(PROJECT/'results/curated/provenance.json',{'source':source_state(),'hardware':hardware,
                'protocol_hash':protocol['protocol_hash'],'ledger':ledger,
                'artifact_manifest':'.artifacts/artifact_manifest.json','artifact_inventory':audit,
                'model_revision':read_json(PROJECT/'results/curated/llm_revision.json'),
                'data_audit_sha256':file_hash(PROJECT/'results/curated/dataset_audit.json'),
                'split_audit_sha256':file_hash(PROJECT/'results/curated/real_split_audit.json'),
                'human_scientific_review':'pending','run_status':'evaluation and figure export complete'})
