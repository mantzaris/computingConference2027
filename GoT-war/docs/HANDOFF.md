# Research handoff

**Version 2 campaign in progress:** `campaign_v2_20261012T160349Z`, immutable deadline 2026-10-13 16:03:49 UTC. See `V2_METHODOLOGY.md`, `V2_DIAGNOSIS.md`, `configs/budget_v2.json`, and the ignored run directory. The sections below describe the preserved version 1 delivery; new results live in `results/v2/`.

The executable prototype, measured comparisons, source audits, figures and anonymous manuscript scaffold are delivered. The application does **not** yet establish source-valid explanations of the three conflicts. Work is committed directly to `main`; nothing has been pushed or submitted.

## Findings

The primary controlled experiment completed 96 text records from 60 generating SCMs, with 12 development, 12 calibration and 36 test SCMs. Both test paraphrases stay in the same split. All primary synthesis prompts use the same verified AST contract. Another 24 records complete three seeds on the predeclared balanced 12-SCM subset, giving 120 records overall without increasing the number of independent SCMs.

| Primary held-out method | Mean eight-query score | 95% SCM bootstrap interval |
| --- | ---: | --- |
| B0: direct text answer | 0.6771 | [0.6232, 0.7309] |
| B1: text plus generated graph | 0.5903 | [0.5365, 0.6458] |
| B2: first admissible executable model | 0.6927 | [0.5798, 0.8056] |
| P: compatible-rule uncertainty handling | 0.7865 | [0.6753, 0.8854] |

P–B0 is +0.1094, with interval [−0.0208, 0.2292]. Overall superiority is not established. B2–B0 is +0.2292 with complete mechanisms and −0.1979 with an omitted mechanism. Initial/eventual validity is 72/80 of 96 primary records, and 92/100 of 120 records including extra seeds. Failed inference remains in the denominator.

The seed subset yields a P–B0 difference of +0.2049 [−0.0487, 0.4271] after averaging seeds within each of 12 SCMs. It is a sensitivity analysis, not another independent test set. A1 evidence weighting does not establish a ranking improvement. A2 naive summation fails the contrast identity on 26/59 admitted primary test texts; maximum absolute error is 3, while coalition efficiency residuals are zero. A post-hoc benchmark weakness is substantial: all 43 identified structural queries in the incomplete condition preserve the factual outcome; 47 others are ambiguous. The benchmark needs harder identified, outcome-changing queries.

## Application status

The corpus contains 32 Wikipedia television episode Plot summaries and 241 segments. HBO and the television wiki returned HTTP 403; the attempted official Emmy screenplay returned HTTP 404. Exact access records are preserved. Robert's Rebellion was replaced at the source gate with the northern campaign against Bolton rule. No book continuity is mixed into the corpus.

| Principal conflict model | Nodes / edges | Paths | Unsupported edges | Distinct retained functions |
| --- | ---: | ---: | ---: | ---: |
| Five Kings | 10 / 13 | 6 | 12 | 1 |
| Northern campaign | 8 / 12 | 6 | 7 | 1 |
| Daenerys's conquest | 3 / 2 | 2 | 2 | 1 |

Only Five Kings meets the size target; this is not a claim that its ten nodes and mechanisms have independent evidential validation. Two accepted Five Kings generations are functionally equivalent. Three diverse mechanisms per case were not obtained. Source compression and model-construction failures contribute to the shortfalls; source-access limitations alone do not explain them. Earlier and failed generations remain archived, and no graphs were padded.

Every retained principal path has zero weakest-link support because it includes an unsupported mechanism. All weighted segment priorities are therefore zero and provide no informative ranking. The exact path allocations reconstruct each assumed 0→1 model contrast: six equal 1/6 shares for Five Kings and the northern campaign, and two 1/2 shares for Daenerys. Those values are not war probabilities, individual event effects, or historical responsibility. Boundary-derived references preserve these allocations; the alternative domain-endpoint contrast reduces them to zero.

All four final free-text explanations fail the trace audit and are withheld. Some prose confuses path and event contributions or claims a uniquely strongest tied path; some audit outputs quote their own instructions. The northern model also introduces “Edmure Tully (the Blackfish)” despite the personal name being absent from the entire frozen packet; the same-model source critic accepted it. The discrepancy remains flagged without an analyst-supplied identity or causal correction. Source/chronology critique is not independent human adjudication.

Paired application baselines share the frozen packets: 16 questions each for Five Kings and the northern campaign, seven for Daenerys, including four factual/structural questions per case. Canonical intervention counts are 12, 12 and 3; Daenerys falls short of the question target. Literary counterfactual outcomes have no gold labels, so baseline/model agreement is descriptive only.

