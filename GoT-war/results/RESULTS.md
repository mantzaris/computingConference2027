# Measured results

Completed 120 text/seed records from 60 independent generating SCMs. Test variants are averaged within SCM before bootstrap; missing/failed models count as failures.

| Method | Test SCMs | Mean query score | 95% SCM bootstrap interval |
| --- | ---: | ---: | --- |
| B0 | 36 | 0.6771 | [0.6232, 0.7309] |
| B1 | 36 | 0.5903 | [0.5365, 0.6458] |
| B2 | 36 | 0.6927 | [0.5798, 0.8056] |
| P | 36 | 0.7865 | [0.6753, 0.8854] |

Scores combine identified-query correctness and appropriate uncertainty handling on incomplete records. They are not narrative probability estimates. Separate intervention accuracy and uncertainty metrics are in metrics.csv.

Admissible generation: 92 initial, 100 after bounded repairs, out of 120 records.

## Paired differences
- B2-B0: 0.0156, 95% interval [-0.0990, 0.1250], 36 SCMs.
- B2-B1: 0.1024, 95% interval [-0.0243, 0.2223], 36 SCMs.
- P-B0: 0.1094, 95% interval [-0.0208, 0.2292], 36 SCMs.
- P-B2: 0.0938, 95% interval [0.0451, 0.1493], 36 SCMs.

The overall P–B0 interval includes zero. These data do not establish overall superiority to direct prompting. Mechanism completeness changes the result:
- complete: B2–B0 0.2292 [0.1181, 0.3299].
- incomplete: B2–B0 -0.1979 [-0.3333, -0.0660].

A1 evidence weighting had mean nDCG@5 difference -0.0006 versus uniform weights; its interval includes zero. Labels measure rule availability conditional on generated paths, not gold causal importance.
A2 naive path summation failed to reconstruct the contrast on 26/59 admissible test texts; maximum absolute residual 3.0. Coalition efficiency residuals were zero in this controlled evaluation.
Post-hoc query diagnostics expose a benchmark weakness: all 43 identified structural queries in the incomplete condition retain the factual outcome; 47 further queries are ambiguous. Factual carry-forward is perfect on that identified subset. This is a different denominator from the main score and was not a predeclared baseline.

Seed sensitivity: 36/36 planned original-text records across 12 SCMs and three seeds are available. 12 SCMs have all seeds. See seed_robustness_summary.json; these repetitions do not increase the number of independent SCMs.

## Application construction and attribution

| Conflict / alternative | Nodes | Edges | Paths | Reference → full | Sum of shares | Naive sum |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| daenerys_conquest / 0 | 3 | 2 | 2 | 0.000 → 1.000 | 1.000 | 0.000 |
| five_kings / 1 | 10 | 13 | 6 | 0.000 → 1.000 | 1.000 | 0.000 |
| five_kings / 2 | 10 | 13 | 6 | 0.000 → 1.000 | 1.000 | 0.000 |
| northern_campaign / 0 | 8 | 12 | 6 | 0.000 → 1.000 | 1.000 | 0.000 |

Only the Five Kings network reaches ten nodes. The northern and Daenerys models contain eight and three nodes. Accepted generations yield only one distinct functional model per case; the two Five Kings generations are equivalent. Three diverse alternatives per case were not obtained.
All principal paths have zero weakest-link support because each includes an unsupported mechanism. Consequently all weighted segment priorities are zero; alphabetical zero-score ties are not a meaningful ranking. Exact path allocation remains an accounting property of assumed equations.

| Case | Unsupported edges | Positive-support paths | Trace-audit passes |
| --- | ---: | ---: | ---: |
| daenerys_conquest | 2/2 | 0 | 0/1 |
| five_kings | 12/13 | 0 | 0/2 |
| northern_campaign | 7/12 | 0 | 0/1 |

The northern model generates “Edmure Tully (the Blackfish)” although that personal name is absent from its entire frozen packet. The same-model reviewer accepted it. The retained alias flag demonstrates a grounding/audit failure; no corrected identity or new causal rule was supplied by the analyst. Source critiques also leave chronology and reference-state questions unresolved. Failed prose is withheld; numerical execution traces remain available.

Literary values are fixed-background model contrasts. They do not measure war probabilities, natural path-specific effects, or objective responsibility. Source spans are mechanically verified; event entailment and counterfactual mechanisms have not received independent human review. Mechanism support is assessed separately from event support.

Reference, evidence-summary, uniform-weight, model-alternative and disjoint-group results are retained in sensitivity.json and individual model records. Path IDs must only be compared across alternatives when their node sequences align. No averaging across incompatible path collections is performed.

## Runtime and failures

Elapsed campaign time through 2026-10-12T10:39:19.747445+00:00: 5.989 hours. GPU service residency: 5.666 hours. Peak sampled VRAM: 21996.0 MiB. Requests: 956; completed-response output tokens: 922897; server cumulative generated tokens: 935619.0. The latter includes interrupted streams where counted. Billing cost unavailable.

15 API/JSON requests failed; validation failures are additionally preserved with candidates. Startup failures involved tokenizer compatibility and an inherited optional downloader setting. The initial application blueprint protocol failed; its results remain in application_v1, and both the constrained-schema and modular revisions are documented in DECISIONS.md.

## Limitations and unfinished work

- Robert's Rebellion was replaced with the northern campaign against Bolton rule at the source gate; accessible evidence did not establish enough onset mechanisms.
- Sources are secondary television episode summaries from one dependent editorial family; no full primary transcript corpus was available.
- No human review, reader study, probability calibration, or paid external inference was used.
- A second model, full independent application seed repetitions, evidence-guided selection ablation, and an interactive explorer were not run. The controlled seed subset is reported above.
- Twelve canonical intervention questions per retained Five Kings/northern model were executed; the three-node Daenerys model provides only three distinct single/pair interventions and falls short of the question target.
- The benchmark is a bounded Boolean family with explicit deterministic prose. It does not prove identification or open-domain causal reasoning.
- Free-form generated explanations remain subject to semantic review even where structured number/path checks pass.
- The anonymous manuscript is a researcher-review scaffold and must not be submitted without human scientific responsibility and conference-policy review.
