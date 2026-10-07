# Evidence report for Alex’s review

This report summarizes executed computations. Human scientific review and manuscript approval remain pending.

Primary controlled study: 30 independent SCMs; graph sizes [5, 10]; three mechanism families; two non-test intervention budgets and two nominal corruption levels. Uncorrupted heteroscedastic controls are reported separately.

## Primary paired T2 prediction comparisons

- controlled, diagnostic - fixed: mean ΔSW₁ -0.07815; 95% paired cluster bootstrap interval [-0.10060, -0.05672]; 30 independent SCMs. Negative favors diagnostic repair.
- controlled, diagnostic - random: mean ΔSW₁ -0.04825; 95% paired cluster bootstrap interval [-0.06652, -0.03211]; 30 independent SCMs. Negative favors diagnostic repair.
- semantic, diagnostic - llm_edit: mean ΔSW₁ +0.03057; 95% paired cluster bootstrap interval [+0.01085, +0.05029]; 5 independent SCMs. Negative favors diagnostic repair.

Intervals quantify variation across SCMs, retaining budgets, corruptions and metadata variants within clusters. They are distinct from predictive quantiles in response plots. No unadjusted multiple-comparison p-values are reported.

## Distinct generalization endpoints

T1 uses new samples at the fitting setting, T2 uses a new setting on seen targets, and T3 uses unseen targets. The following T1/T3 comparisons are descriptive secondary results, not replacements for the frozen T2 endpoint. All endpoint, family, graph-size and budget summaries remain separate in endpoint_summary.csv.

- T1, diagnostic - fixed: mean ΔSW₁ -0.05193; 95% paired SCM interval [-0.06458, -0.04002]; n=30.
- T1, diagnostic - random: mean ΔSW₁ -0.02881; 95% paired SCM interval [-0.03887, -0.01986]; n=30.
- T3, diagnostic - fixed: mean ΔSW₁ -0.04789; 95% paired SCM interval [-0.06661, -0.02922]; n=30.
- T3, diagnostic - random: mean ΔSW₁ -0.03488; 95% paired SCM interval [-0.04926, -0.02219]; n=30.

## Repair reliability

After-audit counts across paired controlled conditions: {'beneficial': 84, 'neutral': 26, 'harmful': 10}. These conditions are not independent replications. Harm uses max(0.001, 5% of initial SW₁); beneficial uses the symmetric decrease. All individual deltas are in paired_repairs.csv. Before-audit results remain in metrics.csv.
Before-audit counts: {'beneficial': 84, 'neutral': 26, 'harmful': 10}. The audit did not reduce the observed number of harmful T2 repairs in this matrix. Passing its independent in-setting check does not guarantee safe extrapolation.

Largest adverse example: `benchmark-linear-d5-s11004-B100-diagnostic-c0.5-none`. T2 SW₁ rose from 0.246529 to 0.301508 (Δ +0.054980) despite passing the audit. SHD changed from 4 to 3. Figure F2_adverse shows the accepted reversal; an improvement in graph distance need not improve finite-sample intervention prediction.

## Local LLM and real case

Initialization generations: 46 recorded attempts, 20 invalid. The pinned local Qwen model, exact revision, seeds, token counts and raw-output hashes are recorded. LLM-edit is a CauScientist-inspired continuous-flow adaptation with search feedback and rejection memory, not published reproduction scores.
Conditions with no valid LLM start: 5 of 18. The predeclared data-only initializer remains available. See llm_generation_audit.csv; invalid and duplicate attempts are not relabeled as successful generations. Metadata comparisons include both proposal validity and fallback behavior; their prediction differences do not isolate the quality of accepted semantic graph knowledge.
LLM-edit stage: 46 actual generation attempts, 18 invalid attempts and 84 rejected proposed graphs across 18 conditions. Attempt and proposed-graph counts are different units; per-run records are in llm_edit_audit.csv.
All 18 LLM-edit conditions returned the initial graph, with 0 admissible new candidates evaluated. Rejected parsed graphs by reason: {'not a legal single edit': 84}; their edge counts: {'1': 84}. Every rejected parsed proposal contained one edge although the prompt requested the complete edited DAG. Invalid generations violated assigned-root constraints. The incumbent uses numeric node indices while the requested output uses V-prefixed IDs, adding an avoidable interface burden. These are actual model outputs, preserved without post-test reinterpretation or prompt repair. This failed adaptation is not evidence against CauScientist or evidence of effective LLM editing. The semantic comparison is therefore effectively against fixed initial graphs. A stronger edit-command interface requires a new prospectively frozen study, not a favorable retry here. See llm_edit_failure_audit.json.

