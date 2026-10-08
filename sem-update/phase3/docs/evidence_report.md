# Phase-three executed evidence — 8 October 2026

The required scalability matrix completed on the existing RTX PRO 4500: **45
independent SCMs, 90 corrupted-prior settings, and both fixed and size-adjusted
resource policies**. All six methods generated valid predictions through 100
nodes. M3 had the lowest observed mean T2 error at 20 and 50 nodes; its repair
advantage disappeared at 100 nodes, where M3, M4 and random repair always returned
G0. M5 had no harmful repairs in the 90 adjusted-policy settings, but its 100-node
predictive improvement was very small. These are bounded empirical findings,
not causal-identification or general safety guarantees.

## What actually ran

Study A contains five independently seeded SCMs for each of three sizes and two
mechanism families: 30 SCMs and 60 prior settings. Study B adds five 50-node
heteroscedastic SCMs for each dense, hub and deep profile: 15 SCMs and 30 settings.
Every graph is weakly connected, labels/columns are permuted, and mechanisms
include signed smooth effects and pairwise interactions. Heteroscedastic systems
have strictly positive parent-dependent noise scales and independent disturbances.
The deep profile deliberately uses a common unlabeled chain/second-predecessor
skeleton with fresh permutations, mechanism parameters and data. Thus it replicates
SCMs but offers limited variation in unlabeled topology.
No generator draw was numerically rejected and no seed was replaced in the
completed matrix; rejected draws would be retained as `rejected_generator.json`.

One optional 50-node fixed-total-budget dataset reuses SCM 320500. It is exploratory
and does not increase the independent-SCM count. There are 46 completed datasets,
184 dataset/prior/resource records, 368 verified diagnostic/random bank views,
529 unique selected predictions, 10,872 full endpoint/method records and 1,512
compact T2 records with T1/T3 columns. The prediction audit checked 16,849 generated
model/environment arrays containing 34,506,752 observations, including checkpoint
controls. Reused predictions are not independent experimental replicates.

The protocol, seeds, data splits, budgets and scientific implementation were
frozen before final access. Protocol SHA256 is
`86a0200fc7f3f51864362b47804f1e53c2f8273a6dc94f95911d2e2af8c47246`;
scientific implementation hash is
`c20f2ac54186bcc6a385a5a4f81c1444814de4313ed99927e144208c01c8c3ee`.
The frozen record is [protocol.json](../results/protocol.json), with
[data descriptors](../results/datasets.csv), [priors](../results/priors.csv),
[input/selection audit](../results/preselection_audit.json) and
[prediction audit](../results/execution_audit.json).

Observational counts are fixed at 4096/1024/1024/512/512 for
fit/early/search/calibration/audit. Exactly 20% of targets are intervention-visible:
4, 10 and 20 at the three sizes. B=400 per visible target yields 1,600, 4,000 and
8,000 non-test intervention observations, allocated 50/10/20/10/10%. These totals
include every non-test intervention partition. Training-only observational means
and SDs standardize all environments. T1 uses fresh observations at familiar
assignments; T2 changes the assignment distribution; T3 uses targets absent from
all non-test interventions. Every final model/environment uses 2,048 samples and
256 SW projections. Increasing size therefore increases total experimental data;
it is not a fixed-total-data scaling claim.

## Primary accuracy and uncertainty

T2 is joint non-target sliced Wasserstein error in training-standardized units;
lower is better. The table uses size-adjusted resources, equal weighting of the
two families, ten independent SCMs per size and two priors per SCM. Intervals are
2,000-draw family-stratified SCM-cluster bootstrap intervals, preserving paired
conditions. Full secondary metrics and costs are in [summary.csv](../results/summary.csv).

