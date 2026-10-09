"""Generate factual tables and an evidence draft from executed application outputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from app_runtime import ROOT,PHASE,RESULTS,read_json,atomic_json,file_hash,snapshot

MAIN=['M0','M1','M2','M3','M4','M5'];CONTROLS=['fixed','random']

def main():
    s=pd.read_csv(RESULTS/'summary.csv').set_index('method');c=pd.read_csv(RESULTS/'costs.csv').set_index('method')
    harm=pd.read_csv(RESULTS/'reliability.csv').set_index('method');obs=pd.read_csv(RESULTS/'observed_effects.csv')
    effects=pd.read_csv(RESULTS/'effects.csv');acoustic=pd.read_csv(RESULTS/'acoustic.csv');decisions=pd.read_csv(RESULTS/'decisions.csv')
    graphs=read_json(RESULTS/'graphs.json');audit=read_json(RESULTS/'execution_audit.json');llm=read_json(RESULTS/'llm_prior.json')
    book=snapshot();atomic_json(RESULTS/'compute.json',{k:v for k,v in book.items() if k!='jobs'})
    main_record=read_json(ROOT/'runs/main/frozen.json');disc=main_record['methods']['M2']['discovery']
    best=min(MAIN,key=lambda m:s.loc[m,'effect_error']);best_all=min(MAIN+CONTROLS,key=lambda m:s.loc[m,'effect_error'])
    table=['| Method | Primary contrast error [95% CI] | Joint SW1 | Coverage 90% | Charged s | Prediction s |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    latex=[r'\begin{tabular}{lrrrr}',r'\toprule',r'Method & Effect error & Joint SW & Fit/select s & Predict s \\',r'\midrule']
    for m in MAIN+CONTROLS:
        r=s.loc[m];cost=c.loc[m]
        table.append(f'| {m} | {r.effect_error:.4f} [{r.ci_low:.4f}, {r.ci_high:.4f}] | {r.joint_sw1:.4f} | {r.coverage90:.1%} | {cost.logical_seconds:.2f} | {cost.prediction_seconds:.2f} |')
        latex.append(f'{m} & {r.effect_error:.4f} & {r.joint_sw1:.4f} & {cost.logical_seconds:.2f} & {cost.prediction_seconds:.2f} '+r'\\')
    latex.extend([r'\bottomrule',r'\end{tabular}']);(PHASE/'comparison.tex').write_text('\n'.join(latex)+'\n')
    (RESULTS/'comparison.md').write_text('\n'.join(table)+'\n')
    def contrast(run,outcome):
        r=obs[(obs.run==run)&(obs.outcome==outcome)].iloc[0]
        return f'{r.effect:+.4g} {r.unit} (95% block CI {r.ci_low:+.4g} to {r.ci_high:+.4g}; {int(r.n_low)}/{int(r.n_high)} low/high assignments)'
    findings=[
        'At hatch 0° and outlet duty 0.01, changing inlet duty 0.01→1 changes inlet current by '+contrast('validate_load_in','current_in')+' and upwind-relative pressure by '+contrast('validate_load_in','pressure_upwind')+'.',
        'At hatch 0° and inlet duty 0.01, changing outlet duty 0.01→1 changes outlet current by '+contrast('validate_load_out','current_out')+' and downwind-relative pressure by '+contrast('validate_load_out','pressure_downwind')+'.',
        'At inlet duty 1 and outlet duty 0.01, opening the hatch 0→45° changes upwind-relative pressure by '+contrast('validate_hatch_rpms','pressure_upwind')+' and inlet current by '+contrast('validate_hatch_rpms','current_in')+'.']
    a=acoustic[acoustic.run=='validate_load_out_mic'].iloc[0]
    findings.append(f'In the separate outlet-command acoustic experiment (10-second wait, hatch 0°, inlet duty 0.01), microphone-circuit amplitude changes by {a.effect_signal_volts:+.4g} V (95% block CI {a.ci_low:+.4g} to {a.ci_high:+.4g}). This is not dB SPL; no generative acoustic prediction was fitted across incompatible OSR settings.')
    initial=set(map(tuple,graphs['M3']['initial']['edges']));selected=set(map(tuple,graphs['M3']['selected']['graph']['edges']))
    freq=pd.read_csv(RESULTS/'edge_frequency.csv');unstable=sum(float(freq[(freq.source==a)&(freq.target==b)].selection_frequency.iloc[0])<.6 for a,b in selected)
    reliability=['| Method | Harmful tested regimes / 5 | Max SW deterioration | Returned G0 |','| --- | ---: | ---: | --- |']
    for m in ['M3','M4','M5','random']:
        r=harm.loc[m];reliability.append(f'| {m} | {int(r.harmful_runs)}/5 | {r.max_sw_deterioration:.4f} | {r.retained_initial} |')
    matched=[];allmetrics=pd.read_csv(ROOT/'reports/all_metrics.csv')
    for axis,budgets in read_json(RESULTS/'protocol.json')['config']['checkpoints'].items():
        for budget in budgets:
            names=[f'checkpoint_{p}_{axis}_{budget:g}' for p in ('diagnostic','random')]
            if not all(n in s.index for n in names):
                matched.append({'axis':axis,'limit':budget,'paired_coverage':False});continue
            matched.append({'axis':axis,'limit':budget,'paired_coverage':True,
                'diagnostic_error':float(s.loc[names[0],'effect_error']),'random_error':float(s.loc[names[1],'effect_error']),
                'diagnostic_updates':int(c.loc[names[0],'fitting_updates']),'random_updates':int(c.loc[names[1],'fitting_updates']),
                'diagnostic_charged_seconds':float(c.loc[names[0],'logical_seconds']),'random_charged_seconds':float(c.loc[names[1],'logical_seconds'])})
    pd.DataFrame(matched).to_csv(RESULTS/'matched_compute.csv',index=False,float_format='%.8g')
    decision_summary=[]
    for method,group in decisions.groupby('method'):
        feasible=group.measured_feasible_arms>0;valid=group.feasible_current_regret_a.notna()
        decision_summary.append({'method':method,'recorded_decisions':len(group),'violations':int(group.constraint_violation.sum()),
            'decisions_with_measured_feasible_arm':int(feasible.sum()),'valid_regret_comparisons':int(valid.sum()),
            'mean_feasible_regret_a':float(group.loc[valid,'feasible_current_regret_a'].mean()) if valid.any() else None})
    pd.DataFrame(decision_summary).to_csv(RESULTS/'decision_summary.csv',index=False,float_format='%.8g')
    refits=[]
    for m in ['M1','fixed','M3','M4','M5']:
        names=[f'refit{i}_{m}' for i in range(1,6)];values=s.loc[names,'effect_error'].to_numpy()
        refits.append({'method':m,'grouped_training_refits':5,'error_mean':float(values.mean()),'error_sd':float(values.std(ddof=1)),
                       'error_min':float(values.min()),'error_max':float(values.max())})
    pd.DataFrame(refits).to_csv(RESULTS/'refit_sensitivity.csv',index=False,float_format='%.8g')
    semantic=[]
    for m in ['M1','fixed','M3','M4','M5','random']:
        if 'semantic_'+m in s.index:
            semantic.append({'method':m,'training_prior_error':float(s.loc[m,'effect_error']),
                'semantic_prior_error':float(s.loc['semantic_'+m,'effect_error']),
                'error_change':float(s.loc['semantic_'+m,'effect_error']-s.loc[m,'effect_error']),
                'semantic_full_logical_seconds':float(c.loc['semantic_'+m,'logical_seconds']+llm['seconds']),
                'llm_seconds_charged':llm['seconds']})
    pd.DataFrame(semantic).to_csv(RESULTS/'semantic_comparison.csv',index=False,float_format='%.8g')
    subset=effects[(effects.method=='M3')&(effects.run.isin([r['run'] for r in read_json(RESULTS/'protocol.json')['final_design'] if r['panel']=='primary']))].copy()
    manifest=read_json(ROOT/'data/processed/main/manifest.json');scales=dict(zip(manifest['variables'],manifest['standardization']['std']))
    subset['standardized_error']=[r.absolute_error/scales[r.outcome] for r in subset.itertuples()]
    worst=subset.sort_values(['standardized_error','run','outcome'],ascending=[False,True,True]).iloc[0]
    text=f'''# Executed wind-tunnel application evidence

This separate phase preserves studies ad21e60, 8c452ac and a17a8f7. It evaluates
one wind-tunnel apparatus, not a population of independent physical systems.
Human scientific review remains pending.

## Executed coverage and primary prediction

Eight fitting acquisitions and disjoint early/search/calibration/audit acquisitions
produce {audit['all_main_non_test_rows']:,} non-test observations including the
single preprocessing-only row. Development examined another 14,000 recorded rows.
The primary test contains 699 measurements in five randomized acquisition files,
with three actuator targets and a ten-second post-assignment wait. A separate
three-file panel contains 3,200 measurements at shorter waits. Five grouped
training-run bootstrap refits and one actual local-LLM semantic initialization
were executed. These are repeated analyses of the same apparatus.

**{best} has the lowest observed primary error among the six main methods;
{best_all} has the lowest observed error including fixed/random controls.** The
endpoint is the standardized absolute error of measured randomized changes on
both currents and three ambient-relative pressures, weighted equally by outcome
and actuator. Joint SW1 remains secondary and can be affected by ambient drift.

{chr(10).join(table)}

M2 denotes the capped/projected DCDI-DSF adaptation plus common flows. Prediction
time covers 16 intervention arms × 4,096 draws, excluding checkpoint loading and
disk serialization. Charged times cover fitting/search/selection; preprocessing
and untimed common initialization overhead remain included in the actual device
ledger rather than individual method charges. M0 has no continuous-density
likelihood endpoint.

Intervals resample acquisition files within target and consecutive ten-row blocks
within acquisition. They condition on one apparatus and fixed fitted models/MC
streams. They are not predictive intervals. Four-batch MC errors are in effects.csv;
grouped-refit spread is separate in refit_sensitivity.csv. Formal comparisons use
the four prespecified Holm-adjusted acquisition sign-flip tests in contrasts.csv.
With five acquisitions, these tests cannot establish broad method superiority.

## Measured engineering effects

{chr(10).join('- '+f for f in findings)}

These randomized contrasts support total actuator effects at the stated fixed
nuisance commands. They do not establish direct edges, airflow, power savings,
acoustic SPL or transport to different equipment. Published current calibration
uncertainty is not included in the block intervals.

## Graph, repair reliability and semantic prior

The main M3 process graph has {len(initial)} initial and {len(selected)} returned
edges: {len(selected-initial)} added, {len(initial-selected)} removed. Of its
returned edges, {unstable} appear in fewer than three of five grouped refits.
Selection frequency is conditional algorithmic stability, not causal probability.
The full graph and all M5 components are retained in graphs.json. Ensemble weights
combine complete predicted distributions and are not probabilities of causal truth.

{chr(10).join(reliability)}

These five regime counts concern one selected repair, not five independent repairs.
Harm retains the historical joint-SW threshold above corresponding fixed flows;
it is distinct from primary contrast error. Matched completed-prefix results and
coverage are in matched_compute.csv, without treating candidate counts as compute.

The local Qwen3-8B produced two actual responses in {llm['seconds']:.2f} seconds,
including loading. Both returned metadata objects in the nodes field; the original
strict parser rejected them. A tested serialization adapter extracts exact ordered
IDs and changes no edge/rationale. The first original graph was used before final
access. There was no outcome-based proposal selection or additional generation.
Semantic comparisons and full charged prior costs are in semantic_comparison.csv.
One public-benchmark prior cannot distinguish engineering knowledge from possible
pretraining familiarity and does not establish independent discovery.

The frozen largest standardized-contrast-error M3 example is {worst.run}, {worst.outcome}:
predicted change {worst.pred_effect:+.6g}, measured {worst.observed_effect:+.6g},
absolute error {worst.absolute_error:.6g} in the outcome's physical unit.

## Recorded operating alternatives

The frozen target is upwind-relative mean pressure ≥6.1875 Pa, the development
75th percentile. Each decision chooses only between the two recorded arms,
minimizing predicted total fan current among predicted feasible arms. Decisions,
measured violations, feasible-set coverage and eligible current-regret comparisons
are in decisions.csv and decision_summary.csv. Regret is unavailable for infeasible
choices or unsupported feasible comparisons. A model-generated response surface
is never used as ground truth. This is not verified optimal control.

## Computation, convergence and limitations

Additional device-job use at this report is {book['phase4_gpu_seconds']/3600:.6f}
hours, including the pilot, tests, LLM and grouped refits; cumulative project use
is {book['cumulative_gpu_seconds']/3600:.6f} hours. The authorized device is the
RTX PRO 4500 Blackwell; real CUDA arithmetic and gradients passed. The unchanged
dependency lock and actual environment are preserved with the evidence.

DCDI-DSF density plus the documented optimizer adaptation stopped at
{disc['optimization_steps']:,} steps after {disc['seconds']:.2f} seconds,
with raw h/d={disc['h_per_node']:.6g}. Strict convergence: {disc['converged']}.
Projection removed {len(disc['projection_removed_edges'])} edges. Common-flow
refitting is charged separately. This is a valid capped/projected comparator,
not a converged native DCDI result. It cannot establish that native DCDI is inferior.

Residual temporal dependence, shared ambient measurement error, omitted temperature
and fluid pathways, one audit acquisition and only one randomized hatch acquisition
limit causal and uncertainty claims. The static model is a quasi-steady surrogate;
it does not model transient feedback. The microphone has measured acoustic
contrasts but no compatible main generative comparison. There is no unseen-target,
new-apparatus or live-control evaluation. Previous light-tunnel conclusions remain
unchanged. Further confidence requires replicated randomized acquisitions over
days, matched settling histories, calibrated temperature/ambient context, a common
microphone configuration, and a denser randomized grid of recorded operating
alternatives. Direct airflow, supply voltage and acoustic SPL require their own
calibrated measurements before related engineering claims are possible.

Execution integrity, figure reproduction, template validation and durable artifact
preservation are recorded in separate manifests. All raw records, checkpoints,
generated samples, full logs and bootstrap draws remain ignored artifacts.
'''
    (PHASE/'docs/evidence_report.md').write_text(text)
    claims=[{'claim':'Recorded randomized actuator effects and six-method predictions were evaluated on one wind tunnel','status':'supported','evidence':'execution_audit.json; observed_effects.csv; summary.csv'},
        {'claim':best+' has the lowest observed primary error among the six executed main methods','status':'supported','limit':'descriptive tested-panel ranking, not broad superiority','evidence':'summary.csv; contrasts.csv'},
        {'claim':'The returned DAG or LLM graph establishes direct physical causality','status':'unsupported','evidence':'protocol.json; graphs.json'},
        {'claim':'The DCDI run is a converged native implementation','status':'unsupported','evidence':'capped adaptation; discovery record'},
        {'claim':'Block intervals represent independent-apparatus uncertainty','status':'unsupported','evidence':'one apparatus; acquisition/block resampling'},
        {'claim':'The model provides validated optimal control, airflow, electrical power or dB SPL','status':'unsupported','evidence':'variables.md; finite binary decisions only'},
        {'claim':'A semantic prior generally improves real engineering prediction','status':'untested','limit':'one actual prior and one public apparatus; measured within-case differences only','evidence':'semantic_comparison.csv'},
        {'claim':'Repair reliability transfers uniformly from the synthetic studies','status':'mixed','evidence':'reliability.csv; previous phase reports'},
        {'claim':'Human scientific review and manuscript approval are complete','status':'unsupported','evidence':'review remains pending'}]
    claims.extend([
        {'claim':'Fixed flows improve the observed primary error over ridge on the same initial graph','status':'supported' if s.loc['fixed','effect_error']<s.loc['M1','effect_error'] else 'unsupported','limit':'one apparatus and test panel; no formal general superiority','evidence':'summary.csv'},
        {'claim':'The semantic LLM prior improves the primary endpoint in this application','status':'unsupported' if all(r['error_change']>0 for r in semantic) else 'mixed','evidence':'semantic_comparison.csv'},
        {'claim':'The main M3 graph omits an experimentally supported hatch total effect','status':'supported','limit':'no direct causal edge identified; one randomized hatch acquisition','evidence':'graphs.json; observed_effects.csv'},
        {'claim':'The offline decisions demonstrate a model advantage or verified current savings','status':'unsupported','evidence':'decision_summary.csv; identical choices; current uncertainty'},
        {'claim':'Zero harm counts establish calibrated or generally safe intervention prediction','status':'unsupported','evidence':'reliability.csv; undercoverage in summary.csv; one apparatus'}])
    atomic_json(RESULTS/'claim_ledger.json',claims)
    print(json.dumps({'best_main':best,'best_including_controls':best_all,'phase4_hours':book['phase4_gpu_seconds']/3600,'findings':findings,'semantic':semantic,'decisions':decision_summary}))

if __name__=='__main__':main()
