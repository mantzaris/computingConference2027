# Material decisions made before final access

- Actual files supersede advertised generator counts. Counter resets identify
  segments, not independently replicated apparatuses. Inconsistent timestamp
  epoch semantics prevent a claim about calendar-separated sessions.
- The main model has 11 variables. Acoustic outcomes remain measured-only because
  speaker activity and microphone OSR differ across the useful datasets. Keeping
  only two compatible mixed acquisitions would sacrifice the independent-run
  development/selection design and would not validate an acoustic distribution.
- Relative pressures remove common level drift without fitting test-regime
  offsets. This retains shared ambient sensor error and does not establish causal
  sufficiency. Published ADC calibration supports amperes, not electrical power.
- There is no observational fitting regime. M0 uses fitting-policy marginals;
  assigned root-law placeholders are explicitly separated from physical losses.
  The conditional diagnostic reference is an adaptation of the existing policy.
- Quasi-steady filtering and a ten-second primary response horizon limit the
  question. Residual pressure dependence remains. This study tests a static
  response surrogate, not transient dynamics or a proven instantaneous DAG.
- The training-only initializer is greedy Gaussian BIC with declared exogenous
  roots and at most two initial parents; all methods allow three parents during
  discovery/repair. The experimentally validated reference DAG stays unused.
- Source-specific root constraints are enforced in the graph neighborhood. The
  phase-three neighborhood accepted a root argument without applying it; no
  historical file or result is changed. Phase-four tests check the constraint.
- The development pilot selected ridge alpha 1.0 from the frozen four-value grid.
  It measured 22.42 seconds for the representative common-flow fit. A conservative
  full-study estimate is 2.41 device hours, below the twelve-hour ceiling.
- Only 416,332 bytes remain in the cumulative Git allowance. Full graph banks,
  raw/calibrated arrays, prediction draws, full logs, bootstrap arrays and SVG/PNG
  variants stay in ignored storage. Selected compact PDFs and plotting tables
  will be curated without deleting evidence or rewriting history.
- Both bounded LLM responses returned the supplied node metadata objects rather
  than a bare ID list. The original strict parser rejected them. Inspection
  demonstrated a serialization defect: all ordered IDs and proposed edges were
  valid. A tested adapter extracts those exact IDs, changing no edge or rationale.
  Both raw failures remain preserved; the first original valid graph is used,
  without additional generations or outcome-based proposal selection.
- The first final-evaluation attempt wrote all predictions and result tables,
  then failed at its final `json.dumps` logging statement because the evaluator
  omitted the module import. The coordinator now supplies that standard-library
  dependency. Frozen scientific source, protocol, banks and prediction draws are
  unchanged. A single corrective resume reuses those draws; the failed attempt,
  its full runtime and the corrective runtime remain in the cumulative ledger.
- Figure inspection found that globally shared x axes reused hatch-degree labels
  on fan-command panels. Sharing is now limited to each physical-variable column;
  values and displayed acquisitions are unchanged. The original figure variants
  are preserved, and reproduction checks verify both duty and degree labels.
