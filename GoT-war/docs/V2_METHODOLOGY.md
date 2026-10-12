# Version 2 methodology and departures from version 1

Research question: **Can generative AI synthesize evidence-grounded structural models that support useful, assumption-sensitive explanations of individual and combined causal pathways?**

Version 1 is preserved at the commit and artifact paths in `configs/versions.json`. Its numerical results remain version 1 results. `V2_DIAGNOSIS.md` connects the verified weaknesses to their causes. Version 2 has its own immutable deadline, inference records, outputs and test freeze. A change in method is not evidence of improvement; only the measured paired comparisons support such a claim.

## Three evidence judgments

For a variable, retain an operational definition, domain, actor, actual event time, statement/information time, factual state and references. A narrative event, a report that an event occurred, and a character's belief are different variables. Dialogue establishes an utterance; it does not automatically establish the truth of its content.

For each candidate influence, inspect the relevant passage context and separately record support for both endpoint events, directional influence, exact function identification, contradictions, temporal and information constraints, assumptions, provenance and unresolved questions. Mere chronology/co-occurrence is not directional support. A claim that a parent affects a child is weaker than a claim that it is necessary, sufficient, substitutable or inhibitory in every context.

The fixed display rubric assigns **1** to explicitly supported direction, **0.5** to contextually supported direction with a stated passage-based rationale, and **0** to unsupported/unassessed direction. Unsupported endpoint claims, absent evidence references, contradictions, or unresolved temporal/information constraints force zero. The exact equation's identification status is recorded separately and is never converted into an invented causal probability. Unknown functional form does not itself negate otherwise supported direction. Conversely, a proposed alternative equation cannot rescue an unsupported connection. These are heuristic display weights, not calibrated probabilities or independent human judgments.

The primary source acquisition is bounded to ten first-season television episode transcript pages, at most one hour of acquisition and 30 seconds per request. ScreenScripts supplies attributed dialogue and stage directions, but its transcription fidelity and annotations are not independently authenticated. Alternative transcriptions and summaries of the same episode are dependent records of the same fictional event. A pilot screenplay draft is excluded without an aired-version concordance check. Full text stays in ignored local/private files; public manifests provide URLs, hashes, offsets and limitations. The model receives contextual passages, never analyst-supplied story causes.

## Generated structure and inspectable functions

The LLM discovers substantive variables, definitions, dependencies, equations, assumptions, alternatives, revisions and explanations. Deterministic software validates the restricted AST and its declared parents/backgrounds, types, domains, active dependence, DAG structure and factual compatibility. No unrestricted generated code is executed.

Every accepted function receives a behavior-derived description. Small finite domains are enumerated; larger domains receive labeled bounded probes. Reports expose local input/output rows, contexts where each parent changes the child, necessary and sufficient input conditions, joint enabling, substitution and inhibitory/mixed effects. Statements about these tables describe a model, not historical necessity. Original generated descriptions remain available for discrepancy analysis and are not silently treated as faithful paraphrases of an equation.

Source-supported representation revisions may alter a variable definition, parent set or explicitly justified background context. The protocol does not require every story event to be Boolean or forbid all nonroot background inputs. Background variables require operational definitions, provenance and a stated reason beyond matching the factual row; unrestricted residuals are prohibited. Targeted repair is bounded and its failures are retained. Each accepted model is frozen during intervention execution, with the same factual background reused across worlds.

## Alternatives and partial identification

In the controlled benchmark, enumerate all active deterministic Boolean functions on the declared inputs consistent with recorded factual rows, jointly across unresolved rules. This generalizes version 1's single two-parent special case. The implementation also supports bounded finite categorical/three-parent cases and reports when local or Cartesian coverage is sampled. Coverage is exhaustive only within the stated graph/domain/background/function family, never across arbitrary hidden variables or confounding.

Literary mechanisms are retained as evidence-compatible generated hypotheses with explicit assumptions and behavioral signatures. Compare intervention outcomes and functions, not wording or generation counts. Do not treat sampling frequency as a posterior. Aligned schemas permit corresponding-path sensitivity envelopes; differing schemas require common outcome queries or explicit mechanism-group alignment. One interpretation is an exploratory hypothesis, not agreement across alternatives.

## Path aggregation and evidence priority

Preserve the version 1 union-of-edges coalition game with explicit inactive-edge reference inputs. Shared edges execute once. Report every coalition outcome for small games, minimal full-outcome coalitions, unanimity, substitution, negative marginal effects, pairwise interaction ranges and allocation ties. Equal allocations may arise from conjunction, redundancy or other symmetries; equality alone does not identify the game.

For an intervention explanation, change only targeted equations and freeze everything else. Selected path edges compare counterfactual propagation with factual edge references. If path truncation leaves active omitted routes, the coalition reference need not reproduce the entire factual world: report that distinction. Application reference scenarios, selected path counts and compatible mechanisms receive separate sensitivity analyses. These allocations are not event effects, natural path-specific effects, probabilities or objective responsibility.

Passage priority sums absolute path contributions times weakest-link **directional** support and a declared allocation over supporting evidence clusters. Exact-function uncertainty appears in model envelopes and assumption views. Display influential weak-evidence paths separately. All-zero scores mean that the ranking is unavailable; alphabetical zero ties are never promoted as a substantive ranking.

