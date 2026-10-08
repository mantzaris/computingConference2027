# Phase-three claim ledger

This ledger reflects executed results, including adverse findings. Evidence links
refer to the separate phase-three study; historical ledgers remain unchanged.

| Status | Claim | Evidence and boundary |
| --- | --- | --- |
| Supported | All six implemented variants generate valid predictions through 100 nodes on the required matrix. | 45 independent SCMs, 90 settings; [coverage](../results/coverage.csv), [audit](../results/execution_audit.json). M2 predictions are capped and projected, not strictly converged. |
| Supported | M3 has the lowest observed average T2 error at 20 and 50 nodes. | [Summary](../results/summary.csv), adjusted policy, ten SCMs/size. Formal superiority after Holm is not established. |
| Supported | M3/M4/random do not repair any 100-node primary setting. | 20/20 G0 retentions per method; zero accepted search changes, unchanged SHD despite expanded budgets. |
| Supported | M5 has zero observed harmful repairs across 90 adjusted-policy primary settings. | [Reliability](../results/reliability.csv); M3 two, M4 one. Positive below-threshold deterioration exists; zero events is not zero population risk. |
| Supported | At 100 nodes M5's mean T2 error is slightly lower than M3/G0. | Difference 0.000080958, Holm p=0.046875 across 24 contrasts; [contrasts](../results/contrasts.csv). Small practical magnitude and fixed Monte Carlo streams. |
| Supported | Fixed flows equal M3 at 100 nodes for much less charged computation. | 0.070146 error; mean 359 versus 3784 fitting/search/selection seconds. Shared execution savings are separately recorded. |
| Supported | Ridge is inexpensive and competitive on the joint endpoint; flows better predict descendants here. | [Summary](../results/summary.csv); neither metric alone determines a universal winner. |
| Supported | No primary DCDI discovery meets strict convergence. | [Discovery](../results/discovery.csv): 44 step caps, one legacy stop, 45 projections. Valid predictions and convergence are distinct. |
| Supported | The complete required matrix fits the existing device within the authorized phase cap. | 19.482635 additional device hours; [compute](../results/compute.json), verified CUDA and gradients. Concurrent elapsed timings are hardware/scheduling dependent. |
| Mixed | The earlier M3 accuracy advantage persists with scale. | Observed at 20/50 and hub/deep, absent as repair at 100 and dense. No global superiority claim. |
| Mixed | More candidate/update budget improves repair. | Helps some 20/50/hub/deep cells; no 100-node gain; M3 harms at 20 increase from one to two. |
| Mixed | M5 offers the best reliability/accuracy tradeoff. | Best observed harms, but conservative weights, smaller mean improvement and greater prediction latency. |
| Mixed | Diagnostic prioritization beats random at matched computation. | Lower observed errors at selected 20/50 checkpoints; exact ties at 100; paired-case coverage varies at low ceilings. [Checks](../results/interpretation_checks.json). |
| Unsupported | All repair methods remain effective on 100-node graphs. | M3/M4/random always return G0; M5 gain is very small. |
| Unsupported | Falling joint SW error with dimension proves better causal prediction. | Descendant fractions and all-outcome response magnitude also fall; M0 improves on the same aggregate. |
| Unsupported | This experiment establishes superiority over converged native DCDI-DSF. | Executed optimizer variant never strictly converged and all graphs were projected. |
| Unsupported | An ensemble weight is a probability that a component graph is causally true. | Weights optimize calibration prediction with anchoring; no causal posterior model. |
| Unsupported | Good prediction establishes the repaired graph's causal correctness. | Small SHD gains, limited intervention coverage, fallible scores and generators do not establish identification. |
| Untested | A dimension-adjusted acceptance threshold would solve stagnation. | Plausible mechanism, no post-test tuning or ablation executed. |
| Untested | Results generalize to 200 nodes, non-Gaussian noise or assumption violations. | No such phase-three runs. |
| Untested | Fixed-total-budget behavior is established at 100 nodes. | Optional cell not admitted by the frozen reserve guard; only one exploratory 50-node sensitivity completed. |
| Untested | Large real causal systems or LLM proposals retain these rankings. | No new real/LLM panel in phase three; prior limitations preserved. |
| Untested | Alex has approved the protocol or final claims; paper submitted/accepted/indexed. | Scientific review and any submission require human action; none is invented. |

Methodological novelty remains narrowly positioned as an empirical investigation
of disturbance-guided repair under controlled fitting budgets, independent
prediction and harmful-repair evaluation, with previously proposed robust and
ensemble extensions. [Source-linked positioning](positioning.md) does not claim
priority for LLM/verifier loops, causal flows, robust selection, or mixtures.
