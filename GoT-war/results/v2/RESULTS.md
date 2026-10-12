# Version 2 measured results

Completed 72 of 72 planned held-out SCM records. All planned test SCMs remain in the primary denominator. Questions are repeated measurements within SCMs. Intervals are 95% SCM bootstrap intervals.

| Method | Valid answers | Identified accuracy | Outcome changes | Outcome preserved | Appropriate uncertainty | Unsupported confident answers |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 1.000 [1.000, 1.000] | 0.567 [0.478, 0.658] | 0.546 [0.410, 0.678] | 0.569 [0.473, 0.668] | 0.431 [0.304, 0.569] | 0.228 [0.177, 0.280] |
| B1 | 0.987 [0.962, 1.000] | 0.561 [0.474, 0.647] | 0.567 [0.436, 0.695] | 0.569 [0.478, 0.661] | 0.377 [0.245, 0.510] | 0.261 [0.208, 0.315] |
| B2 | 0.778 [0.681, 0.875] | 0.778 [0.681, 0.875] | 0.800 [0.675, 0.925] | 0.778 [0.681, 0.875] | 0.000 [0.000, 0.000] | 0.137 [0.100, 0.177] |
| ALT | 0.778 [0.681, 0.875] | 0.778 [0.681, 0.875] | 0.800 [0.675, 0.925] | 0.778 [0.681, 0.875] | 0.529 [0.392, 0.667] | 0.037 [0.013, 0.067] |
| FULL | 0.778 [0.681, 0.875] | 0.778 [0.681, 0.875] | 0.800 [0.675, 0.925] | 0.778 [0.681, 0.875] | 0.529 [0.392, 0.667] | 0.037 [0.013, 0.067] |
| CARRY | 1.000 [1.000, 1.000] | 0.862 [0.820, 0.902] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.332 [0.292, 0.371] |
| ORACLE_FAMILY | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| ORACLE_TRUE | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.209 [0.168, 0.251] |

B0: direct LLM; B1: same text plus generated graph; B2: one synthesized model; ALT: compatible mechanisms; FULL: ALT answers plus separately assessed path/evidence/explanation outputs. CARRY retains the factual outcome. ORACLE_FAMILY receives the declared compatible family. ORACLE_TRUE receives the hidden generating model and is a point-prediction diagnostic, not an uncertainty oracle.

Eligible SCM counts: identified_correct=72, changed_correct=40, unchanged_correct=72, uncertainty_appropriate=51. Eligibility is defined by the fixed questions, not method success.

Zero-width bootstrap intervals at zero or one reflect resampling of the observed SCM scores; they do not guarantee identical performance on new SCMs. These are descriptive intervals, without multiplicity-adjusted discovery claims.

Unsupported confident answers are nonabstaining singleton responses that are wrong or not identified by the record, divided by all questions within each SCM. Missing answers cannot be confident, so this rate must be read together with valid-answer coverage and synthesis failures; low coverage must not be mistaken for safe reasoning.

## Mechanism completeness

