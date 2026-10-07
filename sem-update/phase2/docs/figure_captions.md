# Figure and table interpretation

These captions specify how to read the executed figures. They do not assert
which method wins. Final outcome claims belong in the evidence report and claim
ledger. All numeric panels derive from actual frozen predictions. PDF/SVG are
the publication masters; PNG files are inspection previews.

- **F0, shared-bank procedure.** M3, M4 and M5 use the same fitted candidate bank.
  Search, calibration, audit and final observations have separate roles. The
  audit returns the initial model after rejection, without another candidate
  attempt. This is a protocol schematic, not an experimental result.
- **F1, mechanism family and intervention budget.** Mean T2 joint sliced
  Wasserstein error, averaging the two corruption conditions within each SCM.
  Bars are pointwise 95% confidence intervals from resampling five independent
  SCMs in each family. B counts all fit/early/search/calibration/audit rows per
  seen target; total non-test intervention observations are 3B.
- **F2, matched fitting ceilings.** Diagnostic and random repair use completed
  candidate prefixes at the same update or canonical fitting-time ceiling.
  Conditions must be available for both policies. The accompanying checkpoint
  table gives coverage and achieved cost; these can differ across ceilings.
  Shading is SCM-cluster uncertainty. Fitting time includes contention from the
  recorded execution schedule and excludes policy/scoring overhead. This panel
  must not be described as equal total method runtime.
- **F3, accuracy, harm and cost.** Left: controlled mean error versus logical
  model construction and selection time. Each M3/M4/M5 method pays its entire
  shared bank cost. Right: mean gain over fixed G0 versus harmful frequency.
  Harm exceeds max(0.001, 5% of G0 error). Horizontal and vertical bars are
  separate pointwise SCM-cluster intervals, not a joint confidence region.
- **F4, representative graphs.** Common node positions show G0, returned M3/M4,
  the synthetic reference DAG and M5's shortlisted components. Component weights
  are predictive combination weights before audit; audit rejection returns G0.
  The largest-weight graph is explicitly a representative, not a causal
  posterior mode. Uniform edge widths convey topology only, not effect size or
  graph stability. The case is the median M3 change among B400/high-corruption
  conditions, selected by a rule fixed before evaluation.
- **F5, adverse graphs, if harm occurs.** The largest harmful returned-model
  change among M3/M4/M5 illustrates an adverse condition. The graph panel uses
  the same layout and interpretation as F4. It is an intentionally adverse
  illustration, not a randomly sampled or typical result.
- **F6, intervention responses.** Complete SCM sampling at 17 fixed intervention
  assignments, using 2048 observations per model and assignment. Lines show
  means; shading shows central 90% marginal predictive intervals for the
  reference SCM and M5 only. These bands are not confidence intervals for the
  mean or effect. Assignments and outcomes use observational training SDs.
- **F7, separate semantic and real panels.** Coherent-metadata T2 errors for all
  six main methods and the functioning LLM-edit adaptation. Semantic intervals
  resample five independent SCMs. Polarizer and RGB intervals resample ten-row
  contiguous reporting blocks conditional on one apparatus and frozen fitted models;
  their uncertainty scope differs. RGB is exploratory; the polarizer panel uses
  previously unused regimes of a familiar apparatus. Panels are never pooled.
  Reporting blocks are analyst-defined groups of consecutive observations, not
  independent acquisition runs; each regime contains one acquisition run.
  The two real-data panels use logarithmic error axes to display the elementary
  control and the other methods together without obscuring their differences.
- **F8, corruption and budget.** T2 error at each budget/corruption combination,
  averaging 15 independent SCMs. Confidence intervals resample systems within
  mechanism families; each system's conditions stay together. Corruption uses
  the prescribed finite edit procedure, not an assumed fraction of wrong edges
  after cancellation or reversals.

The six-method table reports controlled T2 error with SCM-cluster intervals and
separates mechanism fitting, discovery and prediction time. Prediction time
covers all final environments for a fitted model, not one environment. The reliability table
uses the same fixed-G0 comparator within every condition. Reliability is N/A for
nonrepair M0/M1/M2; their errors are still directly comparable distributionally.
Continuous-density likelihood is unavailable for M0's empirical distribution.
Aggregate graph-recovery statistics are unavailable for the predictive-mixture
methods. Some individual returned models collapse to one DAG after weighting
or audit fallback; those rows remain in the per-condition metrics, but they are
not averaged into an optimistically selected graph-recovery subgroup.
All inferential superiority statements use the corrected primary comparisons,
not overlap of the plotted marginal intervals.

`results/figure_manifest.json` binds figures to their compact numeric/graph
inputs and rendering source. `tools/check_plot_reproduction.py` rebuilds vectors,
previews and LaTeX tables from a clean curated-only copy with CUDA hidden.
