# Executed wind-tunnel application evidence

This separate phase preserves studies ad21e60, 8c452ac and a17a8f7. It evaluates
one wind-tunnel apparatus, not a population of independent physical systems.
Human scientific review remains pending.

## Executed coverage and primary prediction

Eight fitting acquisitions and disjoint early/search/calibration/audit acquisitions
produce 3,399 non-test observations including the
single preprocessing-only row. Development examined another 14,000 recorded rows.
The primary test contains 699 measurements in five randomized acquisition files,
with three actuator targets and a ten-second post-assignment wait. A separate
three-file panel contains 3,200 measurements at shorter waits. Five grouped
training-run bootstrap refits and one actual local-LLM semantic initialization
were executed. These are repeated analyses of the same apparatus.

**M2 has the lowest observed primary error among the six main methods;
M2 has the lowest observed error including fixed/random controls.** The
endpoint is the standardized absolute error of measured randomized changes on
both currents and three ambient-relative pressures, weighted equally by outcome
and actuator. Joint SW1 remains secondary and can be affected by ambient drift.

| Method | Primary contrast error [95% CI] | Joint SW1 | Coverage 90% | Charged s | Prediction s |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 | 1.0911 [1.0514, 1.1264] | 2.9158 | 61.7% | 0.02 | 0.03 |
| M1 | 0.8131 [0.7726, 0.8490] | 2.7164 | 67.9% | 0.50 | 0.08 |
| M2 | 0.2199 [0.1987, 0.2462] | 2.5780 | 73.0% | 699.31 | 0.14 |
| M3 | 0.3310 [0.2915, 0.3664] | 2.5819 | 72.2% | 296.84 | 0.49 |
| M4 | 0.3680 [0.3299, 0.4030] | 2.5953 | 66.8% | 296.78 | 0.44 |
| M5 | 0.3506 [0.3200, 0.3811] | 2.5954 | 68.7% | 290.02 | 0.79 |
| fixed | 0.3602 [0.3298, 0.3904] | 2.5966 | 65.7% | 29.44 | 0.38 |
| random | 0.3320 [0.2927, 0.3674] | 2.5825 | 71.7% | 276.74 | 0.50 |

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

- At hatch 0° and outlet duty 0.01, changing inlet duty 0.01→1 changes inlet current by +0.106 A (95% block CI +0.103 to +0.1089; 25/25 low/high assignments) and upwind-relative pressure by +26.51 Pa relative to ambient (95% block CI +25.97 to +26.94; 25/25 low/high assignments).
- At hatch 0° and inlet duty 0.01, changing outlet duty 0.01→1 changes outlet current by +0.1079 A (95% block CI +0.1039 to +0.1128; 23/26 low/high assignments) and downwind-relative pressure by -26.15 Pa relative to ambient (95% block CI -26.49 to -25.91; 23/26 low/high assignments).
- At inlet duty 1 and outlet duty 0.01, opening the hatch 0→45° changes upwind-relative pressure by -5.426 Pa relative to ambient (95% block CI -6.376 to -4.522; 117/83 low/high assignments) and inlet current by -0.002438 A (95% block CI -0.005206 to +0.0004793; 117/83 low/high assignments).
- In the separate outlet-command acoustic experiment (10-second wait, hatch 0°, inlet duty 0.01), microphone-circuit amplitude changes by +0.4611 V (95% block CI +0.2585 to +0.6568). This is not dB SPL; no generative acoustic prediction was fitted across incompatible OSR settings.

These randomized contrasts support total actuator effects at the stated fixed
nuisance commands. They do not establish direct edges, airflow, power savings,
acoustic SPL or transport to different equipment. Published current calibration
uncertainty is not included in the block intervals.

## Graph, repair reliability and semantic prior

The main M3 process graph has 14 initial and 15 returned
edges: 2 added, 1 removed. Of its
returned edges, 5 appear in fewer than three of five grouped refits.
Selection frequency is conditional algorithmic stability, not causal probability.
The full graph and all M5 components are retained in graphs.json. Ensemble weights
combine complete predicted distributions and are not probabilities of causal truth.

| Method | Harmful tested regimes / 5 | Max SW deterioration | Returned G0 |
| --- | ---: | ---: | --- |
| M3 | 0/5 | -0.0038 | False |
| M4 | 0/5 | 0.0008 | False |
| M5 | 0/5 | 0.0019 | False |
| random | 0/5 | -0.0029 | False |

These five regime counts concern one selected repair, not five independent repairs.
Harm retains the historical joint-SW threshold above corresponding fixed flows;
it is distinct from primary contrast error. Matched completed-prefix results and
coverage are in matched_compute.csv, without treating candidate counts as compute.

The local Qwen3-8B produced two actual responses in 69.15 seconds,
including loading. Both returned metadata objects in the nodes field; the original
strict parser rejected them. A tested serialization adapter extracts exact ordered
IDs and changes no edge/rationale. The first original graph was used before final
access. There was no outcome-based proposal selection or additional generation.
Semantic comparisons and full charged prior costs are in semantic_comparison.csv.
One public-benchmark prior cannot distinguish engineering knowledge from possible
pretraining familiarity and does not establish independent discovery.

The frozen largest standardized-contrast-error M3 example is validate_load_out, pressure_intake:
predicted change +5.5677, measured -1.58949,
absolute error 7.15719 in the outcome's physical unit.

## Recorded operating alternatives

The frozen target is upwind-relative mean pressure ≥6.1875 Pa, the development
75th percentile. Each decision chooses only between the two recorded arms,
minimizing predicted total fan current among predicted feasible arms. Decisions,
measured violations, feasible-set coverage and eligible current-regret comparisons
are in decisions.csv and decision_summary.csv. Regret is unavailable for infeasible
choices or unsupported feasible comparisons. A model-generated response surface
is never used as ground truth. This is not verified optimal control.

## Computation, convergence and limitations

Additional device-job use at this report is 0.793968
hours, including the pilot, tests, LLM and grouped refits; cumulative project use
is 36.370067 hours. The authorized device is the
RTX PRO 4500 Blackwell; real CUDA arithmetic and gradients passed. The unchanged
dependency lock and actual environment are preserved with the evidence.

DCDI-DSF density plus the documented optimizer adaptation stopped at
40,000 steps after 670.99 seconds,
with raw h/d=1.86195e-06. Strict convergence: False.
Projection removed 13 edges. Common-flow
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