| Method | 20 nodes | 50 nodes | 100 nodes |
| --- | ---: | ---: | ---: |
| M0 independent marginals | 0.172730 | 0.121626 | 0.098702 |
| M1 ridge on G0 | 0.107031 | 0.082249 | 0.070105 |
| M2 DCDI-DSF adaptation + common flows | 0.189145 | 0.109084 | 0.082638 |
| M3 diagnostic repair | **0.097591** [0.084754, 0.109776] | **0.080263** [0.076096, 0.085270] | 0.070146 [0.068214, 0.072201] |
| M4 robust selection | 0.098804 | 0.081311 | 0.070146 |
| M5 anchored ensemble | 0.102162 | 0.081759 | **0.070065** [0.068142, 0.072109] |
| Fixed-G0 flows | 0.106173 | 0.082131 | 0.070146 |
| Random-priority repair | 0.102145 | 0.082131 | 0.070146 |

Bold marks the observed minimum among the six main methods, not a formal claim
of superiority. All six intervals and costs are in the reproducible
[paper table](../paper/comparison.tex). At 20 nodes M3 improves on fixed flows by
0.008582 (paired 95% CI 0.003455–0.014220), but the Holm-adjusted p value is 0.494.
The only contrast below 0.05 across the **24 prespecified comparisons** is
M3 minus M5 at 100 nodes: +0.000080958, CI [0.000039149, 0.000123974], adjusted
p=0.046875. This approximately 0.12% gain is practically small; fixed final Monte
Carlo streams do not estimate uncertainty over alternative simulation seeds.
The other comparisons do not support formal superiority after multiplicity
adjustment. See [contrasts.csv](../results/contrasts.csv).

T1/T3 mean errors for M3 are respectively 0.085535/0.092490, 0.075731/0.078692,
and 0.067850/0.069837 at 20/50/100 nodes. M5's corresponding 100-node values are
0.067785/0.069800. These are distinct endpoints, not extra independent SCMs.
Nominal 90% marginal coverage is approximately 89.85–89.94% for M3, compared with
88.53–88.58% for ridge; mean interval widths are about 3.28 versus 3.16 standardized
units. Marginal coverage is not simultaneous joint coverage or a confidence
interval for a method mean. Energy scores, mean-effect errors, worst-regime errors,
50% intervals and non-descendant checks are retained in the compact metrics.
M0 has no continuous-density likelihood; its NLL is unavailable, not zero.

## Dimensional dilution and oracle checks

The mean descendant fraction drops from 0.301 at 20 nodes to 0.170 at 50 and 0.137
at 100. True response RMS over all non-targets drops from 0.144 to 0.094 to 0.076,
while response RMS on descendants remains approximately 0.355/0.334/0.342.
These reference-response magnitudes are estimated from finite reference-SCM
samples, not analytic population effects; independent samples introduce a
Monte Carlo floor even for non-descendants.
A falling joint error across sizes therefore does not demonstrate better causal
prediction. The independent-marginal control also improves on that aggregate.

| Method | Descendant W1, 20 | Descendant W1, 50 | Descendant W1, 100 |
| --- | ---: | ---: | ---: |
| Ridge | 0.160970 | 0.165901 | 0.147080 |
| M3 | 0.136330 | 0.132704 | 0.115074 |
| M5 | 0.138216 | 0.142009 | 0.114983 |
| Fixed flows | 0.143123 | 0.143457 | 0.115074 |

Ridge is a strong accuracy/computation option for the joint endpoint, but misses
more of the responding-variable distributions. Descendant truth is accessed only
by isolated evaluation and declared illustrations, never selection or diagnostics.
Non-descendant W1 at 100 nodes is 0.057061 for M3/G0, 0.057028 for M5 and 0.061496
for ridge. These nonzero errors include finite-sample and distribution-fitting
error; they are not automatically evidence of a genuine causal effect.

Oracle flows on the prespecified first replicate of each family give matched
mean T2 errors 0.065370/0.051866/0.047458 at 20/50/100 nodes; **on those same SCMs**,
M3 gives 0.088474/0.072791/0.067794. This demonstrates remaining predictive headroom
with correct structure on the selected subset. It does not prove that structure
is the only bottleneck. There is only one oracle SCM per family/cell, so population
confidence intervals are unavailable rather than spuriously zero-width.

## Complexity profiles at 50 nodes

