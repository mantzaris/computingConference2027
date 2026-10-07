# Phase-two protocol: selection reliability from a common fitted bank

This is a follow-up informed by the adverse semantic/real results in commit
ad21e60. It is not a reproduction of the historical 0.09927 controlled error.
The earlier source, metrics and interpretation remain unchanged. Alex's
scientific review is pending. The frozen machine-readable protocol and hashes
in `results/protocol.json` govern the executed matrix.

## Units, splits and budgets

The minimum controlled matrix is 15 fresh five-node SCMs: five linear, five
nonlinear additive and five nonlinear heteroscedastic systems. Graph, mechanism
and data seeds start at 211001, 212001 and 213001 respectively. Each has B=100
and 400 intervention observations per seen target, and prior-corruption fractions
0.2 and 0.5, producing 60 settings. The unchanged generator and corruption
operators are reused with new seeds. The corruption seed is SCM seed + 37 +
1000 times the fraction. Only construction/evaluation sees reference graphs.

Three targets are assigned independently of graph structure. Each has a normal
assignment centered one observational training SD above its training mean,
with SD 0.25 training SD. B is divided fit/early/search/calibration/audit as
50/10/20/10/10 percent. These five partitions use independent noise streams;
the two budgets use nested prefixes within each role. Their total is 3B,
not just the fitting subset. Observational role sizes are 4096/1024/1024/512/512.
Only the observational fitting set defines standardization. All mechanisms use
the historical environment-balanced conditional negative log likelihood and
exclude rows intervening on that node. Diagnostic scores do not enter that loss.

T1 uses 2048 new observations per familiar target/setting. T2 uses 2048 at the
opposite assignment center, one training SD below the training mean, and is
primary. T3 uses 2048 at the positive setting on the two unseen targets. Distinct
role/endpoint RNG streams and row IDs prevent overlap. A separate 1024-row
observational final sample defines reference means for effect error. All methods
generate 2048 complete observations per environment, including mixtures.

Three independent development systems (290001/291001/292001) select a single
ridge alpha from {0.001,0.01,0.1,1}; the measured choice is 0.1. Two independent
timed pilot systems, 295001 linear B100 and 295002 heteroscedastic B400, exercise
the complete six-method pipeline and optimizer grid validation. Their final
outcomes are development evidence only. No main final observations are opened
until protocol, source, splits and every selected model are frozen.

## Six main methods

M0 is an empty-graph product of empirical marginals fitted only to observational
fitting data. It independently resamples each non-target marginal and replaces
intervention targets. It has no continuous density; NLL is unavailable.

M1 is a ridge linear Gaussian SEM on the same supplied G0 as repair. Independent
standard-normal disturbances, an unpenalized intercept and a 1e-4 residual
variance floor define its mechanisms. Eligible environments receive equal
weight. Regression and intervention generation run on CUDA. No oracle graph
is supplied to this baseline.

M2 is **DCDI-DSF + common flows**. Its official density implementation is pinned
at `594d328eae7795785e0d1a1138945e28a4fec037`. Device-local Gumbel draws and a
device context for two upstream tensor allocations enable current CUDA without
changing the DSF/Jacobian equations. CPU/GPU density and gradient equivalence is
tested. The historical augmented-Lagrangian CUDA training adapter uses known
perfect targets, the same fit/early observations and justified root constraints.
The DSF has two flow layers of width eight, a two-layer width-64 conditioner,
RMSprop 0.001, and the recorded step ceiling. Discovery cost and common-flow
refitting cost are separate. Strict normalized DAG convergence (1e-8), any
threshold/cycle/indegree projection and capped fits are reported explicitly.
Nonconvergence is not silently equated with a successfully optimized baseline;
strict-convergence sensitivity comparisons accompany full-budget results.

M3 reuses the historical flow architecture (two conditional rational-quadratic
splines, eight bins, width 64), node-local canonical fitting, exact parent masks,
disturbance scheduling, graph operations and search objective. The search cap is
12 distinct graphs, four rounds, three candidates per round, with two stalled
rounds stopping search. Every fourth diagnostic proposal is globally random.
The fitting cap is 1000 Adam updates per parent set with early stopping. An
immutable bank is built using only fit, early and search. A procedural refinement
then selects its best average **calibration** objective, requiring improvement
of at least 0.005 over G0. This does not reproduce historical search selection.