Semantic metadata controls:

- diagnostic - llm_edit (coherent): ΔSW₁ +0.02511, 95% paired SCM interval [+0.00413, +0.04833], n=5. Negative favors the first named method.
- diagnostic - llm_edit (anonymous): ΔSW₁ +0.02183, 95% paired SCM interval [-0.00097, +0.04650], n=5. Negative favors the first named method.
- diagnostic - llm_edit (shuffled): ΔSW₁ +0.04478, 95% paired SCM interval [+0.01524, +0.07514], n=5. Negative favors the first named method.
- coherent diagnostic - anonymous diagnostic: ΔSW₁ +0.00111, 95% paired SCM interval [-0.00164, +0.00498], n=5. Negative favors the first named method.
- coherent diagnostic - shuffled diagnostic: ΔSW₁ -0.00055, 95% paired SCM interval [-0.00164, +0.00000], n=5. Negative favors the first named method.
- coherent diagnostic - none data_only: ΔSW₁ -0.00055, 95% paired SCM interval [-0.00164, +0.00000], n=5. Negative favors the first named method.

Restricted diagnostic ablations:

- diagnostic - marginal: ΔSW₁ -0.02782, 95% paired SCM interval [-0.09060, +0.00758], n=5. Negative favors the first named method.
- diagnostic - no_wasserstein: ΔSW₁ -0.01053, 95% paired SCM interval [-0.03243, +0.00104], n=5. Negative favors the first named method.
- diagnostic - additive_repair: ΔSW₁ -0.02438, 95% paired SCM interval [-0.03505, -0.01371], n=5. Negative favors the first named method.

Flow versus additive mechanisms:

- fixed flow - fixed additive: ΔSW₁ +0.00140, 95% paired SCM interval [-0.00101, +0.00368], n=30. Negative favors the first named method.

Uncorrupted starting-graph control: {'neutral': 9, 'harmful': 1} across the ten paired budget conditions from five heteroscedastic SCMs. A correct structural starting graph can still receive a predictively harmful edit.

Real T2 results (one apparatus; no real unseen-target claim):

- data_only / none: SW₁ 0.09049; run `chambers-B400-data_only-c-1-none`.
- dcdi / none: SW₁ 0.08907; run `chambers-B400-dcdi-c-1-none`.
- fixed / coherent: SW₁ 0.08567; run `chambers-B400-fixed-c-1-coherent`.
- diagnostic / coherent: SW₁ 0.09049; run `chambers-B400-diagnostic-c-1-coherent`.
- random / coherent: SW₁ 0.08463; run `chambers-B400-random-c-1-coherent`.
- llm_edit / coherent: SW₁ 0.08567; run `chambers-B400-llm_edit-c-1-coherent`.
- fixed / anonymous: SW₁ 0.08284; run `chambers-B400-fixed-c-1-anonymous`.
- diagnostic / anonymous: SW₁ 0.08639; run `chambers-B400-diagnostic-c-1-anonymous`.
- random / anonymous: SW₁ 0.08639; run `chambers-B400-random-c-1-anonymous`.
- llm_edit / anonymous: SW₁ 0.08284; run `chambers-B400-llm_edit-c-1-anonymous`.
- fixed / shuffled: SW₁ 0.08567; run `chambers-B400-fixed-c-1-shuffled`.
- diagnostic / shuffled: SW₁ 0.09049; run `chambers-B400-diagnostic-c-1-shuffled`.
- random / shuffled: SW₁ 0.08463; run `chambers-B400-random-c-1-shuffled`.
- llm_edit / shuffled: SW₁ 0.08567; run `chambers-B400-llm_edit-c-1-shuffled`.
Coherent diagnostic − fixed: ΔSW₁ +0.00482, conditional block interval [+0.00219, +0.00648]. Repair worsened the primary real endpoint; the controlled-corruption gain did not generalize to this case.