| Condition | Method | Identified accuracy | Changed | Preserved | Appropriate uncertainty |
|---|---|---:|---:|---:|---:|
| complete | B0 | 0.714 [0.604, 0.813] | 0.666 [0.489, 0.831] | 0.724 [0.574, 0.862] | not evaluable |
| complete | B1 | 0.663 [0.562, 0.755] | 0.686 [0.516, 0.839] | 0.677 [0.534, 0.805] | not evaluable |
| complete | B2 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | not evaluable |
| complete | ALT | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | not evaluable |
| incomplete | B0 | 0.518 [0.412, 0.627] | 0.447 [0.252, 0.644] | 0.517 [0.404, 0.631] | 0.431 [0.304, 0.569] |
| incomplete | B1 | 0.527 [0.419, 0.633] | 0.470 [0.295, 0.648] | 0.533 [0.421, 0.645] | 0.377 [0.245, 0.510] |
| incomplete | B2 | 0.704 [0.574, 0.815] | 0.636 [0.455, 0.818] | 0.704 [0.574, 0.815] | 0.000 [0.000, 0.000] |
| incomplete | ALT | 0.704 [0.574, 0.815] | 0.636 [0.455, 0.818] | 0.704 [0.574, 0.815] | 0.529 [0.392, 0.667] |
| missing_intermediate | B0 | 0.723 [0.617, 0.817] | 0.567 [0.327, 0.793] | 0.696 [0.542, 0.830] | 0.133 [0.000, 0.300] |
| missing_intermediate | B1 | 0.721 [0.610, 0.819] | 0.567 [0.347, 0.780] | 0.716 [0.589, 0.829] | 0.100 [0.000, 0.233] |
| missing_intermediate | B2 | 0.667 [0.444, 0.889] | 0.600 [0.333, 0.867] | 0.667 [0.444, 0.889] | 0.000 [0.000, 0.000] |
| missing_intermediate | ALT | 0.667 [0.444, 0.889] | 0.600 [0.333, 0.867] | 0.667 [0.444, 0.889] | 0.467 [0.200, 0.733] |
| missing_outcome | B0 | 0.456 [0.235, 0.678] | not evaluable | 0.456 [0.235, 0.678] | 0.556 [0.333, 0.778] |
| missing_outcome | B1 | 0.370 [0.172, 0.586] | not evaluable | 0.370 [0.172, 0.586] | 0.653 [0.431, 0.861] |
| missing_outcome | B2 | 1.000 [1.000, 1.000] | not evaluable | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| missing_outcome | ALT | 1.000 [1.000, 1.000] | not evaluable | 1.000 [1.000, 1.000] | 0.722 [0.500, 0.889] |
| multiple_missing | B0 | 0.376 [0.198, 0.567] | 0.190 [0.000, 0.476] | 0.397 [0.207, 0.604] | 0.556 [0.333, 0.778] |
| multiple_missing | B1 | 0.490 [0.298, 0.676] | 0.262 [0.048, 0.548] | 0.513 [0.302, 0.715] | 0.333 [0.111, 0.556] |
| multiple_missing | B2 | 0.444 [0.222, 0.667] | 0.714 [0.429, 1.000] | 0.444 [0.222, 0.667] | 0.000 [0.000, 0.000] |
| multiple_missing | ALT | 0.444 [0.222, 0.667] | 0.714 [0.429, 1.000] | 0.444 [0.222, 0.667] | 0.389 [0.167, 0.611] |

## Paired differences

| Comparison | Identified accuracy difference | Changed accuracy difference | Uncertainty difference |
|---|---:|---:|---:|
| B1 − B0 | -0.007 [-0.055, 0.046] | 0.021 [-0.085, 0.135] | -0.054 [-0.147, 0.034] |
| B2 − B0 | 0.210 [0.096, 0.328] | 0.254 [0.088, 0.420] | -0.431 [-0.569, -0.304] |
| ALT − B2 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.529 [0.392, 0.667] |
| FULL − B0 | 0.210 [0.096, 0.328] | 0.254 [0.088, 0.420] | 0.098 [-0.108, 0.294] |
| FULL − CARRY | -0.085 [-0.191, 0.016] | 0.800 [0.675, 0.925] | 0.529 [0.392, 0.667] |

## Separate components

| Component | Estimate [95% interval] |
|---|---:|
| synthesis_first | 0.444 [0.333, 0.556] |
| synthesis_after_repair | 0.778 [0.681, 0.875] |
| known_function_agreement | 0.778 [0.681, 0.875] |
| unknown_flag_accuracy | 0.764 [0.667, 0.856] |
| direction_precision | 0.778 [0.681, 0.875] |
| direction_recall | 0.778 [0.681, 0.875] |
| direction_grounding | 0.778 [0.681, 0.875] |
| event_state_agreement | 0.778 [0.681, 0.875] |
| explanation_generated | 0.778 [0.681, 0.875] |
| explanation_deterministic_pass | 0.569 [0.458, 0.681] |
| reviewer_valid_ids | 0.778 [0.681, 0.875] |
| explanation_same_model_supported | 0.681 [0.569, 0.778] |
| explanation_displayable | 0.556 [0.444, 0.667] |
| reviewer_control_accuracy | 0.698 [0.608, 0.788] |
| reviewer_control_false_acceptance | 0.021 [0.000, 0.049] |
| reviewer_control_missing | 0.222 [0.125, 0.319] |

