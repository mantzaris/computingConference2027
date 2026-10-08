# Figure definitions and caption notes

These definitions accompany the executed final figures. M0–M5 are defined in the
README. M2 is the documented DCDI-DSF optimizer adaptation plus common flows;
all 45 primary discoveries are capped/projected and none strictly converges.
Every M2 comparison must retain that qualification in its publication caption.
All error
metrics use observational-fitting means and standard deviations; regimes are not
normalized separately. Actual coverage accompanies every reported comparison.

**Comparison and reliability tables.** The comparison table pools the two Study A
families with ten independent SCMs per size, two priors per SCM and adjusted
resources. Time is logical training/discovery/search/selection wall time, excluding
final prediction; VRAM is maximum allocated memory across the method's recorded
stages. Time rounded to 0.0 does not mean zero computation. The reliability table
uses the frozen harm threshold and distinguishes exact G0 retention from a
mixture dominated by G0. Exact costs and precision remain in the compact CSVs.

**F1 — Intervention prediction by graph size.** T2 joint non-target sliced
Wasserstein error, using 256 projections and 2,048 final samples per environment.
Panels separate additive and heteroscedastic mechanisms. Lines average the two
corruptions within each SCM, then average independent SCMs. Faint points are
individual SCM averages; bars are 95% SCM-cluster percentile bootstrap intervals
from 2,000 resamples. They are not predictive intervals. The adjusted search
policy is used. A decreasing joint error across dimensions does not alone imply
better causal prediction; inspect responding-variable errors and response size.

**F2 — Computation and memory by size.** Logical training/discovery and selection
wall time for each method, and maximum measured allocated CUDA memory. M2 includes
discovery and common-flow refitting; those costs are also reported separately.
Each of M3–M5 is charged its complete bank even when execution reuses models.
Times can include contention from six processes on one physical GPU. Allocated
memory differs from sampled device-wide memory, which includes concurrent
processes and CUDA contexts. The cumulative device ledger unions overlapping
intervals and is not the sum of these method charges.

**F3 — Prediction versus charged resources.** Fixed and adjusted resource policies
at each graph size. The fixed bank is the historical at-most-12-candidate,
two-stall prefix; adjusted caps are 24, 36 and 72. Baselines whose resources do not
change coincide across policies. Graph count is not treated as constant cost:
time includes unique parent-set fitting and search/selection work. Initial SHD,
accepted moves and remaining SHD are separate recorded quantities.

**F4 — Structural profiles and responding variables.** The upper panel compares
50-node heteroscedastic SCMs. Sparse, hub and deep profiles have 97 edges; dense
graphs deliberately have 322. Deep graphs have a common unlabeled skeleton with
fresh label permutations, mechanisms and data. The lower panel reports marginal
Wasserstein error restricted to true descendants, using reference structure only
in evaluation. Environments without descendants are unavailable for this metric;
their count is reported. Non-descendant errors, response magnitude and descendant
fractions remain separate table columns.

**F5 — Harm and improvement.** A repair is harmful when its T2 error exceeds G0 by
more than `max(0.001, 0.05 × G0 error)`. Frequency intervals resample SCMs while
retaining their two prior conditions. Maximum deterioration is the largest
positive error change, not a confidence interval or a conditional mean harm.
The final panel relates condition-averaged improvement over G0 to harm frequency
at the three sizes. Zero observed harm does not establish zero population risk;
the reliability table includes the separate one-sided bound for any harm on an
independent SCM. M0, M1 and M2 do not perform repair and receive no repair-harm label.

**F6 — Matched computation.** Diagnostic and random policies are compared at
identical prespecified update or fitting-plus-search time ceilings. Only completed
prefixes containing G0 qualify. Each comparison retains the same SCM/corruption
cases for both policies before averaging within SCM. The horizontal coordinate is
achieved cost, not the requested ceiling. Coverage can vary between ceilings;
the plotted sequence is not an unqualified learning curve on a fixed population.
Calibration/audit costs remain in the accompanying logical-cost columns.

**F7 — Intervention-response illustrations.** Each curve uses 21 fixed assignments
and 2,048 generated observations per assignment. Means are shown for all listed
models; shaded 5th–95th predictive quantiles appear for the reference and M5.
They represent distribution spread, not uncertainty about a mean or SCM ranking.
The prespecified cases use the first 100-node sparse heteroscedastic and first
50-node deep system, high corruption, the lowest visible target with descendants,
and its lowest labeled direct child. The adverse case is
explicitly selected after evaluation by the rule in the protocol. These fixed
assignment curves are illustrations; the T2 benchmark uses Gaussian assignments.

**Graph panels — Common-layout structure.** Each case has a whole-graph overview
and a declared local subgraph, with positions shared across reference, G0, returned
repair and M5 component graphs. Red identifies the intervention target. Local
nodes follow the frozen neighborhood rule, and the plotted outcome is retained.
Whole-graph panels illustrate overall structure; the labeled local view supports
edge inspection. Mixture weights are predictive combination weights, rounded in
titles; exact weights and all edges are retained in graph JSON. The highest-weight
component is labeled as a representative, not as a causally proven graph. Edge
lines encode graph membership, not effect magnitude or selection stability.

Final local views use a shared circular layout in the original declared node
order to avoid overlapping labels. Whole-graph positions are unchanged. All
initial renders and the layout-only content hash are preserved in the ignored
evidence; `results/visual_review.json` records the change.

The three executed illustration cases are:

| Panels | SCM; prior | Intervention target; outcome | Interpretation |
| --- | --- | --- | --- |
| F7 first row; F8 whole/local | 321000; 0.5 | 3; 24 | Prespecified 100-node heteroscedastic case. The reference has a causal path; G0, returned M3 and both M5 components lack it. The repaired/ensemble curves miss this response. |
| F7 second row; F9 whole/local | 352000; 0.5 | 11; 10 | Prespecified 50-node deep case; all displayed graphs contain a target-to-outcome path. |
| F7 third row; F10 whole/local | 310200; 0.2 | 10; 18 | Post-evaluation adverse M3 example. Reference and G0 have no directed path; returned M3 introduces one and predicts a spurious response. |

The graph-path assertions are checked from actual exported edges in
`results/interpretation_checks.json`. Reference topology is used for illustration
and evaluation only. Plotted values trace to `results/responses.csv`; graph
panels trace to `results/illustration_graphs.json`. All other numeric plot inputs,
source hashes and output hashes are listed in `results/figure_manifest.json`.