M4 uses precisely the same bank, including G0. For intervention environment e,
Delta_e(G)=S_e(G)-S_e(G0). It minimizes
`(1-rho)*mean(Delta) + rho*max(Delta)`, with rho=0.5. G0 is retained unless the
score improves by at least 0.005. A rho=0 control must reproduce M3. The
per-environment score is constructed to preserve the original objective:
if m_j environments leave node j intact, its shared observational term is
sum_j loss_obs,j/(d*m_j); the intervention term for e is
K*sum_intact_j loss_e,j/(d*m_j). Add shared complexity 0.02|E|/d and that
environment's SW1. Averaging over K interventions exactly reconstructs the
node/environment-balanced NLL + mean SW1 + complexity objective.

M5 shortlists G0 and at most two other distinct graphs with the best **search**
scores, before calibration access. It predicts a mixture of complete SCM
intervention distributions. A single nonnegative unit-sum weight vector is
estimated per task and frozen for all final settings/targets. The calibration
objective is an equal-environment energy score plus `0.01*(1-w_G0)^2`.
Distances use standardized non-target outcomes and divide by sqrt(outcome count).
Fixed 512-sample component draws give matrices a (component-to-observation
distances) and B (component-to-component distances), yielding
`w'a - 0.5*w'B*w + tau*(1-w_G0)^2`. SLSQP uses analytic gradients and deterministic
starts; development solutions are checked against a 0.005 simplex grid.
Tau=0 and uniform-weight controls are included. Each generated observation
selects **one** component graph for all its nodes. The weights are predictive
combination weights, not posterior causal probabilities. A highest-weight
graph may be shown only as a labeled representative, never an averaged DAG.

## Common audit, controls and accounting

Each selected single model or mixture is persisted before one audit comparison
against G0. Pass requires SW1 <= 1.05*initial SW1 + 0.001 and NLL <= initial NLL
+ 0.05. Audit NLL uses the truncated **whole-joint** density divided by the
number of intact nodes, then equal weighting over environments, for all methods.
Mixture logsumexp combines component joint densities before normalization.
This audit normalization refinement is disclosed separately from the preserved
selection score. Rejection returns G0; it never triggers another candidate.

Fixed-G0 flows and random-priority repair are essential controls. Random search
starts from the same initial candidate set, uses the same fitting/search caps
and calibration-average selection, and has its own bank. Prespecified completed
prefix checkpoints compare diagnostic/random policies at matched ceilings for
canonical fitting updates and measured canonical fitting time. No cheaper
later candidate can be skipped into a prefix. Coverage and achieved cost below
each ceiling are reported; fitting-time curves are not labeled total-method
time. Candidate counts alone are not evidence of equal computation.

M3/M4/M5 each pay the full logical bank construction cost plus their own
calibration/audit and prediction work. Shared cache execution savings are
reported separately as actual incremental job times. Node cache keys include
dataset and fit/early hashes, ordered parents, preprocessing, architecture,
optimizer configuration, source/dependency versions and device type. Each
parent set has a deterministic canonical seed and reusable complete checkpoint.

The runtime ledger copies intact historical records (10.318525 device hours)
into the separate phase-two artifact root. New intervals are unioned on the
single GPU, including tests, pilots, development, failed attempts, LLM work and
final computations. The additional cap is 16 device hours and does not authorize
new resources. No CPU replacement is allowed for GPU experimental stages.

## Semantic, real and LLM panels

Five fresh semantically grounded optical synthetic systems (241001–241005),
B100, use coherent, anonymous and shuffled metadata. Roles precede graph draws;
three independent source/filter controls affect two noisy sensor variables.
Each task begins with actual frozen Qwen3-8B graph proposals plus a fit-only
linear-BIC initializer; G0 is their best common search score. All applicable
methods receive that same G0. An LLM-edit adaptation uses the same flow verifier,
legal add/delete/reverse menu and search-only feedback. It is inspired by
CauScientist, not a reproduction of its published procedure or scores.

