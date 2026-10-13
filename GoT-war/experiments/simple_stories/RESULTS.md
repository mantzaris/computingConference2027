# Three simple stories: results

**The reference solver checks succeed; the autonomous model-construction check fails in this run.** These are three introductory development cases, not evidence of general narrative understanding. All previous Game of Thrones results remain unchanged.

## Outputs and reproduction

[Three-page vector PDF](FIGURES.pdf); individual SVGs: [Humpty Dumpty](humpty.svg), [The Boy Who Cried Wolf](wolf.svg), [The Crow and the Pitcher](crow.svg). These figures show **Codex-authored frozen reference SCMs**, not successful Qwen models. Independent researcher review remains pending.

Run from `GoT-war/`: `python3 scripts/simple_stories.py`. No GPU or network is required. The command verifies hashes, rebuilds reference and available generated families, checks claims/mutations, writes [COMPARISON.tsv](COMPARISON.tsv), and renders the figures. Local individual PDFs, PNG previews, expanded machine-readable results and the source/claim review packet go under `.private/simple_stories/` and are regenerated. `records.json.xz` publishes exact requests, first outputs, repairs, audits, usage and a result snapshot; `frozen.json` contains all six numbered texts and reference specifications.

## Separate measurements

| Check | Result | Interpretation |
|---|---|---|
| Author reference factual reconstruction | 3/3 models | Existing SCM engine agrees with all 19 reference variable values. |
| Author reference interventions | 12/12 | Four frozen questions per story; rules are controlled author specifications. |
| Qwen first constructions | 0/3 natural; 0/3 controlled valid | Failures remain in the primary denominator. |
| Qwen direct answers | 12/12 correct | 4/4 in each story, including joint and unchanged outcomes. |
| Qwen executed answers | 0/12 obtained correctly | All 12 unavailable because construction failed; no wrong computed answers are fabricated. |
| Bounded repairs | 0/3 valid | Every repaired parsed object exactly repeats its first attempt. |
| Qwen executable factual reconstruction | 0/3 controlled, 0/3 natural | No accepted full generated model exists. |
| Natural-story uncertainty answers | 0/3 valid answers; 3 unavailable | Compiler failure is not credited as appropriate epistemic abstention. |
| Targeted mutation checks | 4/4 detected | AND→OR, dropped necessary input, reversed inhibition, false sufficiency. |


Questions are clustered within three stories. No hypothesis test, question-level confidence interval or composite score is appropriate. Successful-synthesis-only accuracy and full generated behavioral equivalence are undefined because there are no successful syntheses.

## Source and factual audit

Codex reviewed the complete short passages and each output, without correcting the generator. The counts below concern **asserted event/state values**, not executable reconstruction. Null states and statements about what the narrator omits are excluded. Detailed item IDs, exclusions, citations and prose translations are in the archived audit and the reproducible local review packet. Literal citation existence alone is not source entailment.

| Story/version | Supported factual assertions | Confirmed source-support issues | Important finding |
|---|---|---|---|
| humpty / natural | 4/6 | 4 | Invents permanent irreparability and makes missing information its cause; reverses two temporal edges. |
| humpty / controlled | 6/6 | 1 | Correct facts, but an edge confuses damage needed for repair success with damage needed to attempt repair. |
| wolf / natural | 8/8 | 3 | Preserves a null prevention possibility but overstates three factual descriptions as necessity claims. |
| wolf / controlled | 5/6 | 1 | Incorrectly says villagers responded in time; exact prose is represented only by partial positive rows. |
| crow / natural | 8/8 | 3 | Useful event sequence, but undefined outcome ID, missing mechanisms and unjustified necessity claims. |
| crow / controlled | 8/8 | 4 | Adds an unsupported intact-pitcher prerequisite for adding stones; some edges omit required qualifiers. |


These are fallible assistant judgments, not human adjudication. Source issues count explicitly listed claim/variable/mechanism records, sometimes sharing one underlying mistake; they are not independent observations. The generator did not invent an egg or the boy's death. Natural Humpty nevertheless asserts irreparability twice. Added-rule origins are visible in our frozen packet and figures, while the generated models leave their assumption arrays empty.

## Why construction failed

All six first outputs parse as JSON, but put edge and claim arrays at the top level instead of inside mechanisms. The flat edges lack child IDs, so assignment cannot safely be guessed. Humpty and Wolf also label mechanism-dependent variables as fixed context. Natural Crow names a nonexistent outcome (`drank`) and omits mechanisms for several endogenous variables. An automatic schema repair would require substantive choices; none were silently made.