Actual RGB strong regimes are held out as new settings. Raw ADC/PWM data are dequantized; all relevant included-sensor settings are fixed. Acquisition blocks and gaps are recorded. Residual serial dependence, shared electronics, imperfect measurement models and extrapolation limit causal interpretation. Conditional intervals resample ten-row acquisition blocks within each strong regime (200 replicates); models and generated samples are fixed. They are in real_block_intervals.csv and real_block_comparisons.csv. No independent-apparatus confidence interval is claimed. The sample budget counts 6,656 randomized reference rows plus 1,200 additional mid-RGB rows: 7,856 non-test experimental observations. B=400 means rows per additional target regime, not the total real budget.

## Achieved fitting budget

Achieved controlled costs per paired condition: diagnostic versus random used 10.58 versus 9.52 DAGs and 9047.1 versus 7525.4 canonical optimizer updates. The latter counts each required node/parent-set once irrespective of cross-method cache hits. Actual cached updates and timing are in achieved_cost_summary.csv; shared-cache execution order prevents treating wall time as an isolated-method benchmark.

## Computational validation and failures

Device: NVIDIA RTX PRO 4500 Blackwell; driver 580.159.04; PyTorch 2.8.0+cu128; CUDA runtime 12.8; actual CUDA gradients recorded. Union of recorded reserved-device intervals: 10.319 hours (cap 64).

Recorded failed jobs: 3. Initial test-runner setup and development DCDI adapter failures are retained, not converted to zero error or silently omitted. Inspect dcdi_development.json and run_index.json for baseline convergence and any threshold projection.

DCDI benchmark fits: 66; 47 met the strict normalized constraint; 28 required edge removal for the declared DAG/indegree projection. Update-cap results remain included and explicitly flagged. This is the documented official-network CUDA adaptation, not an exact published-score reproduction.

## Limits and interpretation

- Finite intervention data and flexible flows do not identify every edge. LLM suggestions and residual diagnostics are fallible.
- Node-local caching changes achieved compute. Candidate counts, actual and canonical optimizer updates, parent-set fits, measured times and memory are reported separately. Elapsed times depend on cache execution order and concurrent GPU jobs.
- The equal maximum of 12 candidate DAGs and identical stopping rule do not equalize achieved fitting work. No equal-optimizer-budget or compute-efficiency superiority is established.
- Mean-effect errors use independent test Monte Carlo reference means; these are finite-sample estimates, not exact analytic effects.
- No optimization-repeat graph stability or real individual counterfactual study is claimed.
- General LLM-guided graph editing, flow SCMs and intervention-aware likelihoods are established prior work; novelty wording requires human review.
- Publication, registration, indexing and acceptance have not been performed or guaranteed.

## Artifacts and reproduction

Evidence is stored under SEM_UPDATE_ARTIFACT_ROOT (default sem-update/.artifacts). Run records, model checkpoints, generated samples, raw LLM outputs and failure traces remain there. Compact metrics, response tables, graph JSON and vector figures are curated under results/curated and paper/figures. figure_manifest.json identifies the plotting inputs and checksums. See README.md and docs/status.md for tested commands and remaining work.

Recorded maximum PyTorch allocation: 15.593 GiB; flow-stage maximum 0.107 GiB. Sampled whole-device occupancy is reported separately in runtime_memory_summary.json; it includes contexts and concurrent processes and is not interchangeable with tensor allocation.
