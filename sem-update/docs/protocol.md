# Frozen computational protocol for scientific review

The machine-readable authority is `results/curated/frozen_protocol.json`, with
the split summary in `split_manifest.json`. Alex's scientific review remains
pending. This document explains the implemented estimands and limits; it does
not certify the physical truth of a returned graph.

## Mechanisms and interventions

For each node, the mechanism is
\(X_j=T_{\theta_j}(U_j;X_{\mathrm{Pa}(j)})\), with mutually independent standard
normal disturbances. Two monotone rational-quadratic spline transforms, each
with eight bins, and a conditional affine transform parameterize the scalar
noise map. The conditioner has two 64-unit SiLU layers and receives exactly the
ordered parent columns. Roots have learned unconditional parameters. Parameters
are independent across nodes and shared across all intact environments.

Topological sampling evaluates each mechanism only after its parents. A perfect
intervention replaces the target mechanism with the declared assignment law;
it does not condition on a realized target value in the observational model.
The target mechanism is not evaluated in an intervention likelihood. For intact
nodes, inverse noise and the inverse-Jacobian log determinant give their
conditional log density. Independent disturbances and the triangular structural
map give the usual product of intact conditional factors. This is standard SCM
and change-of-variables reasoning, not a new identification result.

The optional counterfactual software path abducts each factual disturbance and
reuses it after replacing target mechanisms. Only analytic software checks are
claimed. Real individual counterfactual accuracy is not evaluated, and monotone
scalar-noise coupling imposes assumptions beyond intervention-distribution fit.

## Fitting and graph selection are different objectives

For node \(j\), let \(\mathcal E_j\) contain the non-targeted fitting environments.
The fitting loss is

\[
L_j=-\frac{1}{|\mathcal E_j|}\sum_{e\in\mathcal E_j}
       \frac{1}{n_e}\sum_i\log p_{\theta_j}(x_{ij}^{(e)}\mid x_{i,\mathrm{Pa}(j)}^{(e)}).
\]

A minibatch samples an eligible environment uniformly, then a row uniformly.
Each node uses Adam, learning rate 0.001, weight decay 0.00001, batch size 256,
at most 1,000 updates, and early-stop evaluation every 50 updates with patience
five. The best early-stop state is retained. Diagnostics do not enter this loss.

On the separate search split, every candidate uses the common score

\[
S(G)=\operatorname{NLL}_{\rm balanced}(G)
     +\operatorname{SW}_{1,\rm intervention}(G)+0.02|E_G|/d.
\]

The NLL first averages within environment, then across eligible environments
for each node, then across nodes. The intervention term averages joint
non-target sliced-Wasserstein distances across intervention environments.
Search uses 512 generated samples, 64 fixed random projection directions and
512 midpoint quantiles. All coordinates are standardized using observational
fitting data alone. This weighted score is the declared verifier, not an
unweighted full-data likelihood or a calibrated causal posterior.

## Disturbance-guided scheduling and bounded edits

Search-split inverse disturbances supply three scheduling components:
cross-environment marginal MMD, disturbance-parent HSIC, and dependence between
intact disturbance pairs. Targeted nodes are omitted in their intervention
environments. At most 256 rows per environment and 32 permutations are used.
Scalar kernels mix bandwidths 0.5, 1 and 2; standardized parent kernels use
bandwidth equal to the square root of parent count. Each statistic is centered
and scaled by its permutation reference, then clipped below at zero. These
scores are priorities, not calibrated p-values. Real-data row permutations are
descriptive because temporal dependence may remain.

Only acyclic add/delete/reverse moves with maximum indegree three are legal.
Known independently assigned roots cannot receive incoming edges. Priorities
sum over affected child mechanisms. Every fourth proposed candidate is drawn
globally at random; the other slots follow diagnostic priority. The random
baseline uses the same legal neighborhood, fitting configuration, verifier,
maximum candidate count and stopping rule.

Each run can evaluate at most 12 distinct DAGs, including starting DAGs, in at
most four rounds with three new candidates per round. A score decrease of at
least 0.005 is required; two stalled rounds stop search. The common cap does not
force identical achieved node-fit counts or wall time. Fixed graphs naturally
cost less, and shared caching changes incremental cost. Both actual and
canonical required optimizer updates, parent-set fits and times are reported.

The initial graph is the best search-scored starting DAG. Before audit, the
initial and selected candidates are committed to an audit-candidate record.
Exactly one comparison on the audit split permits the repair only when its
SW1 is at most 1.05 times initial SW1 plus 0.001 and its NLL is at most initial
NLL plus 0.05. Otherwise the run returns its initial graph. This rule is a
safeguard, not a guarantee against final-test harm.

## Canonical mechanism reuse

Cache identity includes dataset checksum, exact fitting and early-stop splits,
node, ordered parents, preprocessing, model family, architecture, optimization
configuration, software versions, device type, and mechanism/training source
hashes. The canonical initialization and minibatch seed is derived from that
complete identity and recorded. An unchanged parent set loads identical fitted
parameters, regardless of graph-search path or which comparison ran first.
Reversals can change two parent sets. Changed parent sets receive canonical
training rather than path-dependent warm starts. Optimizer/RNG checkpoints and
failed attempts remain in ignored artifacts.

## Independent units and data roles

