# Phase-two evidence for scientific review

Executed 60 controlled conditions from 15 independent SCMs. Best observed mean T2 prediction: M3 Average repair, 0.10617 (descriptive SCM-cluster 95% interval [0.09195, 0.12213]).

This ranking is descriptive. Formal pairwise primary comparisons use SCM-level sign randomization and Holm correction over all 15 pairs, assuming sign exchangeability under the paired null. See results/primary_comparisons.csv; overlapping marginal intervals alone do not establish ties or differences.

The best observed method is not separated by the corrected primary test from: none. It has a corrected difference from: M0, M1, M2, M4, M5. Failure to separate methods is not proof of equivalence.

The lowest observed repair harm frequency among M3/M4/M5/random is shared by M5 Anchored mixture: 1/60. Mean gains, retention and harm severity must be read together; retaining G0 is not proof of better prediction.

Observed accuracy/computation Pareto set among the six main methods: M0, M1, M3, M4, M5. Cost here is logical construction/selection plus one complete final prediction batch. There is no unique best tradeoff without a cost preference. Simple methods receive their measured small costs rather than artificial compute padding. The frontier is descriptive, not a test of efficiency dominance.

DCDI-DSF strict convergence: 29/30 unique controlled dataset fits. All capped fits and projected edges are disclosed. A capped baseline is not evidence about the fully converged published algorithm. Discovery and common-flow refitting costs are separate.

Phase-two device use: 5.774939 h; historical 10.318525 h; cumulative 16.093464 h. Runtime includes tests, development, pilots and failed attempts. Logical method costs count shared bank construction separately for each M3/M4/M5 method.

Coverage: 468 six-method conditions across 78 settings / 36 datasets. Controls and checkpoint variants bring this to 2390 selected method-condition records. See run_coverage.csv and execution_audit.json for actual completion, failed validation attempts and resumed jobs. A metadata variant or checkpoint is not a new independent SCM.

Recorded peak allocated CUDA memory across method stages: 15.558 GiB; deterministic-grid optimizer fallbacks: 0. This is allocator memory, not a continuous device-wide reserved-memory trace.

## Main controlled results

| method | mean | low | high | flow_fit_seconds | discovery_seconds | prediction_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| M0 | 0.3250 | 0.2905 | 0.3587 | 0.0294 | 0.0000 | 0.0043 |
| M1 | 0.1940 | 0.1579 | 0.2283 | 0.0393 | 0.0000 | 0.0112 |
| M2 | 0.2722 | 0.2303 | 0.3225 | 53.7303 | 792.7185 | 0.1241 |
| M3 | 0.1062 | 0.0919 | 0.1221 | 169.5007 | 0.0000 | 0.1224 |
| M4 | 0.1175 | 0.1020 | 0.1349 | 169.5007 | 0.0000 | 0.1223 |
| M5 | 0.1302 | 0.1105 | 0.1508 | 169.5007 | 0.0000 | 0.2472 |

Fit seconds include all canonical mechanisms needed by a method; M0/M1 contain their direct fitting costs. Prediction seconds cover all final environments for that model, not a single environment. Mechanism times measured with concurrent workers include device contention. Actual incremental method fields must not be summed across reused conditions; the cumulative device ledger is authoritative.

## Repair reliability

| method | harmful_count | conditions | mean_improvement | harmful_severity_mean | retention_rate |
| --- | --- | --- | --- | --- | --- |
| M3 | 8 | 60 | 0.0757 | 0.0344 | 0.2500 |
| M4 | 7 | 60 | 0.0643 | 0.0381 | 0.3833 |
| M5 | 1 | 60 | 0.0516 | 0.0104 | 0.0167 |
| random | 5 | 60 | 0.0397 | 0.0346 | 0.3333 |

Secondary paired extension differences (negative error/harm changes favor the extension; these intervals are descriptive, without additional formal superiority claims):

| comparison | metric | mean | low | high |
| --- | --- | --- | --- | --- |
| M4 - M3 | sw1 | 0.0114 | 0.0027 | 0.0220 |
| M4 - M3 | harmful | -0.0167 | -0.0500 | 0.0000 |
| M4 - M3 | positive_deterioration | -0.0002 | -0.0004 | 0.0000 |
| M4 - M3 | retained_initial | 0.1333 | 0.0667 | 0.2000 |
| M5 - M3 | sw1 | 0.0240 | 0.0116 | 0.0379 |
| M5 - M3 | harmful | -0.1167 | -0.2000 | -0.0500 |
| M5 - M3 | positive_deterioration | -0.0043 | -0.0077 | -0.0013 |
| M5 - M3 | retained_initial | -0.2333 | -0.3333 | -0.1333 |

The fixed G0 reference is common within each task. Harm is N/A for nonrepair M0/M1/M2. Zero observed harm can produce a degenerate bootstrap interval and does not rule out harm on new SCMs. Matched computation curves retain only conditions available for both policies at each ceiling and report achieved updates and time. The time ceiling covers canonical mechanism fitting, not all search and diagnostic overhead; total method costs are shown separately.