| Profile | Edges; depth | M1 | M2 | M3 | M4 | M5 | Fixed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dense | 322; 21–26 | 0.077673 | 0.118603 | 0.077360 | 0.077360 | **0.077248** | 0.077360 |
| Hub | 97; 3–5 | 0.090075 | 0.098844 | **0.082415** | 0.087678 | 0.087636 | 0.089195 |
| Deep | 97; 49 | 0.076614 | 0.123795 | **0.073224** | 0.074868 | 0.074874 | 0.075336 |

Each row has five independent SCMs and ten prior settings. Hub and deep edge counts
match the sparse 50-node design; dense intentionally changes edge count and mean
indegree to 6.44 (maximum seven). Hub maximum outdegree is 29–44, with 92–95% of
edges leaving the top decile of nodes. All graphs have one weak component.

M3 returns G0 in all ten dense settings, six hub settings and eight deep settings.
No repair method is harmful in these three panels. Mean initial/returned M3 SHD
is 85.3/85.3 for dense, 29.6/29.2 for hub and 28.5/28.1 for deep. Predictive gains
do not imply substantial graph recovery. The hub panel has few descendants
(mean fraction 0.075) with relatively large responses (descendant response RMS
0.392); dense and deep fractions are 0.410 and 0.521. These structural/effect
differences prevent treating profile labels as a single ordered difficulty scale.
No profile contrast survives the prespecified multiplicity correction.

## Repair reliability and retained initial models

Harm retains phase two's definition: returned T2 error exceeds fixed-G0 error by
more than `max(0.001, 0.05 * fixed_error)`. M0/M1/M2/oracle are not repair methods;
harm is N/A for them. Under adjusted resources:

| Method | Harmful settings / 90 | At 20 / 50 / 100 nodes | G0 retention at 20 / 50 / 100 |
| --- | ---: | --- | --- |
| M3 | 2 | 2/20; 0/20; 0/20 | 25%; 80%; 100% |
| M4 | 1 | 1/20; 0/20; 0/20 | 50%; 90%; 100% |
| M5 | 0 | 0/20; 0/20; 0/20 | 0%; 0%; 0% |
| Random | 1 | 1/20; 0/20; 0/20 | 45%; 100%; 100% |

M3's two harms have mean deterioration 0.010027 and maximum 0.013538. M4's one
harm is 0.010323; random's is 0.011048. M5 has small positive deteriorations below
the frozen harm threshold; zero harmful settings does not mean every result
improves. Its components remain overwhelmingly anchored near G0 at large sizes.
Zero exact G0 retention means a nondegenerate predictive mixture was returned,
not that the initial component received little weight. Its mean initial weight
before audit is 0.877/0.961/0.980 at 20/50/100 nodes. Exact weights and audited
fallbacks are in [mixture_weights.csv](../results/mixture_weights.csv).

M5 preserves the best observed reliability, but at 50/100 nodes it ties methods
that mostly or entirely abstain from repair. With ten independent SCMs per size,
zero events still permits a one-sided 95% upper bound of 25.9% for the probability
an SCM has **any** harmful tested condition; the five-SCM profile bound is 45.1%.
These are system-level risk bounds, distinct from condition-frequency bootstrap
intervals. The full reliability table retains both, with harm severity and
mean positive deterioration. See [reliability.csv](../results/reliability.csv).
Robust selection's mean worst-regime error is 0.139053 versus M3's 0.140012 at
20 nodes, but 0.129175 versus 0.128629 at 50; both are 0.117033 at 100. It does
not uniformly improve the worst-regime endpoint under the tested conditions.

The declared adverse example is additive SCM 310200, corruption 0.2, M3, target
10 and outcome 18. It was selected after evaluation by the frozen worst-harm rule,
not as a representative random example. The reference and G0 have no directed
path from 10 to 18; M3 introduces one and predicts a spurious response. Conversely,
the prespecified 100-node example (SCM 321000, target 3, outcome 24) has a true
path missing from G0, M3 and both M5 components, so these models miss that response.
Actual curves, predictive intervals and edges are preserved in F7/F8/F10; path
checks are in [interpretation_checks.json](../results/interpretation_checks.json).

## Computation, budgets and failures