## Newly frozen evaluation

The development design has 120 independently generated SCMs: 24 development, 24 calibration, 72 test; sizes 8 and 12; complete, missing intermediate, missing outcome and multiple missing rule conditions. All mechanisms use general conjunction, redundancy, XOR, inhibition or NAND families and random DAGs with shared causes. Two rules are omitted in the multiple condition. Explicit deterministic rule texts retain exactly the declared information. No uncontrolled paraphrases or repeated seeds are added to the main design.

Omissions are chosen from graph structure before method inference. Questions enumerate every non-outcome single-state flip, three seeded joint flips and three factual-value controls. No direct outcome override enters the primary queries. The gold-family audit defines identified/underidentified and changed/preserved strata without consulting method outputs. Missing-outcome records with only a factual rule row need not have identified changing interventions; this remaining limitation is explicitly reported rather than hidden. Both factual states and identified changes occur elsewhere in the design. Splits group generating SCMs and all repeated questions.

Paired methods see the same source text: B0 direct answers; B1 source plus the synthesized graph without equations; B2 execution of the first admissible synthesized model; ALT execution over compatible alternatives; FULL uses ALT's answers plus inspected mechanisms, coalition explanation, evidence ranking and prose/review. FULL and ALT share their structural answers by design. Factual carry-forward is a diagnostic baseline. Oracle generating-model and declared-family solvers separate hidden-world prediction from appropriate uncertainty.

Report identified accuracy, changed/preserved accuracy, underidentification handling, unsupported confident answers, synthesis/repair validity, known-function agreement, evidence grounding, source ranking, explanation fidelity, reviewer behavior, runtime and tokens separately. Failures stay in primary denominators; conditional-on-synthesis results are secondary. Confidence intervals and paired differences resample SCMs, not questions. No composite score certifies the whole pipeline.

For source ranking, an independently defined gold causal slice contains descendants of intervened variables that are ancestors of the queried outcome, excluding intervened equations. A relevant paragraph gets grade 2 for an available rule, 1 for an explicitly missing rule and 0 otherwise. This assesses structural information relevance, including useful uncertainty statements; it is not a human ranking of literary importance. Labels do not depend on generated paths. Compare FULL with uniform support and direct/graph source rankings. In this initial rule-text benchmark, documented directions are explicit even when functions are absent; it does not independently calibrate graded literary support.

## Explanation and review gates

A structured record precedes prose: exact intervention/outcome, computed states and outcome sets, mechanisms, paths, reference/full values, allocations and ties, evidence status and assumptions. The LLM explains these supplied values without recalculation. Each generated sentence receives a fixed software-assigned ID before semantic review. The reviewer must return each actual ID exactly once; invented IDs, missing sentences or quoted audit instructions are reviewer failures.

Deterministic checks cover numbers, identifiers, ties and probability terminology. Semantic review separately addresses interpretation and entailment. Reviewer format failure is distinguished from an unsupported explanation. Known factual-value and probability-interpretation control sentences assess the reviewer against controlled labels; these controls do not validate the literary model. A researcher review packet remains unadjudicated unless an actual review occurs.

The end-to-end gate covers four benchmark omission conditions and one Five Kings construction before test inference. Repairs are targeted and bounded; no unchanged broad regeneration is allowed. Freeze achievable sample size, prompts, analysis and token ceiling from measured throughput before test requests. The temporary pilot ceiling is 80,000 output tokens; it is not inherited from version 1's million-token ceiling and is replaced by a measured campaign allowance before scaling.

## Engineering and publication boundaries

The version 2 24-hour deadline starts conservatively before initial inspection, reserves at least four hours after heavy work, and survives restarts. The remote watchdog verifies process birth identities; unverified launches fail before registration. Only project-created jobs may be stopped. Version 2 checkpoints synchronize every 20 minutes. No new pod, paid external inference, unrelated-service restart, push or paper submission is authorized or performed.

Keep the existing 250-file, 8-MiB-total, 2-MiB-per-file staged release limits. New results, figures and manuscript are versioned in dedicated subdirectories, with curated compressed reproduction records and raw candidates retained locally. The final scientific claim must follow measured component results and the actual level of source adjudication, whether that supports an application, narrower methods or failure-analysis contribution.

Development clarification: the flagship outcome keeps version 1's first-season armed-conflict endpoint and removes the subsidiary clause about wider royal claims through S2E4, because the new transcript corpus ends at S1E10. The initial source-extraction records were preserved under `application/five_kings_scope_pilot`; the source-aligned construction restarts before variable/graph selection. No story-specific variable or mechanism was supplied by this clarification.

The first four-case inference pilot produced 18,001 output tokens in 378.49 request seconds (47.56 tokens/s). Its size-eight per-case cost, multiplied by 120 SCMs and a conservative 1.4 size/variation factor, projects 756,042 tokens. Adding 220,000 for the application and 100,000 for targeted repairs/limited transfer yields 1,076,042; the campaign safety ceiling is rounded to 1,100,000. At half measured throughput this requires about 12.85 inference hours, within the separate absolute deadline and four-hour delivery reserve. The ceiling is not an instruction to consume the allowance.
