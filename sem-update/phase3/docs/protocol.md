# Phase three: prospective scale and structural complexity

This phase investigates the earlier findings, without assuming their persistence.
Phase one's adverse semantic and real results and phase two's accuracy/reliability
tradeoff remain unchanged. The authoritative executed configuration, task list,
source hashes and freeze time will be recorded in results/protocol.json after
three complete independent timed pilots. No main final outcomes inform that freeze.

## Systems and environments

Study A proposes five independent SCMs in each of six cells: d=20,50,100 crossed
with nonlinear additive and nonlinear heteroscedastic mechanisms. Each has two
corruptions, 0.2 and 0.5. Study B proposes five heteroscedastic 50-node SCMs each
for dense, hub and deep profiles, also with two corruptions. This is 45 independent
SCMs and 90 prior settings; resource policies do not create independent systems.
SCM seeds are in runner.main_tasks; development uses disjoint 390xxx/399xxx seeds.

Every graph is weakly connected. Sparse graphs give each successive node two
uniformly sampled predecessors (one for the second node), yielding 2d-3 edges.
Hub graphs match that edge count, with heterogeneous indegrees up to six and
preferential outgoing attachment. Deep graphs also match 2d-3 edges and connect
the preceding one/two nodes, giving depth d-1. Dense graphs use up to seven
predecessors, intentionally increasing density. Labels/columns are independently
permuted. Graph constraints are max indegree 3/6/8 for sparse-or-deep/hub/dense,
respectively, consistently applied to corruption, repair and discovery projection.

Signed smooth parent terms choose tanh, sine or x/(1+|x|), divided by sqrt(indegree).
Selected signed pair interactions multiply bounded tanh terms and divide by the
square root of the number of pairs. Nodes have different intercepts, coefficients
and functions. Additive noise SD is 0.4–0.7; heteroscedastic SD is
0.25 + 0.65 sigmoid(signed bounded parent combination). Independent standard-normal
disturbances, causal sufficiency and perfect known-target interventions hold.
Nonfinite observational draws, SD <0.05 or maximum absolute observation >50 are
numerical rejections, retained without replacing seeds based on method outcomes.

Visible targets are a seeded uniform 20% subset independent of graph/method
outcomes. The same number of uniformly chosen unseen targets forms T3; other
unseen targets remain unused. All variables remain observed. The initial budget
is B=400 per visible target: fit/early/search/calibration/audit = 50/10/20/10/10%.
Total non-test targeted observations are 1,600/4,000/8,000 at d=20/50/100.
Observational counts stay 4096/1024/1024/512/512. Only observational fitting data
set the means/SDs. Hashed role-and-target seeds avoid seed collisions at d=100.
T1 uses new draws at N(+1,0.25²); T2 uses N(-1,0.25²); T3 uses N(+1,0.25²) on
unseen targets. Final observations and predictions use 2048 rows per environment.

## Methods and resource policies

M0 empirical independent marginals, M1 ridge on G0 (alpha=.1, variance floor
1e-4), M2 official DCDI-DSF plus common RQS flows, M3 average calibration selection,
M4 robust mean/max selection (rho=.5), and M5 anchored predictive mixture (tau=.01)
retain their phase-two meanings. Fixed-G0 and random repair remain controls.
Oracle flows are prespecified for replicate zero in each size/family/profile cell.
The oracle graph never enters a repair candidate bank or baseline constraint.

The unchanged flow uses two RQS transforms, eight bins, two width-64 hidden
layers, Adam .001, batch 256, up to 1000 updates, and early checks every 50 with
patience five. Compatible nodes are fitted in groups with separate parameters,
seeds, minibatch streams and stopping states. The loss is the historical
node/environment-balanced conditional likelihood, masking targeted mechanisms.
Group execution does not imply shared causal disturbances or parameters.

All parent-set keys include fit/early identities, preprocessing, node, canonical
parents, fitting configuration, software and implementation hashes. Completed
mechanisms are reused intact; changed parents get canonical fresh initialization.
Per-mechanism fitting time is an allocation of measured group elapsed time,
proportional to active updates, rather than an estimate of serial execution time.
Input-weighted updates and group sizes are retained in full records.

Diagnostic scheduling preserves MMD, parent HSIC and residual-pair HSIC with fixed
kernels and permutation normalization. To bound work, its approximation samples
up to four intervention environments, eight residual peers per node/environment,
64 rows and 16 permutations from frozen seeded streams. Observational data are
always included. The score still uses every search/calibration/audit environment.
These diagnostics remain descriptive scheduling heuristics, not causal tests.

The fixed policy retains the historical 12-candidate cap and two-stall stopping
prefix. The size-adjusted bank continues exploration after stalls with provisional
24/36/48 candidate caps, without forcing acceptance. Both are prefixes of the same
search-only bank; all are constructed before calibration/audit access. Pilots
will determine final candidate/time/update ceilings. All edits obey exact DAG
and parent constraints. Graph descriptors are enumerated without constructing
thousands of unnecessary full DAG objects.

