# Figure captions for scientific review

These captions describe the frozen estimands and plotting conventions. Numeric
findings belong to the executed tables and evidence report. Alex's scientific
review is pending. `results/curated/figure_manifest.json` records the exact input
hashes and illustrative run identifiers after export.

**F1 — Disturbance-guided repair of generative SCMs.** A frozen local language
model proposes candidate DAGs from public variable descriptions. Conditional
normalizing flows fit the structural mechanisms with independent disturbances
and shared parameters across intact environments. Disturbance diagnostics rank
valid edits; a common search score selects candidates under a maximum of 12
evaluated DAGs. A separate one-time audit can return the starting graph.
Final intervention distributions are evaluated only after all selections are
frozen. The schematic describes a computation, not a causal-identification
guarantee. Controlled synthetic corruptions are evaluated separately from
language-model proposals.

**F2 — Initial, returned and reference graphs for the illustrative synthetic
case.** Nodes occupy identical positions across panels. Green dash-dot edges
are additions to the initial graph; orange dashed overlays mark removed
edges. A rejected pre-audit graph appears when the audit returns the initial
graph. The annotation records accepted search edits and their changes in the
common score. The example follows the declared median paired T2 change among
five-node, B=400, 50%-corruption cases, with run-ID tie breaking. Reference
graphs appear only after selection. Edge width encodes neither stability nor
effect magnitude. Any separate adverse-case figure follows the declared
largest harmful change, rather than the representative-case rule.

**F2 adverse case — A graph correction with worse prediction.** In the largest
harmful controlled condition (linear, five nodes, seed 11004, B=100, nominal
corruption 0.5), reversing V2→V3 to V3→V2 reduced the search score by 0.11036 and
passed the audit. T2 SW1 nevertheless rose from 0.246529 to 0.301508. The
reference graph contains V3→V2; correcting an edge does not guarantee better
finite-sample intervention prediction. This is a selected adverse illustration,
not a typical-case estimate.

**F3 — Synthetic intervention-response curves.** For the F2 case, curves show
Monte Carlo means under fixed target interventions at 21 standardized settings,
using 2,048 CUDA-generated samples per point and common disturbances across
settings and models. The shaded model band is its 5th–95th predictive-quantile
interval, not a confidence interval for the mean or an interval across SCMs.
Gray background marks settings outside the observed fitting-intervention range;
the vertical dotted line marks the nominal fitting mean of +1. Fixed-setting
curves illustrate the fitted mechanisms; the primary T2 endpoint instead uses
stochastic assignments with mean −1 and standard deviation 0.25. The synthetic
reference and fitted oracle graph remain distinct. Inputs: response_curves.csv.

**F3 real case — Source-current prediction under measured RGB regimes.** Points
compare measured means with the coherent-metadata fixed, diagnostic-repair and
LLM-edit models. T1 uses later held-out rows from the mid assignment regime;
T2 uses the separately held-out strong regime. No unmeasured intermediate
response curve is interpolated. Values use the reference-fitting mean and
standard deviation. These measurements come from one apparatus; assignment,
measurement and serial-dependence limitations are described in the dataset
audit. Inputs: real_response_points.csv.

**F4 — Held-out intervention prediction versus corruption and sample budget.**
Separate figures show five-node and ten-node SCMs, with rows for mechanism
family and columns for B=100 and B=400 intervention observations per seen
target, including all non-test roles. Each point is an independent SCM;
gray segments connect its matched fixed, random-priority and diagnostic-repair
results. Large markers show means; error bars are descriptive 95% bootstrap
intervals across the five SCMs in that panel. Horizontal baselines show mean
oracle-graph, DCDI and data-only performance; their faint bands show observed
SCM ranges, not confidence intervals. Panel labels also report mean realized
initial structural Hamming distance. Lower joint non-target T2 sliced
Wasserstein-1 is better. Paired primary comparisons use the separate stratified
SCM bootstrap in summary.csv. Inputs: F4_points.csv and F4_summaries.csv.

**F5 — Harmful repair and fitting cost.** The first panel shows paired T2
changes between returned diagnostic-repair and fixed-start models; negative
values favor repair. The second counts beneficial, neutral and harmful
conditions before and after the independent audit. Harm exceeds the larger
of 0.001 and 5% of initial SW1; benefit uses the symmetric decrease. Budgets
and corruptions from the same SCM are paired conditions, not independent
replications. The cost panel relates prediction to canonical required
optimizer updates for diagnostic and random repair. Cache-dependent actual
updates, elapsed time and memory are reported separately in the numerical
records; equal candidate caps need not produce identical achieved costs.
Inputs: F5_histogram.csv, F5_harm_counts.csv, F5_cost_points.csv and
paired_repairs.csv.

In the executed controlled matrix, the beneficial/neutral/harmful counts are
84/26/10 before and after audit. Canonical fitting updates average 9,047.1 for
diagnostic and 7,525.4 for random repair. These measured cost differences qualify
the common candidate cap; this figure does not establish a benefit at equal
achieved fitting work.