The original repair feedback was only `KeyError: edges`, an insufficiently actionable diagnostic. Three bounded repair responses repeated their originals. The implementation now collects missing nesting, contradictory boundary declarations, unknown outcome IDs and absent mechanisms into one diagnostic, but this improvement has **not** been evaluated in a fresh generation run. No prompts or reference answers were changed to obtain a better score.

## Description/function agreement and uncertainty

Local diagnostics inspect the generated row constraints even when the full record is invalid; they do not silently repair or execute the graph. All 11 controlled mechanism descriptions state exact rules, yet all 11 leave incompatible behavior in their partial families. Every complete expression is null. This is not responsible uncertainty about these explicitly stated rules: it is incomplete encoding. The Wolf response and harm descriptions additionally conflict with its wrong factual response value.

Conversely, natural rows leave 13, 7 and 13 local input rows variable for Humpty, Wolf and Crow respectively. The software preserves them. This is useful partial data, but invalid representations and unsupported prose prevent credit for an end-to-end uncertainty answer. Humpty loses uncertainty through irreparability claims; Wolf and Crow mention missing information but do not produce valid models.

All nine generated natural-story necessity predicates admit counterexamples in the local families; the prose usually describes a factual sequence or a sufficient condition instead of necessity. All eleven controlled exact-claim records omit the required rule field. The audit therefore distinguishes a malformed formal record from the actual proposition expressed by the prose. These checks update the simple-stories validation without silently rescoring archived v4 results.

The new necessity check quantifies over **every completion of the other inputs**. For example, under `Y = A OR B`, `(A=0, B=1, Y=1)` refutes “A is necessary,” even though `(0,0)` produces zero. A conjunction test checks each factor's necessity and their joint sufficiency. Inhibition checks paired contexts and a strict effect; an existential effect is distinct from universal monotonicity. Reference equations are exhaustively finite, with at most eight local rows. Mutation counterexamples and every inspected prose claim are retained. Formal checks establish agreement with a translated proposition; Codex's translation of prose remains reviewable, not independently validated.

## Figures and comparison

All operative reference edges are shown, labelled with specific phrases and sentence IDs. Rules are explicitly identified as assumptions introduced by the controlled adaptations. No failed generated graph is presented as accepted. The [comparison table](COMPARISON.tsv) lists every frozen question, expected answer, direct answer, failed executable answer, correctness and separate reference execution.

**Best introductory figure: [The Crow and the Pitcher](crow.svg)** (PDF page 3). Its short stone → rise → reach → drink sequence also reveals a useful distinction: adding stones is not universally necessary when the water is initially reachable. It shows a joint requirement, substitution, and an unchanged-outcome intervention without numerical fluid mechanics. The figure illustrates the author-specified method, not autonomous causal discovery.

## Resources, failures and limits

Qwen/Qwen3-14B-AWQ, revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, AWQ, vLLM 0.10.2, thinking disabled, temperature 0.2, recorded seeds, on the existing RTX 4090. 12 requests (9 first, 3 repairs), **18,814 generated tokens**, 16,509 prompt tokens; 234.4 seconds in requests and **6.26 minutes of service runtime**, including startup and a missing-module launch failure. Peak sampled GPU allocation: 22,012 MiB. The project watchdog stopped only its registered model service after completion. Budget: 40,000 generated tokens or one hour, whichever first. No new pod or paid API was used.

Verification: 98 software tests passed, including 15 new targeted tests. A public-only staged export reproduced all three SVGs, the three-page PDF, the comparison table and this report byte-for-byte. These software checks do not establish source validity.

The first runner failed before inference because existing solver modules were absent remotely. Synchronizing project code resolved it within the same budget. There were no request transport failures or JSON parse failures. The archived original runner/validation logs distinguish execution-time behavior from later diagnostic improvements. Codex authoring/review token usage is unavailable; it is not included in Qwen usage.

These checks establish that the supplied controlled reference SCMs execute correctly and that stronger quantified checks expose false causal claims. They do **not** demonstrate reliable autonomous construction from these narratives; direct answers succeed where the structured pipeline fails. Nor do they validate the traditional tales' counterfactuals, general narrative understanding, reader comprehension, or the Game of Thrones interpretations.

A bounded next experiment should test schema-constrained output with aggregate compiler feedback on these already-development cases, keeping the same references and reporting it as a new attempt series. Its central question is whether it yields a valid model **without** fixing factual/prose mistakes by hand. Independent review should adjudicate the claimed irreparability, the Wolf factual-response error and the extra crow prerequisite before using any generated narrative claim in a paper.