The measured-pilot decision uses 24/36/72 adjusted candidates at d=20/50/100,
six worker processes on the same physical GPU, 3600-second ceilings for each
discovery and bank stage, and the unchanged 60000 discovery-step cap. A three-hour
device allowance is reserved for final evaluation/illustrations. The full planned
matrix remains 45 primary SCMs/90 prior settings, with two optional fixed-total
datasets on existing SCMs. The conservative forecast is approximately 23.93 phase
hours including pilots and the reserve, below the hard 24-hour ceiling. Task
admission and checkpoint guards enforce that ceiling if the forecast is optimistic.
Primary size/family replication runs before complexity profiles and optional
sensitivity. Exact ceilings and prospective forecast are in configs/main.json
and results/runtime_forecast.json; the latter uses no main predictive outcomes.

M3/M4/M5 share the immutable fitted bank for each policy. Selection decomposition,
0.005 tolerance, mixture shortlist, fixed-sample equal-environment energy score,
whole-observation component selection and joint mixture likelihood retain phase
two's tested semantics. A single audit requires SW1 <=1.05 initial +.001 and
joint NLL/intact-node <= initial +.05. Failure returns G0 without a second candidate.
Positive mixture weights are retained even when tiny. Weights are predictive
combination weights, not causal posterior probabilities.

DCDI retains the pinned official DSF density and phase-two augmented-Lagrangian
optimizer adaptation. An algebraically equivalent batched conditioner omits
unused per-layer nonzero-weight telemetry; density and gradients are tested
against upstream. Width, flow layers and regularization are unchanged. Both
legacy dense-exponential-normalized constraint and raw constraint/d are recorded.
The legacy stopping rule is preserved, but strict convergence in this phase
requires raw constraint/d <=1e-8. A projected, capped DAG with valid predictions
is distinguished from strict convergence, missing predictions and numerical failure.

Each repair method is charged the full canonical bank cost plus its selection,
audit and prediction costs; shared actual execution is separate. Discovery and
common-flow refit costs are separate. Diagnostic/random completed-prefix analyses
use matched update and measured fit-plus-search/diagnostic-time ceilings, with
achieved costs and paired-case coverage reported. Both policies must have a
completed prefix under a ceiling to enter that matched comparison. Total logical
method time also includes calibration/audit; prediction time is reported separately.

## Evaluation and uncertainty

T2 joint non-target SW1 with 256 deterministic projections is primary. Report
T1/T3, marginal W1, energy score/distance, mean-effect error, coverage/width,
worst regime, graph recovery, harms, retention, costs and failures separately.
Synthetic truth appears only in generator/prior construction, explicit oracle
fitting, and isolated evaluation. Descendant and non-descendant errors, response
magnitude, and descendant counts/fractions reveal dilution in large joint metrics.
Empty descendant subsets are unavailable, not zero error. A prespecified first
replicate per cell also uses 64/1024 projections for sensitivity.

Harm is unchanged: returned T2 exceeds fixed-G0 T2 by more than max(.001,.05*fixed).
It is N/A for nonrepair methods; their common-reference differences are distinct.
SCM-cluster bootstrap retains corruption/resource/method pairs; n=5 cell intervals
are descriptive and individual system points are shown. Primary contrasts are
M3-fixed, M3-random, M3-M4 and M3-M5; any formal tests apply Holm across declared
study strata and contrasts. No per-observation pseudo-replication is permitted.
For zero observed harms, a percentile bootstrap can degenerate at zero. Report
the one-sided 95% bound 1 - 0.05^(1/n) for the probability that an independent SCM
has any harmful tested condition, with n independent SCMs. This system-level
bound is distinct from the reported condition-level frequency and does not imply
zero population risk.

Representative graphs use the first seed per size/family, high corruption and
adjusted resources. A local view uses the lowest labeled visible intervention
target with at least one true descendant and its two-hop undirected neighborhood, capped at 15 nodes by distance
then label. Positions are shared; an M5 representative is explicitly labeled.
Response curves use this fixed target and its lowest labeled direct child;
reference information chooses illustration only. If the plotted outcome is
outside the capped local view (possible for the adverse case), it replaces the
last node. This fixed child rule makes the illustrated direct response readable
without selecting a favorable method outcome.
An adverse example, if any, uses maximum observed harmful excess among M3/M4/M5
under adjusted resources. Within that condition it uses the T2 environment with
the largest SW1 deterioration versus G0 and the non-target outcome with the
largest mean-effect error. It is labeled as selected after evaluation.
Predictive intervals, SCM confidence intervals,
mixture weights and effects remain visually distinct.

## Preservation, prior scope and review

All operational evidence stays under ignored .artifacts/phase3. Remote overlay
storage is not durable; a SHA256-verified local ext4 preservation copy is required
before reporting preservation. No evidence deletion, new paid resources, push,
submission or Pod termination is authorized. The new ceiling is 24 additional
device hours including tests/pilots/failures, within the original cumulative 64.

This is a scalability/reliability investigation, not a claim of first use of
flows, robust selection or predictive mixtures. See the source-linked
[prior novelty review](../../phase2/docs/novelty.md) and its historical references.
The earlier semantic and real cases remain separate; no apparatus data are
expanded or repackaged as fresh high-dimensional observations. Alex's scientific
review of protocol, assumptions and conclusions remains pending.

The [official venue rules](https://saiconference.com/Computing/CallforPapers),
rechecked 8 October 2026 UTC, retain the October 15 AoE deadline, anonymous PDF,
150–250 word abstract, 18 main pages plus up to seven reference/appendix pages,
official formatting, GenAI disclosure and human accountability. This record does
not assert author review, submission eligibility, acceptance or indexing.