## Verification, resources and failures

The scientific suite passed **19 tests in 3.40 seconds**. Re-execution reproduces all four models' stored queries and attributions, with 35/35 exact source-offset checks matching the private packets. Maximum application efficiency residual is approximately 1.11×10⁻¹⁶. These are software/traceability checks, not semantic truth checks. Graphviz SVG/PDF figures and the anonymous PDF were inspected by the automated assistant at manuscript scale; no human readability study is claimed.

The campaign took approximately **six elapsed hours** through packaging, within the immutable 24-hour ceiling. Qwen3-14B-AWQ used the existing RTX 4090 for substantive extraction, synthesis, repair, evidence assessment and explanation generation. Model-service residency was **5.67 hours**; sampled utilization-weighted GPU time was approximately **2.49 hours**, which is not billed GPU time. Peak sampled VRAM was **21,996 MiB**. The server counted **935,619 generated tokens**, including interrupted streams where exported; completed responses reported 922,897. There were 956 logged requests and 15 API/JSON request failures; validation failures are additional and preserved. The 316 failure-inventory entries overlap across request, repair and stage levels and are not 316 independent failures. Billing cost is unknown.

Initial setup failures involved tokenizer compatibility and an inherited optional downloader setting. Application failures include malformed ASTs and schemas, ungrounded claims, time/scope mistakes, missing outcome evidence in an earlier retrieval stage, invalid background variables and failed prose audits. Exact development decisions and recovery artifacts are retained. Early timeouts before token checkpointing lack complete partial text; this limitation is recorded rather than reconstructed.

Only the project model-service process group was stopped, at 10:36:42 UTC on 2026-10-12. A subsequent check found 1 MiB GPU use, no compute processes, and a Jupyter HTTP 302 response. The pod, SSH and Jupyter remain running. No billing settings were changed. The project watchdog closes through its `COMPLETE` marker. All 956 exact request specifications were synchronized to the ignored local private prompt cache; credentials, source packets, model weights and caches are excluded from Git.

## Files to review

- [Measured results](../results/RESULTS.md), [primary comparisons](../results/method_comparison.csv), [seed sensitivity](../results/seed_robustness_summary.json), and [benchmark diagnostics](../results/diagnostic_summary.json).
- [Causal paths](../results/causal_paths.csv), [weak-support pathways](../results/influential_weak_support.csv), [segment priorities](../results/segment_priorities.csv), and [sensitivity records](../results/sensitivity.json).
- [Source audit](../results/source_audit.csv), [final source critique](../results/final_source_critique.csv), [variable/equation catalog](../results/variable_equation_catalog.csv), and the [unfilled review form](REVIEW_FORM_GENERATED.csv).
- [Five Kings network](../figures/five_kings_network.svg), [northern network](../figures/northern_campaign_network.svg), [Daenerys network](../figures/daenerys_conquest_network.svg), [paired worlds](../figures/paired_counterfactual.pdf), and [path allocation](../figures/path_contributions.pdf). Each principal network has a JSON source/equation index and a PDF export.
- [Anonymous manuscript PDF](../paper/manuscript.pdf) and [LaTeX source](../paper/manuscript.tex), using the downloaded official template and verified reference metadata.
- [Reproduction instructions](REPRODUCIBILITY.md), [usage](../results/usage.json), [verification](../results/artifact_verification.json), [failure inventory](../results/failures.jsonl), and [published artifact manifest](../results/artifact_manifest.json).
- [Repository storage policy](REPOSITORY_STORAGE.md), [compact reproduction manifest](../results/reproduction_manifest.json), and [clean export validation](../results/release_validation.json). The full run archive and its historical manifest remain local; the compressed release retains the inputs needed to reproduce final analyses.

## Scientific decisions for the researcher

1. Decide whether the negative application findings justify a methods/failure-analysis paper, or whether a new authorized campaign with richer primary sources is needed before making literary claims.
2. Independently review event entailment, aliases, within-episode chronology, outcome scope, reference semantics and structural assumptions. The supplied form is unfilled; no human review has occurred.
3. Strengthen the controlled benchmark's identified intervention coverage and evaluate a factual carry-forward baseline in a newly frozen study. Do not retrofit its post-hoc diagnostic into a predeclared result.
4. Review related-work positioning, source licensing, the manuscript's scientific arguments and the conference's GenAI policy before taking authorship responsibility or submitting.

The second model, independent application seed repetitions, evidence-guided selection ablation and interactive explorer were not run. No paper submission or Git push was performed.