Largest observed harmful repair: M3 on p2-main-linear-d5-s211004-B100-c0.2-none, error change +0.07697 against a harm threshold of 0.00491. See F5/F6.

## Separate semantic and real panels

| panel | best_main | main_SW1 | best_including_controls | all_SW1 |
| --- | --- | --- | --- | --- |
| real/anonymous/T2 | M1 | 0.0856 | M1 | 0.0856 |
| real/anonymous/T2_exploratory | M5 | 0.1131 | fixed | 0.1131 |
| real/coherent/T2 | M1 | 0.0856 | M1 | 0.0856 |
| real/coherent/T2_exploratory | M5 | 0.1131 | fixed | 0.1131 |
| real/shuffled/T2 | M1 | 0.0856 | M1 | 0.0856 |
| real/shuffled/T2_exploratory | M5 | 0.1131 | fixed | 0.1131 |
| semantic/anonymous/T2 | M5 | 0.0906 | M5 | 0.0906 |
| semantic/coherent/T2 | M5 | 0.0925 | M5 | 0.0925 |
| semantic/shuffled/T2 | M5 | 0.0830 | M5 | 0.0830 |

The real polarizer panel uses previously unused intervention regimes, conditional on recorded assignment setpoints. It is one familiar apparatus, with temporal dependence and phase-one-informed design. Each regime has one acquisition run. Ten-row bootstrap groups are analyst-defined contiguous reporting blocks, not independent acquisitions; non-test roles use separated within-run segments. RGB results remain exploratory. Resplitting previously exposed observations does not make them confirmatory. Real block intervals quantify conditional observation uncertainty, not between-apparatus or refitting uncertainty.

Semantic LLM comparisons are paired over five independent systems and corrected as a separate family. With five systems a two-sided exact sign test has limited resolution. Real comparisons use conditional within-run reporting-block intervals and are not population-level causal confirmation. Anonymous/shuffled controls use the same underlying SCMs.

## LLM interface diagnosis

The historical raw audit checked 46 query attempts and 138 individual proposals. 114 were individually valid DAGs that failed the single-edit contract; 24 violated design constraints. The old all-or-nothing batch parser also discarded 30 otherwise valid sibling DAGs. These proposal-level counts clarify the older batch/attempt counts without changing its zero-admissible-edit conclusion. The full-graph versus isolated-edge ambiguity and inconsistent node-ID presentation motivated the new legal-edit menu.

| category | main_count |
| --- | --- |
| malformed_output | 0 |
| invalid_nodes | 0 |
| cycles | 0 |
| duplicate_graphs | 0 |
| valid_no_change | 0 |
| valid_new_edits | 122 |
| score_rejections | 97 |
| accepted_changes | 25 |
| evaluated_new_candidates | 122 |
| repeated_valid_proposals_across_retry | 0 |
| valid_unique_proposals_not_evaluated | 0 |

These are actual frozen Qwen3-8B generations. The edit menu guarantees that legal IDs map to acyclic graphs; an invalid ID is counted in the invalid-node/interface category. Counts distinguish proposal validation from search-score rejection and accepted search moves. Valid-proposal events can repeat across a validation retry, and the per-round fitting cap can leave a valid proposal unevaluated; both are counted separately. An accepted move can still be rejected by calibration or the one-time audit. The historical full-DAG/edit-contract failure is preserved in historical_llm_audit.json; it is not poor-method evidence.

Historical negative findings are preserved: diagnostic repair worsened semantic and real prediction; ten of 120 controlled conditions were harmful after audit; achieved fitting budgets differed; the old LLM interface admitted no new edits. The new LLM menu comparator is evaluated separately and is an adaptation inspired by CauScientist.

## Limits and interpretation

Five systems per family give limited power, especially for family-specific claims. Calibration has only ten observations per intervention at B100. Robust selection protects observed calibration environments, not arbitrary unseen settings. Mixture weights are predictive weights, not causal probabilities; marginal prediction intervals are not confidence intervals for causal effects. M2 discovers a graph without receiving the corrupted prior supplied to repair and ridge; this information difference is part of the comparison. The strict-convergence subset is a descriptive optimization-status sensitivity analysis and is not a random subgroup. No identifiability, harmless-repair guarantee, literature-priority or acceptance claim follows from these experiments. Alex must review assumptions, protocol, evidence and final text.

Reproducibility inputs are in phase2/results; final vectors, previews and tables are in phase2/paper. Full raw data, checkpoints, generated observations, candidate traces and logs are in ignored .artifacts/phase2. The runtime, frozen source/model hashes, artifact inventory and staged-blob audit record the execution and preservation state. Historical evidence remains separate. The source-linked novelty and venue reviews are in docs/novelty.md and docs/venue.md.