These are controlled explicit-rule texts. Their known functional semantics support equation and intervention scoring, but do not validate narrative concept discovery or Game of Thrones counterfactuals. Displayable prose has passed software checks and same-model review; it is not independently adjudicated. Successful-synthesis-only statistics are secondary and stored in `test_summary.json`.

## Error inventory

Failed-synthesis SCMs: v2_scm_278107, v2_scm_278111, v2_scm_278114, v2_scm_278307, v2_scm_278308, v2_scm_278309, v2_scm_278311, v2_scm_278313, v2_scm_278314, v2_scm_282107, v2_scm_282109, v2_scm_282113, v2_scm_282307, v2_scm_282311, v2_scm_282313, v2_scm_282314.

Attempt-level formal failures (multiple attempts can belong to one SCM): `{"Factual mismatch": 25, "Graph/AST input mismatch V03": 26, "Graph/AST input mismatch V04": 6, "Graph/AST input mismatch V05": 4, "Graph/AST input mismatch V06": 5, "Graph/AST input mismatch V07": 6, "Graph/AST input mismatch V08": 4, "Graph/AST input mismatch V11": 1, "The controlled record has no unmentioned internal residual/background": 3}`.

Other recorded stage failures: `{}`.

Interpretation: a graph/input mismatch rejects an equation that omits or adds a declared input; a factual mismatch rejects a function that fails its supplied factual row. Finite-table repairs expose those local behaviors explicitly. Valid equations can still misread a stated rule, misclassify missing-function uncertainty, or support unfaithful prose; the separate metrics retain those errors.

## Held-out component costs

Post-hoc descriptive request costs, joined by exact raw/JSON-escaped narrative occurrence in retained prompts. Synthesis is shared by B1/B2/ALT/FULL and must not be counted as independent work for each method. Request durations overlap across workers; CPU execution cost is included in case duration but not isolated here. Development/calibration include retained development attempts, not only the final cached records.

Prompt mapping status: `{"exact_narrative_match": 796, "no_controlled_narrative": 295}`. First held-out request: `2026-10-12T20:14:09.215321+00:00`; all matched held-out requests follow the freeze: `True`.

| Request role | Requests | Distinct SCMs | Input tokens | Output tokens | Sum request seconds | API/JSON errors |
|---|---:|---:|---:|---:|---:|---:|
| v2_B0 | 72 | 72 | 97495 | 33133 | 904.3 | 0 |
| v2_B1 | 72 | 72 | 112399 | 33206 | 974.7 | 0 |
| v2_explanation | 56 | 56 | 101548 | 13895 | 523.0 | 0 |
| v2_explanation_repair | 21 | 21 | 44133 | 6626 | 202.1 | 0 |
| v2_explanation_review | 56 | 56 | 115811 | 16061 | 594.9 | 0 |
| v2_reviewer_controls | 56 | 56 | 104012 | 13377 | 438.4 | 0 |
| v2_synthesis | 72 | 72 | 81799 | 160845 | 3850.8 | 0 |
| v2_synthesis_patch | 40 | 40 | 109067 | 17128 | 417.9 | 0 |
| v2_synthesis_repair | 24 | 24 | 29224 | 52062 | 1190.5 | 0 |

B0 requires direct answering. B1 additionally uses the shared synthesis stage; B2 and ALT execute that shared program without another answering request. FULL adds explanation generation and review. Reviewer controls are evaluation overhead. CPU solver costs are not isolated from complete case durations. Development/application work is accounted separately in `usage.json`; these totals must not be summed as independent per-method GPU costs.
