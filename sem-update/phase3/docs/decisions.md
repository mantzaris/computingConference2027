# Phase-three decisions

- All prior source, results and interpretations remain unchanged. New code is
  under src/sem_update/phase3; operational artifacts are .artifacts/phase3.
- The user's new 24-hour phase ceiling replaces no historical ledger entries:
  the maximum cumulative use is min(64, 16.09346408 + 24) device hours.
- The existing 25 MiB limit includes every earlier committed project blob.
  Full environment metrics, graphs, checkpoints and traces are preserved outside
  Git; curated figures and per-SCM results must fit the remaining 2.78 MiB.
- Phase two's linear baseline alpha=0.1, flow architecture and fitting loss,
  robust rho=0.5, ensemble tau=0.01, selection tolerance and audit/harm definitions
  are retained. This is a fresh prospective synthetic study, not new real data.
- Candidate fitting will batch compatible scalar mechanisms without parameter
  sharing. Numerical equivalence, exact parent masks, intervention replacement,
  canonical per-parent-set random streams and cache independence are tested.
- Diagnostic work is bounded prospectively: observational search data plus up
  to four seeded intervention environments, eight sampled residual peers per
  node/environment, 64 observations and 16 permutations. The historical MMD/HSIC
  normalization is retained. This approximates the earlier diagnostic schedule;
  it does not approximate the common search/calibration objective, which uses
  every environment. Diagnostic priorities are not causal significance tests.
- Fixed resources retain the historical 12-candidate/two-stall prefix. Adjusted
  resources continue exploration after stalls under frozen caps. Extra attempts
  do not force graph changes. Initial SHD, search-accepted moves and the returned
  graph's SHD/change from G0 are distinct quantities. A limited bank is not evidence
  that enough edits were attempted to recover a heavily corrupted large graph.
  The mean-normalized objective and 0.005 acceptance threshold are retained.
  Consequently, a local mechanism improvement can contribute less to the mean
  at larger dimension. Whether this limits repair is evaluated through accepted
  moves and remaining SHD; threshold rescaling is not tuned on these test systems.
- DCDI preserves the earlier optimizer's normalized constraint and stopping
  rule, but phase three also reports raw trace-exponential divided by dimension.
  The latter must be at most 1e-8 for the label `converged`. Capped predictions,
  legacy stops that fail this stronger certificate, cycle projection and indegree
  projection are reported separately. Historical convergence labels are preserved;
  comparisons must recognize that their reporting criterion differs.
- Complete pilots use an archived source version. Before the main freeze,
  refinements add nested fixed-total budgets, sealed checkpoint manifests,
  bounded parallel dispatch, exact prefix search-overhead/memory accounting,
  discovery stop/projection reasons and inference-only gradient suppression.
  Pilot timings are development evidence; main predictions will use the frozen
  revised source and fresh seeds. The original pilot artifacts are not overwritten.
- Shared group fitting time is allocated across its independent mechanisms in
  proportion to active optimizer updates. This is measured grouped execution,
  not an estimate of serial fitting speed. Logical costs charge each repair
  method its full canonical bank; actual device time unions overlapping jobs.
  Matched-prefix time includes fitting, scoring and diagnostics. Comparisons
  pair exact SCM/corruption/ceiling cells before SCM-level aggregation.
- All final PDF/SVG/PNG outputs are generated and retained in the ignored artifact
  archive. Git receives all selected PDF figures, three SVGs and one PNG preview,
  plus compact plotting inputs. This avoids spending the remaining cumulative
  blob budget on redundant image formats while retaining the complete evidence.
- The 100-node pilot exposed redundant retained likelihood-mask parameter copies.
  Ephemeral likelihood/diagnostic groups preserve target exclusion and return
  exactly identical checked densities. On 48 frozen pilot graphs and 21 masks,
  peak allocation fell from 2,985,494,016 to 181,050,368 bytes. Sampling-layer
  caches remain. This is a memory result for that probe, not an end-to-end speed
  claim. Changing source hashes also changes the recorded canonical initialization
  keys for the fresh main fits; all methods within a task still share those keys.
- Six concurrent processes gave 138.856 versus 42.432 joint density updates/s
  for one process in the bounded development probe (startup included). The main
  forecast assumes only a 2.5-fold whole-pipeline gain. Candidate caps are
  24/36/72, with 3600-second stage ceilings and a three-hour final-evaluation
  reserve. The plan attempts all 45 primary systems before optional sensitivity;
  unused resources do not authorize a new paid resource or an extension of 24 h.
- A pre-main recovery review found that a rerun with incomplete coverage could
  replace a sealed result set. The corrected runner preserves any sealed boundary,
  recovers already completed tasks before resource admission, and retains earlier
  failure records. A regression test checks that an incomplete sealed selection
  file is unchanged on resume. The final full suite passed 61 tests.
- After freezing, a CPU-only reporting check used all 162 endpoint rows from the
  three actual development pilots. Their older schema needed known budget/role
  metadata mapped from manifests; no outcomes were fabricated. The failed first
  check and its log are retained. The successful check exercises absent study
  cells as well as observed ones. Missing cells remain unavailable, and Holm
  correction retains all 24 frozen contrasts even if coverage is incomplete.
  These reporting changes do not change the frozen scientific source hash.