The historical raw-generation audit separately counts output and verifier
failures. The fixed interface asks for legal edit IDs, avoiding the ambiguous
full-DAG versus isolated-edge contract. Real generations, prompts, revision,
seeds, malformed/invalid/cycle/duplicate/no-change/new-edit counts and subsequent
score rejections/accepted changes are retained. Controlled parser fixtures are
software tests, not LLM generations. LLM inference and flow fitting use separate
stages; model weights stay frozen and never receive audit/test/reference graphs.

The Causal Chambers case retains red, green, blue, the `current` readout, polarizer
motor pol_1 and angle_1 readout. Independently assigned roots are red/green/blue/
pol_1. Sensor gain and oversampling settings must remain fixed. Measurement-
parameter interventions are excluded. The previously unused pol_1 mid/strong
regimes provide a separate new-regime panel. Strong polarizer outcomes are
sealed until evaluation. These files were schema/checksum inspected in phase
one but never fitted or outcome-scored; the apparatus and design are familiar.
This is not independent-apparatus replication. Previously evaluated RGB final
regimes are explicitly exploratory even after changing splits.

Reference acquisition ranges are fit[0,3400), early[4200,5224), search[5330,6354),
calibration[3500,4012), audit[6460,6972), final[7100,8124). Each mid intervention
uses fit[0,200), early[304,344), search[408,488), calibration[656,696),
audit[552,592), T1[760,1000). Strong T2 uses [0,1000). The source protocol takes
one measurement per assignment; ten-row groups are analyst-defined contiguous
reporting blocks, not independent experimental runs. Each regime has one
acquisition run. Non-test roles occupy separated within-run segments; the new
T2 regime comes from a separate acquisition file. Splits preserve reporting-block
identities and guard gaps: no reporting block is shared between roles.
Some fitting/validation segments contain partial edge blocks; all real T2
bootstrap segments contain complete ten-row blocks. All 6472 non-test reference-policy rows plus
1600 targeted rows count: **8072 intervention observations**, not 1600 alone.

Logged motor positions do not match the documented 0.1-degree assignment grid.
Motor predictions therefore condition on the recorded firmware-quantized
assignment setpoints, with identical assignment draws for every method. This
uses target design values, never held-out outcome responses. Source hashes,
role row hashes, measurement settings and dequantization are recorded. Temporal
dependence and one-apparatus scope remain limitations. Real T3 is unavailable.

## Outcomes and uncertainty

Primary error is macro T2 sliced Wasserstein over the joint standardized
non-target outcomes, with 256 deterministic projections. Also report T1/T3,
energy score/distance, mean effect RMSE, worst-regime SW1, marginal 50/90-percent
predictive coverage and width, graph recovery where meaningful, initial-model
retention, costs, VRAM, fitting updates, failures and coverage. Mixture graph
recovery is unavailable; representative graphs are descriptive only.

Harm uses the historical definition: returned T2 error exceeds the fixed-G0
flow error by more than max(0.001, 5 percent of fixed error). A symmetric decrease
is beneficial. Report before/after audit, harmful count, positive excess and
maximum deterioration. Harm is N/A for nonrepair M0/M1/M2; common-reference
deterioration, if shown, is labeled separately.

Paired uncertainty resamples independent SCM clusters, stratified by mechanism
family, retaining all budgets/corruptions/methods together. Conditions, generated
samples and metadata variants are not independent systems. Use 2000 bootstrap
replicates. The 15 six-method pairwise primary comparisons use paired SCM-level
sign randomization and Holm correction; no unadjusted formal superiority
claims. Sign randomization assumes sign exchangeability of paired SCM
differences under its null; it is not a distribution-free test of an arbitrary
mean-null distribution. Bootstrap intervals can degenerate at zero observed
harm and do not rule out harmful repairs on new SCMs. Semantic and real panels
are never pooled into the controlled average.
Real block intervals describe observation uncertainty conditional on this one
apparatus and fitted models, not full causal/training uncertainty.

Report best observed mean prediction, reliable repair and computation tradeoff
separately, with ties/uncertainty. Neither proposed extension is required to win.
The response/graph illustration uses the median M3 paired change among d5/B400/
c0.5 cases; an adverse example uses the largest harmful M3/M4/M5 change if any.
All figures use reproducible vector plotting and compact actual-run tables.