Actual additional GPU-job usage, including pilots, correctness runs and failed
attempts, is **19.482635 hours**, within the 24-hour cap. Earlier use is 16.093464
hours; cumulative use is **35.576099 hours**. Overlapping intervals on the single
physical GPU are unioned. Summed nested/concurrent intervals are 199.643 hours;
that figure is not device consumption. The measured experiment wall span including
idle gaps is 20.564 hours, excluding subsequent CPU documentation/preservation.

The verified device is NVIDIA RTX PRO 4500 Blackwell, 32,623 MiB, driver
580.159.04, PyTorch 2.8.0+cu128. CUDA matrix computation and gradients passed.
Device-wide sampled peak usage is 7,840 MiB (15-second polling, not an exact
continuous peak); maximum recorded process allocation is 1,845,830,656 bytes
(1.719 GiB). Median sampled GPU utilization was 86%. Flow fitting, discovery,
sampling and substantial distances ran on CUDA. Six workers shared the same GPU;
reported per-job times include contention and are not isolated hardware benchmarks.

| Mean charged training/selection seconds | 20 | 50 | 100 |
| --- | ---: | ---: | ---: |
| Ridge | 0.191 | 0.825 | 2.982 |
| DCDI discovery + common refit | 1388 + 89 | 1536 + 159 | 1847 + 252 |
| M3 | 773 | 1531 | 3784 |
| M5 | 762 | 1499 | 3651 |
| Fixed flows | 151 | 214 | 359 |
| Random repair | 612 | 1090 | 2704 |

M3–M5 each pay the full logical cost of the same candidate bank, even when shared
execution reuses it. Selection/audit costs differ. Actual stage runtimes and
unique prediction savings are separately recorded in
[execution_sharing.csv](../results/execution_sharing.csv); discovery/refit and
inference are separate columns in the main metrics. Mean complete final-generation
time for M3 is 0.062/0.196/0.622 seconds versus M5's 1.351/6.269/19.964 seconds.
These totals cover all T1/T2/T3 environments, whose number grows with size.
M5's complete-observation mixture implementation is substantially slower; its
tiny 100-node accuracy gain is not a free inference improvement. Throughput and
per-environment latency are also reported.

Adjusted M3 banks average 24/36/70.2 candidate graphs, 53.8/108.1/215.1 unique
parent sets and 21,515/49,090/111,712.5 per-mechanism updates. Search accepts
1.1/0.25/0 changes on average; returned SHD is 10.5/28.75/57.25 versus initial
10.6/29.05/57.25. Random receives the same candidate caps but averages
17,747.5/38,705/89,710 updates. Candidate counts alone are not compute matching.

Fixed-budget M3 gives 0.097688/0.081400/0.070146 T2 error at 20/50/100 nodes,
charging 379/468/666 seconds (exact costs in summary.csv).
Expanded resources improve some 20/50-node cases but leave 100-node error unchanged.
At 20 nodes the larger bank increases M3 harms from one to two despite a small
mean gain. Increased search is therefore neither uniformly useful nor harmless.

The matched-computation analysis uses paired completed prefixes and reports
achieved costs and coverage. At the 20-node 500-second ceiling, diagnostic/random
errors are 0.097520/0.104531 with achieved fit-plus-search times 487/489 seconds
(all 20 conditions). At 50 nodes and 1,000 seconds they are 0.080810/0.082131,
achieving 979/986 seconds (all 20). At 100 nodes they are identical at every
available matched checkpoint, including the 3,000-second ceiling. The 100-node
50,000-update checkpoint has no paired coverage because the initial fits already
exceed that limit; the 20-node 200-second checkpoint covers 16/20 conditions.
Changing checkpoint coverage is shown explicitly, not silently dropped.
SCM-paired descriptive intervals are in interpretation_checks.json; formal tests
remain the original 24 contrasts. See [checkpoints.csv](../results/checkpoints.csv)
and [coverage](../results/checkpoint_coverage.csv).