- The optional fixed-total sensitivity is a nested subset of the corresponding
  primary synthetic pool. The simulator recreates full role streams before
  retaining prefixes, so assignment/noise draws align exactly. Its stated budget
  counts every learner-accessible fit/early/search/calibration/audit row; unused
  simulated suffixes do not enter any fitting or selection partition. It is a
  data-availability sensitivity, not a claim that fewer physical acquisitions
  were performed. These two datasets add no independent SCMs.
- The deep profile uses a fixed unlabeled chain-plus-second-predecessor skeleton
  with fresh label permutations, mechanisms and disturbance streams. Its five
  SCMs are independent mechanism/data systems, not five different unlabeled deep
  topology families. Conclusions for that profile must retain this limitation.
  The graph-only frozen-design audit found 45 distinct labeled graphs and no
  collisions among 4,370 checked generator/partition/target random streams.
- Columns named `true_response_rms` and `true_descendant_response_rms` use
  empirical means from 2,048 observations drawn from the reference SCM per final
  environment. They estimate the true response; they are not analytic population
  effects. Independent reference observational/intervention samples introduce a
  Monte Carlo floor, including for non-descendants. Report this separately from
  model predictive intervals and SCM-level uncertainty.
- A separate CPU watchdog bounds the coordinator's verified process group with
  a two-minute margin inside the 24-hour ceiling. This closes a wrapper-level
  gap for a long prediction call between budget checks. It does not alter the
  frozen scientific configuration, fit limits, samples or selection rules.
  CPU-only reporting may finish after GPU work is quiescent. Owner verification
  and guard status are retained under `runs/budget_guard*.json`; any actual
  budget interruption remains a resource outcome, not a numerical method failure.
- The 3,600-second per-stage limits are checked at completed search-round or
  discovery-block boundaries. A final atomic unit and graph projection can make
  measured stage time exceed that nominal threshold. Report actual elapsed time
  and cap status; do not equate the nominal threshold with exact consumed time.
  The separate phase watchdog enforces the overall authorized maximum.
- The final phase-three prediction matrix retains the six main methods, fixed
  flows, random repair, the oracle subset and matched-compute prefixes. The
  rho=0, tau=0 and uniform choices remain computed and audited in selection records,
  but separate final predictions for these optional phase-two ablations are not
  part of this scaling matrix. Large-graph results therefore cannot isolate the
  anchor penalty's effect from ensembling itself. M3 versus M4 still isolates
  the frozen robust selection rule on the same bank.
- Intervention-visible coverage is fixed at 20% in the primary design. Its
  absolute target count and total observation count grow with dimension. Neither
  that comparison nor the optional fixed-total subset identifies the effect of
  changing the visible fraction itself; other coverage fractions remain untested.
- Long graph paths do not guarantee large long-range responses. The bounded,
  scaled mechanisms can attenuate effects along a deep path. Descendant counts
  describe graph reachability; measured response magnitudes describe how much
  those outcomes change. These quantities must not be used interchangeably.
- M1 and the repair methods receive a corrupted prior; DCDI discovers a graph
  from observations, intervention labels and the common indegree constraint.
  This compares their specified prediction procedures with different prior
  information. It is not an information-matched test of de novo discovery.
  DCDI's existing optimizer adaptation, strict constraint certificate, resource
  caps and graph projection must remain explicit when interpreting its results.
- The first final-evaluation attempt failed on 8 October at CSV serialization:
  T1 rows lack the optional T2 projection-sensitivity fields, but the original
  writer used only the first row's keys. No numerical calculation or model failed.
  `tools/evaluate_frozen.py` supplies a union-of-row-keys export adapter, retaining
  blank missing values and the original precision. The frozen scientific source,
  protocol, selected models, metrics and prediction cache identities are unchanged.
  A regression test covers mixed endpoints, missing values and atomic repeatable
  export. The failed attempt, partial CSV and coordinator state are preserved;
  compatible completed predictions are reused on the bounded resume. This is a
  disclosed post-freeze serialization repair, not a new model-selection opportunity.
- Oracle-flow results use only the prespecified first SCM in each family/profile
  cell. Their point estimates are retained, but aggregate oracle confidence
  intervals are marked unavailable: resampling one system per stratum would give
  a degenerate interval, not zero scientific uncertainty. Main-method intervals
  and the frozen 24-contrast family are unchanged.
- Visual review found coincident labels in the spring layout of a declared
  100-node local neighborhood. `tools/refine_figure_layout.py` retains the exact
  node subset and its order but gives local nodes separated circular positions,
  shared by every method panel. Whole-graph layouts, edges, weights and all
  numerical results are unchanged. Original figures, graph-layout JSON and
  reproduction records are retained under `paper/pre_visual_review/` in the
  ignored evidence. The harm-frequency axis is scaled to its observed confidence
  bounds from zero so rare events are readable. Final figures are reproduced
  again after these presentation-only changes.
