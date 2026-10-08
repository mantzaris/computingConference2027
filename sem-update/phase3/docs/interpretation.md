# Interpretation for scientific review

The earlier M3 accuracy finding persists as an **observed average** at 20 and 50
nodes and on hub/deep 50-node profiles. It does not persist as active repair at
100 nodes: M3/M4/random all return the initial model, even with substantially
expanded search. M5 retains the best observed harm record, but its large-graph
predictions are very close to G0. These results support a qualified
accuracy/reliability tradeoff, not a scale-independent success claim.

## What looks best under these conditions

**Average intervention prediction:** M3 at 20 and 50 nodes, M5 by a small amount
at 100; M3 on hub/deep profiles, M5 by a small amount on dense profiles. The
prespecified multiplicity-adjusted comparisons support only the tiny 100-node
M5-versus-M3 difference. They do not establish universal superiority. Family-level
rankings are retained in `results/interpretation_checks.json`; pooled size results
must not hide the heteroscedastic 100-node panel, where ridge has the lowest
observed main-method joint error.

**Observed repair reliability:** M5 has zero harms in 90 primary adjusted-policy
settings, versus two M3 and one M4 harm. At 50 and 100 nodes all repair methods
have zero harms, often through retaining G0. M5's exact-retention indicator is
zero because it returns mixtures with nonzero alternative weights, but the initial
weight approaches one. This is conservative predictive combination, not strong
structural evidence or proof of zero harmful-repair risk.

**Accuracy/computation:** ridge is competitive on joint prediction at a small
fraction of the cost. Fixed flows give better descendant prediction and approximately
nominal marginal coverage, and equal M3's 100-node predictions for about one tenth
the charged fitting/search cost. M5 adds substantial sampling latency for a small
100-node gain. Choice depends on whether average joint error, responding-variable
prediction, coverage, or repair avoidance matters most; one winner does not cover
all four criteria.

**Structural recovery:** weak. M3's average SHD improvements are only 0.10, 0.30
and 0 at 20/50/100 nodes. A search trajectory's accepted-change count is distinct
from the ultimately calibrated and audited graph. Mixtures have no single true
adjacency matrix; their component edges and representative are visualized without
assigning causal posterior probabilities.

## Plausible explanations and their evidential limits

The fixed 0.005 acceptance threshold acts on an objective averaged across more
nodes/environments as dimension grows. A local edit can therefore have a smaller
aggregate influence. The sparse diagnostics also examine only a fixed subset of
environments/peers. Together with the limited number of proposals relative to
initial SHD, these are plausible contributors to large-graph stagnation. They are
**hypotheses from the implementation and observed behavior**, not tested causal
explanations. Thresholds, generators and diagnostics were not retuned after final
outcomes were opened.

The oracle subset shows lower prediction error with the true graph, so unchanged
100-node predictions cannot be interpreted as evidence that the corrupted graph
was already sufficient. The subset does not identify how much of the remaining
gap is due to scoring, scheduling, model class, finite data or optimization.

Lower joint SW error at larger sizes coincides with fewer descendants as a
fraction of measured outcomes and weaker average responses over all outcomes.
The elementary control also improves on the joint metric. Descendant errors and
response magnitudes are therefore necessary companions to the scaling plot.
Training-only standardization avoids a separate regime-normalization artifact.

Dense graphs use more edges and parameters; hub and deep graphs match the sparse
edge count but differ in depth, target descendant count and response magnitude.
Five SCMs per profile support descriptive comparisons with broad uncertainty,
not a claim that a single topology feature causally determines performance.
The deep topology shares an unlabeled template, limiting topological diversity.

## Boundaries of the established-method comparison

The DCDI comparator is the pinned upstream DSF density with the explicitly
documented existing optimizer adaptation and common-flow refit. It completes at
100 nodes but never satisfies the stricter raw acyclicity criterion in the 45
primary systems. All outputs require constrained DAG projection. This is a
valid capped-prediction comparison and a negative convergence result for the
executed variant. It is not evidence of inferiority of converged native DCDI-DSF.
No converged-only comparison is available. Prior-informed repair versus data-only
discovery also differs in information supplied.

The [DCDI paper](https://arxiv.org/abs/2007.01754) already studies large graphs;
100-node execution alone is not novel. The
[CauScientist paper](https://arxiv.org/abs/2601.13614) already combines LLM proposals
and intervention verification. This phase examines the limits of the existing
repair/selection/ensemble comparison under controlled data and compute budgets;
it introduces no additional headline method and makes no first-combination claim.

## Earlier real and semantic evidence remains separate

The previous semantic and apparatus findings are preserved in
[phase-two interpretation](../../phase2/docs/interpretation.md). The real polarizer
regime favored ridge; its observations had already been examined, so follow-up
analysis was exploratory. No apparatus variables were duplicated, no new real
test was manufactured, and no new large-graph LLM run was conducted. This study
cannot update real-world or LLM efficacy claims from synthetic scaling alone.

Alex should review the frozen assumptions, DCDI convergence limitation, descriptive
versus formal rankings, conservative ensemble behavior and negative 100-node
repair result before drafting claims. Human approval is not recorded or implied.
