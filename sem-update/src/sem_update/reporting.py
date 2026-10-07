"""Evidence-first reporting. No author approval or unexecuted results implied."""
import csv
from pathlib import Path
import numpy as np
import pandas as pd
from .runtime import PROJECT,artifact_root,read_json,atomic_json,file_hash,source_state,Ledger,verify_artifacts

def evidence_report(frame,summary):
    from .evaluation import paired_results
    selected=frame[(frame.stage=='selected')&(frame.endpoint=='T2')]
    core=selected[(selected.study=='controlled')&(selected.corruption>0)]
    independent=core[['d','family','seed']].drop_duplicates()
    pairs=paired_results(frame[(frame.study=='controlled')&(frame.corruption>0)])
    counts=pairs.outcome.value_counts().to_dict()
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
            '## Repair reliability','',f"After-audit counts across paired controlled conditions: {counts}. "
            'These conditions are not independent replications. Harm uses max(0.001, 5% of initial SW₁); beneficial uses the symmetric decrease. '
            'All individual deltas are in paired_repairs.csv. Before-audit results remain in metrics.csv.','',
            '## Local LLM and real case','']
    proposals=[]
    for p in (PROJECT/'results/curated/proposals').glob('*.json'):
        proposals.extend(read_json(p)['records'])
    lines.append(f"Initialization generations: {len(proposals)} recorded attempts, {sum(not p['valid'] for p in proposals)} invalid. "
                 'The pinned local Qwen model, exact revision, seeds, token counts and raw-output hashes are recorded. '
                 'LLM-edit is a CauScientist-inspired continuous-flow adaptation with search feedback and rejection memory, not published reproduction scores.')
    real=selected[selected.study=='real']
    if len(real):
        lines+=['','Real T2 results (one apparatus; no real unseen-target claim):','']
        for row in real.to_dict('records'):
            lines.append(f"- {row['method']} / {row['metadata_variant']}: SW₁ {row['sw1']:.5f}; run `{row['run_id']}`.")
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
            '- Mean-effect errors use independent test Monte Carlo reference means; these are finite-sample estimates, not exact analytic effects.',
            '- No optimization-repeat graph stability or real individual counterfactual study is claimed.',
            '- General LLM-guided graph editing, flow SCMs and intervention-aware likelihoods are established prior work; novelty wording requires human review.',
            '- Publication, registration, indexing and acceptance have not been performed or guaranteed.','',
            '## Artifacts and reproduction','',
            'Evidence is stored under SEM_UPDATE_ARTIFACT_ROOT (default sem-update/.artifacts). '
            'Run records, model checkpoints, generated samples, raw LLM outputs and failure traces remain there. '
            'Compact metrics, response tables, graph JSON and vector figures are curated under results/curated and paper/figures. '
            'Figure_manifest.json identifies the plotting inputs and checksums. See README.md and docs/status.md for tested commands and remaining work.']
    (PROJECT/'docs/evidence_report.md').write_text('\n'.join(lines)+'\n')
    claims.extend([
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
