# Decisions and deviations

- 2026-10-07 UTC: retain plan defaults unless development evidence justifies a
  change. No test-informed tuning. Human scientific review remains pending.
- All work stays in sem-update on main; user pushes. Local supplied plan is
  preserved; RESEARCH_PLAN.txt is an exact copy.
- No persistent Pod mount detected. Remote work uses the existing container
  storage with local evidence mirrors under sem-update/.artifacts. This is a
  storage limitation, not a claim of durable RunPod volume storage. No paid
  storage or new resources provisioned.
- CPU checks are mathematical/software checks only. Production fitting,
  generation, neural baselines, and local model inference require CUDA.
- Actual complete GPU pilot durations: 157.57 s (5-node linear), 130.96 s
  (5-node heteroscedastic), 315.32 s (10-node heteroscedastic); all 12 candidates.
  Peak allocated flow memory approximately 0.11–0.15 GB. Defaults for flow
  architecture, fitting limits, search weights and audit thresholds retained;
  no test-driven changes or tuning among extra score configurations.
- DCDI-G uses the pinned official density-network implementation with a CUDA
  sampler and trace-exponential constraint adapter. Development grid is
  regularization {0.1, 1.0} on three separate SCMs per family. The adapter uses
  a documented augmented-Lagrangian adapter (superseded v1 settings and v2
  corrections are recorded below). It enforces the shared
  indegree bound by a reported final projection. Convergence violations and
  removed edges are reported; these are not exact paper reproduction settings.
- Real subset: six current/position variables rather than optical intensity
  sensors, to avoid omitting varying local LED causes or exceeding indegree 3.
  Documented RGB interventions only; no real unseen-target claim. Quantization,
  apparatus dependence and fixed measurement parameters are audited explicitly.
- The first Qwen download failed because the container enabled an unavailable
  hf_transfer backend. Disabled that optional backend and the identified retry
  succeeded. No credentials or alternative paid service were required.
- Development adapter v1 DCDI fits (0.1 and 1.0 regularization, first development
  SCM) both returned empty graphs and unconverged constraints. Stopped the sweep;
  retained all traces/checkpoints and archived its source. These are development
  failures, not validated baseline results. Adapter v2 follows the official
  validation-stationarity multiplier updates, starts penalty at 1e-8, resets
  RMSprop on multiplier updates, and allows 40,000 steps. A declared 4,000-step
  plateau fallback bounds delay from stochastic validation oscillations. Validate
  this version on development tasks before freezing the baseline.
- Local default Python is 3.8, below the project's supported version. A local
  test collection attempt failed on type annotations; this does not invalidate
  the successful Python 3.12 GPU tests. No local CPU result is counted as GPU work.
- Semantic synthetic policy is fixed before benchmark generation: two source
  controls, one attenuating filter, two sensors; randomly selected admissible
  source/filter-to-sensor paths, at least one source per sensor. Intensities sum
  positive sigmoid source responses and multiply by an optional filter
  transmission; independent heteroscedastic sensor noise is added. Metadata
  supplies roles, not realized paths or coefficients. This is a designed semantic
  signal, not arbitrary random DAGs given physical-sounding names.
- Real-data diagnostic permutation normalizations are explicitly descriptive;
  no calibrated p-values or independence claims are attached to them.
- DCDI v2 validation completed in 452.11 seconds with four edges at 31,800
  updates. The optimization used the normalized acyclicity threshold 1e-8;
  its first stored Boolean accidentally compared the raw constraint instead.
  Derived summaries correct this label and retain the original raw record.
  No fit, graph, or outcome was changed by this reporting correction.
- A resumability check exposed a last-checkpoint boundary: interruption after
  the final partial checkpoint but before completion could enter an empty
  update loop. Recovery now finalizes the saved best state without extra
  updates; a regression check verifies exact parameter equality.
- Development baseline jobs use a small concurrent pool on the single existing
  GPU. Each job has its own SCM data and process RNG. The runtime ledger unions
  their reservation intervals, while retaining individual timing and periodic
  utilization. LLM inference is kept separate. No speedup factor is inferred
  merely from GPU utilization.
- Main cost reporting distinguishes actual elapsed time (which depends on
  shared-cache execution order) from canonical fitting updates/time, counting
  each required node/parent-set mechanism once. Neither is a new sample count.