M2 uses the pinned official DCDI-DSF density with the **documented phase-two
optimizer adaptation**, followed by common flows. All 45 primary discoveries
require DAG/indegree projection; 44 reach the 60,000-step cap and one meets the
legacy stopping rule but fails the stricter raw-constraint criterion. **Zero of
45 strictly converge.** Valid capped/projected predictions exist for every setting,
but there is no converged-only matched subset. Density and gradient equivalence
tests validate that component, not optimizer convergence. These results do not
establish that a well-converged native DCDI implementation is intrinsically worse.
Discovery is data-only while ridge/repair receive a corrupted prior, another
material information difference. [discovery.csv](../results/discovery.csv) records
raw constraint, stopping reason, projection changes, steps, time and memory.

There are no main training numerical failures or missing primary predictions.
A correctness harness initially marked `SystemExit(0)` as failed; its record was
retained. Final evaluation initially failed when its CSV writer encountered
optional projection columns. A tested serialization-only adapter exported the
union of columns, leaving unavailable values blank. It reused the sealed models
and predictions; no seed was replaced and no scientific source changed. The failed
export, traceback and both attempts remain in the archive. Full coverage and
failure accounting are in [compute.json](../results/compute.json).

## Sensitivities, preservation and limits

Projection checks on the first replicate per cell use 64/256/1024 directions.
For the paired 100-node subset M3 errors are 0.067644/0.067794/0.067900 and M5
errors 0.067528/0.067680/0.067791. The small ordering persists on that subset,
but the check has only two SCMs and does not measure new sampling-seed variability.
The 50-node fixed-total sensitivity reduces intervention data from 4,000 to 1,600
on one SCM. M3 error rises from 0.072277 to 0.079960, and M5 from 0.072019 to
0.079958. This is evidence of data-budget sensitivity in one system, not a
population estimate. The optional 100-node fixed-total cell was not admitted by
the frozen conservative reserve guard; it remains explicitly incomplete. The
unused final allowance does not turn it into an executed result.

There are no 200-node, non-Gaussian, latent-confounded, feedback, soft-intervention,
new real-data or large-graph LLM runs in this phase. Previous semantic and real
results remain unchanged: phase two's real polarizer case favored ridge and was
exploratory on an already examined physical apparatus. This synthetic study does
not validate scalability on large real causal systems or revise those conclusions.
Visible-target fraction stays at 20%; other coverage fractions are untested.
The rho=0, tau=0 and uniform alternatives remain in calibration/audit records but
do not have separate final prediction panels in this scaling matrix. Therefore
large-graph M5 results do not isolate anchoring from ensembling itself.

The scientific source passed **61 tests** before final evaluation; the CSV adapter
and statistical checks subsequently passed four CPU tests (three repeat existing
tests). Linear-Gaussian sampling sanity checks passed at 20/50/100 nodes using
100,000 CUDA samples each. Integrity audits verify splits, masking, parent-set
keys, identical candidate banks, selection arithmetic, one-time audits, simplex
weights and final assignments. All 13 figure sets were generated as PDF/SVG/PNG;
compact-input-only reproduction checks byte identity without raw data or models.
Selected vectors, one preview and two tables are committed within the cumulative
size budget; all formats, original renders, checkpoints and full evidence remain
in the verified ignored archive. See [artifact preservation](artifacts.md),
[figure captions](figure_captions.md), [status/resume](status.md),
[interpretation](interpretation.md) and [claim ledger](claim_ledger.md).

Historical studies at `ad21e60` and `8c452ac` are preserved. Alex's review of
assumptions, claims, protocol and final text remains pending. No push, submission,
registration, new paid resource or Pod termination was performed.

## Repository-size verification

Only explicit source, tests, configs, compact metrics/provenance, documentation
and selected final figures/tables are staged. The actual-index audit includes
all 22.217 MiB of historical new blobs, including intermediate committed versions.
The cumulative project is approximately **24.60 MiB of the 25 MiB limit**; this
phase adds approximately **2.39 MiB**. The largest phase-three file is 865,675 bytes;
the largest project file is 4,045,448 bytes, below 5 MiB. No dataset, checkpoint,
model, generated sample, full log or Git LFS object is included. Exact byte counts
and remaining space are in [repository_size.json](../results/repository_size.json);
the full indexed-blob inventory remains in the ignored local audit. No history
was rewritten and no experimental evidence was deleted to meet the limit.
