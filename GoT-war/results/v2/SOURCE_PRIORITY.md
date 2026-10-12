# Source-priority evaluation

Gold query-specific causal-slice rule relevance, specified before inference; this is not human literary salience. No positive labels means ranking not evaluable. A missing/zero ranking with positive labels receives zero.

| Method | nDCG@5 [95% SCM interval] | Eligible SCMs |
|---|---:|---:|
| B0 | 0.658 [0.538, 0.771] | 37 |
| B1 | 0.722 [0.610, 0.825] | 37 |
| FULL | 0.417 [0.260, 0.568] | 37 |
| UNIFORM | 0.417 [0.260, 0.568] | 37 |

| Paired FULL difference | nDCG@5 difference |
|---|---:|
| versus B0 | -0.241 [-0.433, -0.050] |
| versus B1 | -0.305 [-0.485, -0.119] |
| versus UNIFORM | 0.000 [0.000, 0.000] |

Among the 37 eligible SCMs, FULL ranking availability is: {"admitted_but_unavailable": 11, "available": 16, "failed_synthesis": 10}. These counts separate synthesis rejection from an unavailable ranking after formal admission.

The labels describe a potentially relevant structural slice, not a minimal sufficient evidence set, episode desirability or human reading benefit. Factual-value controls can be answered from the known factual states and intervention semantics even when downstream rules retain positive slice labels. FULL can have no ranking when its selected-path contrast is zero even though rule passages explain the invariance. Those cases receive zero if independent relevance labels are positive. Uniform support uses the same paths and structural allocations; with correctly extracted explicit directional statements, its weights can coincide with FULL even when exact functions are unknown. The explicit-rule corpus does not manipulate source reliability; such equality does not demonstrate a benefit from weighting heterogeneous evidence. Application priorities have no independently adjudicated relevance labels and are reported as provisional review priorities only.

Controlled FULL computes paths and priorities from the single retained model. Its explanation record includes the family outcome set, but its source ranking is not averaged or bounded across compatible mechanisms. In an underidentified case, a zero contrast under that single assumption can therefore miss evidence relevant to the family uncertainty. This is a limitation of the frozen component, not a robustness guarantee. Application games are computed per retained global model, but this campaign retains only one.