- The prespecified real-data bootstrap resamples contiguous ten-row blocks
  within each held-out strong RGB regime, 200 replicates with common resamples
  across methods. Trained models, projection directions and generated samples
  are fixed. These are conditional observation-uncertainty intervals, not
  independent-apparatus intervals or guarantees of causal validity.
- Real sample accounting explicitly counts the reference policy's randomized
  assignments: 6,656 reference observations plus 1,200 mid-RGB observations,
  totaling 7,856 non-test experimental rows. B=400 denotes rows per additional
  target regime only. The preliminary manifest is archived and regenerated
  before any real model fitting; no held-out outcome informed this correction.


## Full-matrix runtime decision before benchmark selection

The three-process cold-cache pilot group completed in 331.62 seconds; summed
individual durations were 719.17 seconds. This measured throughput supports
three independent controlled-dataset workers on the same GPU. The full d=5,10
matrix retains 30 controlled SCMs, five semantic SCMs and the real case. The
forecast is 38.57 remaining hours including an explicit recovery allowance;
a 52-hour planning upper bound plus 1.592 hours already used stays below 64.
Runtime_plan.json contains all assumptions and component estimates. These are
forecasts, and the ledger enforces actual interval-union time. Semantic/real
LLM-edit stages execute sequentially after the controlled worker pool.

The final 23-test suite, model preparation command and complete environment
bootstrap executed successfully. Development tuning completed before benchmark
freeze. No final benchmark outcomes were exposed when choosing this matrix.


## Figure dimensions checked against the actual venue template

The official package was retrieved successfully from the local connection after
the Pod download received HTTP 403. Its 12.2 cm text width requires compact
stacked panels with 8–9 pt text, rather than shrinking wider figures. Only figure
layout and presentation code changed after protocol freeze; the frozen
scientific implementation, split assignments and selected-model rules did not.
Marker shapes and dash patterns supplement color. The downloaded package and
checksums are retained; no final-manuscript compilation is claimed.

## Post-evaluation reporting decisions and observed limitations

- All 869 method runs completed before final-test access. The frozen scientific
  implementation hash remains `8772cd93dfb99d288bdf789a3ad0db963532214c2362cc51f86964d667b5d14f`.
  Subsequent source edits affect reporting, figure presentation and preservation
  utilities only. No fitted mechanism, prompt, selection rule, split or final
  metric was changed after exposure.
- Auditing the actual LLM-edit outputs found 84 parsed graphs containing only
  one edge, although the frozen contract required a complete graph after one
  edit. Another 18 attempts violated assigned-root constraints. The input
  incumbent uses numeric indices while outputs use V-prefixed IDs; this is an
  avoidable interface burden. All 18 conditions returned their initial graph
  without a new admissible candidate. Preserve and disclose this failed
  adaptation; do not reinterpret its edges as commands or tune the prompt on
  final outcomes. It is a limited CauScientist-inspired baseline, not a faithful
  reproduction or a test of CauScientist's published efficacy. A new interface
  needs a separately frozen future study.
- The candidate budget is a common maximum of 12 evaluated DAGs with the same
  stopping rule, as implemented before freeze. Achieved mean counts differ
  (10.58 diagnostic, 9.52 random), as do canonical fitting updates (9,047.1
  versus 7,525.4). Report this as a common candidate cap; equal achieved compute
  and compute-efficiency superiority are untested.
- The independent audit did not reduce the ten observed harmful T2 controlled
  conditions. Report that failure, the harmful uncorrupted control, the semantic
  loss and the real-case loss alongside the controlled mean improvements.
- Final reference arrays were regenerated on CUDA after evaluation from the
  unchanged frozen generators and recorded seeds, and checked against all
  original row counts and non-target means (absolute tolerance 1e-7). They were
  then preserved with generated model samples. This does not claim the original
  in-memory reference arrays were saved at the first evaluation instant. See
  final_reference_preservation.json and scripts/preserve_final_samples.py.
- Final plotting reproduction hides CUDA and copies only source/configuration
  and curated inputs. It is a presentation/reproducibility check, not an
  additional GPU experiment or opportunity to select favorable results.
