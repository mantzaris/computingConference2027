# Interpretation of the executed comparison

These findings concern the frozen tested matrix. They supplement the generated
[evidence report](evidence_report.md); Alex's scientific review is pending.

**Average prediction and repair reliability favor different procedures.** M3
has controlled T2 SW1 0.10617, versus 0.11755 for M4 and 0.13018 for M5. The
paired M3-minus-M4 difference is -0.01138 (cluster interval [-0.02204,-0.00274],
Holm p=0.046875); M3-minus-M5 is -0.02401 ([-0.03787,-0.01163], p=0.008240).
These tests belong to the prespecified 15-pair primary family and assume paired
sign exchangeability. M3 also has lower error than M0/M1/M2 in that family.
See [primary comparisons](../results/primary_comparisons.csv).

M5 has one harmful returned repair in 60 conditions, compared with eight for
M3, seven for M4 and five for random repair. Its largest deterioration is
0.01035; M3 and M4 each reach 0.07697. This is evidence of a useful observed
reliability tradeoff, not a guarantee against future harm. M4 retains G0 in
38.3% of conditions versus 25.0% for M3, with only one fewer harmful condition.
Its mean worst-regime T2 error is 0.17020 versus M3's 0.14842; the robust
calibration criterion did not improve that held-out quantity here. See
[reliability](../results/repair_reliability.csv) and
[secondary outcomes](../results/secondary_outcomes.csv).

**The anchoring control matters.** With tau=0, the same shortlisted predictive
mixture has mean T2 error 0.11126 and eight harmful repairs; uniform weights
give 0.12222 and six. Anchored M5 trades average accuracy for fewer and less
severe harmful repairs. The paired tau=0-minus-M5 harm-frequency difference is
0.11667, with descriptive cluster interval [0.03333,0.21667]. These secondary
intervals are not additional uncorrected formal superiority claims. Rho=0
exactly reproduces M3. All three main repair procedures pay for the same fitted
bank. See [repair comparisons](../results/repair_comparisons.csv).

**Computation has no single optimal tradeoff without a cost preference.** Ridge
M1 is the inexpensive intervention-sensitive baseline: about 0.039 s fitting
and T2 error 0.19396 on the controlled matrix. M3 achieves better accuracy with
169.50 canonical mechanism-fitting seconds plus selection; M2 uses 792.72
discovery seconds and 53.73 refitting seconds for error 0.27225. M3/M4/M5 have
identical mechanism-fitting costs. Small differences in their selection timings
put several on the numerical Pareto frontier, but do not establish a meaningful
computational advantage. Times include the disclosed execution contention.
The full-budget DCDI result does not establish poor performance of every
configuration of the published method. Its strict-convergence sensitivity
still has mean error 0.26951 versus M3's 0.10583 on matched eligible conditions;
the subset is selected by optimization status, not at random.

Diagnostic repair retains an observed advantage over random repair at the
matched ceilings. At 6000 fitting updates, means are 0.11913 versus 0.15289;
mean achieved updates are 5574 and 5383. At the 120 s canonical fitting-time
ceiling, means are 0.14300 versus 0.15773 and both average about 111.4 achieved
seconds. These are completed-prefix ceilings, not exactly equal total method
runtimes. Search/diagnostic overhead is excluded from that time axis and
reported in full method costs. See [checkpoint coverage](../results/checkpoint_summary.csv).

**Separate panels change the ranking.** With coherent metadata, M5's semantic
mean is 0.09250, close to DCDI's 0.09473, versus 0.11166 for M3 and 0.11808 for
the functioning LLM-edit adaptation. Five independent SCMs give limited power;
the corrected semantic LLM comparisons do not establish superiority. M5 has
the lowest observed semantic mean in all three metadata variants, which reuse
the same five SCMs. Its anonymous and shuffled means (0.0906 and 0.0830) are
lower than its coherent mean; these descriptive controls do not demonstrate a
benefit from coherent semantic metadata. On unseen synthetic targets, M5 and M3 are close (T3 means
0.15649 and 0.15736); this is not a formal equivalence claim.

The new polarizer regime favors ridge M1: 0.08557, versus 0.13485 for M3/M4,
0.14599 for M5 and 0.21970 for the LLM adaptation with coherent metadata.
Its conditional block interval is [0.07368,0.11409]. Each regime has only one
acquisition run; ten-row groups are analyst-defined reporting blocks. This
uncertainty excludes refitting and between-apparatus variation. The apparatus
and design were already familiar. RGB outcomes remain exploratory; the fixed
flow control and M5 are close near 0.1131 there. See
[separate-panel results](../results/method_summary.csv) and
[conditional real intervals](../results/real_block_intervals.csv).

The adverse graph/response example is included because a returned repair
increased error by 0.07697 despite passing its audit. The one-time audit does
not certify safe extrapolation. Mixture weights express predictive combination,
and neither a generated graph nor a highest-weight component proves causality.
The narrow proposed contribution and its antecedents remain in the
[source-linked novelty review](novelty.md); both extensions remain proposed
procedures with mixed results across panels.
