# Editorial claim-to-evidence map

This file is outside the reader-facing manuscript. Paths below are relative to
`sem-update/`. Numerical selectors, values and input hashes are generated in
[claim_evidence.json](../.artifacts/manuscript_draft/claim_evidence.json) and
[validation.json](../.artifacts/manuscript_draft/validation.json).

| Manuscript material | Authoritative evidence or executed implementation |
| --- | --- |
| Equations 1 and 2, exact parents, inverse density, intact mechanisms | `src/sem_update/flows.py`; fitting in `training.py` and `phase3/flows.py`; wind masking and acquisition-law handling in `phase4_real_application/tools/app_methods.py` and `app_data.py` |
| Equation 3, diagnostic priorities | `src/sem_update/diagnostics.py`, `phase3/diagnostics.py`; wind `conditional_diagnostics` in `app_methods.py`. Permutation scales are descriptive priorities, not p values. |
| Equation 4, mean score and environment decomposition | `src/sem_update/phase2/objectives.py`, `phase3/objectives.py`; defaults in `search.py`. Wind keeps full dimension in its score normalization. |
| Equation 5, robust selection | `phase2/objectives.py:select` and `phase3/selection.py`. Same frozen fitted bank, rho 0.5, tolerance 0.005. |
| Equation 6, energy objective and complete-SCM mixtures | `phase2/objectives.py:energy_matrices`, `weight_objective`, `fit_weights`; `phase2/models.py:Ensemble`; batched scaling and wind adapters. Tau 0.01. Fixed samples and non-target dimension normalization. |
| One-time audit | `phase2/objectives.py:audit_score`, `phase2/models.py:joint_nll`, `search.py:audit_pass`, scaling/wind equivalents. Whole-joint mixture logsumexp precedes intact-node normalization. |
| Equation 7, sliced Wasserstein and harm | `src/sem_update/metrics.py:wasserstein`, `phase2/reporting.py:repair_table`, `phase3/reporting.py`. Final projection count 256 and quantile grid 512. Harm threshold is max(0.001, 0.05 times fixed error). |
| Equation 8, wind contrast error | `phase4_real_application/tools/app_evaluate.py`; fitting scales and exact acquisition/arm definitions in the frozen protocol and split manifest. Five outcomes equally weighted, acquisitions averaged within three targets. |
| Controlled table and figures, primary ranking and ablations | `phase2/results/method_summary.csv`, `metrics.csv`, `repair_reliability.csv`, `primary_comparisons.csv`, `repair_comparisons.csv`, `checkpoint_summary.csv` |
| Earlier search-selected benchmark | `phase2/results/historical_verification.json`, original `results/curated/` metrics and reports. Kept separate from calibration-selected comparison. |
| Size, topology, retention, initial/final SHD and oracle subset | `phase3/results/summary.csv`, `metrics.csv`, `reliability.csv`, `mixture_weights.csv`, `contrasts.csv`, `datasets.csv`, `priors.csv` |
| Scaling compute, failures and sensitivities | `phase3/results/compute.json`, `discovery.csv`, `checkpoint_coverage.csv`, `checkpoints.csv`, `projection_sensitivity.csv`, `budget_sensitivity.csv` |
| DCDI stopping discrepancy | `phase2/results/discovery_coverage.csv` and `src/sem_update/dcdi.py` give the optimizer-normalized criterion. `phase3/results/discovery.csv` reports raw-per-node acyclicity. These definitions must not be pooled. |
| Light-tunnel polarizer accuracy and uncertainty | `phase2/results/method_summary.csv`, `real_block_intervals.csv`, coherent metadata and T2 filters; split boundaries in `splits.json` and physical-data implementation. |
| Wind accuracy, uncertainty and method costs | `phase4_real_application/results/summary.csv`, `metrics.csv`, `costs.csv`, `contrasts.csv`, `refit_sensitivity.csv`, `compute.json` |
| Wind process graph, omitted hatch, stability, mixture components | `phase4_real_application/results/graphs.json`, `process_edges.csv`, `edge_frequency.csv`; existing graph figures referenced without changing their data. |
| Measured effects, response curves and correct units | `phase4_real_application/results/observed_effects.csv`, `effects.csv`, `plot_responses.csv`, `plot_total_effects.csv`, `acoustic.csv`; application data audit and variable dictionary |
| Operating decision result | `phase4_real_application/results/decisions.csv`, `decision_summary.csv`, `protocol.json`; identical choices and regret do not establish a method benefit or energy savings. |
| Actual LLM proposals and controls | `phase2/results/llm_edit_audit.csv`, `semantic_llm_comparisons.csv`, `metadata_comparisons.csv`; wind `llm_prior.json`, `semantic_comparison.csv`. Original serialization failures remain recorded. |
| Dataset provenance, exclusions, row accounting and sealing | Wind `data_provenance.json`, `acquisitions.csv`, `split_manifest.json`, `protocol.json`, `execution_audit.json`; corresponding controlled and scaling manifests |

All paths in the implementation rows start at `src/sem_update/` unless a full
path is specified. The manuscript's figures use existing compact plotting data,
not new fitting or new Monte Carlo samples. Figure source hashes include the
three reused graph PDFs. The formal ranking checks use the recorded multiplicity
correction, and the text uses “observed” where a broader superiority comparison
was not supported.