The controlled study has 30 independently sampled SCMs: five per mechanism
family and graph size, for three families and sizes five and ten. Budgets 100
and 400 and corruption fractions 0.2 and 0.5 are paired conditions within each
SCM. Nominal corruption is a balanced sequence of valid edit types; realized
initial structural Hamming distance is also reported. These are constructed
corruptions of synthetic reference graphs, never labeled as LLM generations.

Each SCM has 4,096 observational fitting rows, 1,024 early-stop rows, 1,024
search rows and 512 audit rows. The intervention budget per seen target is split
60%/10%/20%/10% across those roles. There are three seen targets at d=5 and six
at d=10. Thus total non-test intervention rows are respectively 300/1,200 and
600/2,400 at the two budgets. Smaller-budget rows are nested prefixes within
each role. Split identifiers and generated arrays are checksum-verified.

Five separate semantic SCMs use roles fixed before random graph and parameter
draws: two source controls, a filter, and two noisy light sensors. Admissible
source/filter paths are random; metadata does not reveal the realized parents
or coefficients. Each instance uses B=100 and the same data under coherent,
anonymous and shuffled descriptions. Known intervention-root constraints remain
available in every metadata condition.

The real case uses the audited Causal Chambers RGB/current/polarizer/position
subset. Its randomized reference data are experimental observations, so the
real budget counts all 6,656 non-test reference rows plus 1,200 additional
mid-RGB rows: 7,856. Acquisition blocks and gaps remain distinct across roles.
`docs/dataset_audit.md` records assignment laws, fixed measurement settings,
dequantization and causal limitations. B=400 denotes the additional rows per
RGB target regime and is not the total real-data budget.

## Actual LLM and other baselines

The frozen, revision-pinned Qwen3-8B runs locally in BF16 entirely on CUDA,
separately from flow fitting. Each metadata condition requests two initial
graphs, with at most one schema-repair retry per graph. Non-thinking decoding
uses temperature 0.7, top-p 0.8, top-k 20 and at most 2,048 new tokens. Invalid
outputs are retained. A fit-observational greedy linear-Gaussian BIC start is
always available; duplicate initial graphs are fitted once.

The CauScientist-inspired LLM-edit adaptation receives the current graph,
search-score components and edit history. It can propose at most three legal
single-edit candidates per round through an actual local generation, with the
same verifier and cap as diagnostic repair. It receives no audit/test outcomes,
reference graph, dataset name, source paper or generator code. Its rejection
records, query counts and runtime are retained. This is an adaptation, not a
reproduction of CauScientist's reported scores. Metadata anonymization cannot
rule out model pretraining familiarity with the real apparatus.

Other baselines are fixed-graph flows, random-priority repair, data-only
initialization plus diagnostic repair, official-network DCDI-G discovery with
the documented CUDA adapter followed by flow refitting, simpler neural
homoscedastic additive-noise SEMs, and synthetic oracle-graph flows. Oracle
graphs supply a structural reference, not a guarantee of best finite-sample
prediction. DCDI regularization was chosen from 0.1 and 1.0 using 18 fits on
separate development SCMs; selected value 0.1. Convergence and any final
cycle/indegree projection are disclosed. No reference graph or final-test
outcome selected this value.

## Final prediction, uncertainty and harmful repair

After every model selection is frozen, T1 tests new samples at the seen
intervention setting, T2 tests the opposite setting on seen targets, and T3
tests unseen targets. Synthetic fitting settings have standardized mean +1;
T2 mean is -1; stochastic assignment standard deviation is 0.25. Synthetic
tests use 2,048 independent true samples per intervention environment, 1,024
observational test samples, and 2,048 generated samples per fitted graph.
Final SW1 uses 256 projections. Energy distance, marginal distances, mean and
variance errors, mean-effect error, and predictive coverage/width are secondary.
Finite Monte Carlo mean-effect estimates are not exact analytic effects.

The primary endpoint is macro joint non-target T2 SW1. The two primary paired
comparisons are diagnostic repair versus fixed graph and versus random repair.
Two thousand paired bootstrap replicates resample independent SCMs within each
family/size stratum; paired budgets and corruptions stay within their SCM.
Semantic comparisons use five independent semantic SCMs. Secondary comparisons
are descriptive, without multiplicity-adjusted significance claims.

Real T1 uses later held-out rows from mid-RGB regimes; T2 uses the actual strong
RGB regimes. There is no real T3 claim. Its 200 bootstrap replicates resample
contiguous ten-row blocks within strong regimes, with common resamples across
methods and fixed models, projections and generated samples. These are
conditional observation-uncertainty intervals for one apparatus, not
independent-apparatus or full training-uncertainty intervals.

A repair is harmful when final T2 SW1 increases by more than
max(0.001, 5% of initial SW1); a symmetric decrease is beneficial. Other changes
are neutral. Report before-audit and returned-graph outcomes separately. A
five-SCM uncorrupted heteroscedastic control tests inappropriate repair.
Predictive quantiles, SCM bootstrap intervals, effect magnitudes and unmeasured
optimization-seed graph stability are distinct quantities.

The illustrative synthetic graph/response case is the median paired T2 change
among d=5, B=400, corruption=0.5 cases, with run-ID tie breaking. An adverse
example is the largest harmful change if any occurs; otherwise a rejected
repair may illustrate the audit. This presentation rule does not select models,
seeds, metrics or favorable headline results.
