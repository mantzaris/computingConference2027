# Version 2 error analysis

This is a descriptive stage audit of 72/72 held-out records. Counts can overlap within one SCM; they are not extra independent samples. Examples are the first stable SCM IDs in each category, not a representative error-rate sample. Primary estimates and paired intervals remain those in `test_summary.json`.

| Stage or property | SCM count | First retained examples |
|---|---:|---|
| B1 missing or malformed answer(s) | 1 |  |
| admitted model with unavailable FULL ranking | 40 |  |
| admitted model with zero selected coalition contrast | 43 |  |
| admitted synthesis | 56 |  |
| displayable explanation | 40 |  |
| explanation failed deterministic checks | 15 | v2_scm_278009, v2_scm_278011, v2_scm_278014 |
| generated explanation | 56 |  |
| incorrect unknown-rule flag | 9 | v2_scm_278110, v2_scm_278113, v2_scm_282110 |
| prose not fully supported by same-model review | 7 | v2_scm_282013, v2_scm_278106, v2_scm_282112 |
| rejected synthesis | 16 | v2_scm_278107, v2_scm_278111, v2_scm_278114 |

Unknown-rule declaration errors at the rule level: `{"missing rule not marked unknown": 10}`.

## Retained controlled mechanism families

These are exhaustive within each admitted model's declared unknown flags and fixed graph. A missed unknown flag can collapse a truly unresolved source family to one model. Rejected synthesis is absent from this descriptive family table but remains in every primary denominator.

| Condition | Functionally distinct retained models | Admitted SCMs |
|---|---:|---:|
| complete | 1 | 18 |
| missing_intermediate | 1 | 3 |
| missing_intermediate | 5 | 9 |
| missing_outcome | 1 | 5 |
| missing_outcome | 5 | 13 |
| multiple_missing | 1 | 1 |
| multiple_missing | 25 | 7 |

## What the failures mean

- Formal rejection means no candidate survived the fixed initial generation plus two repairs. It is an end-to-end failure, even if its extracted adjacency remains usable by B1.
- Formal admission means typed, active-input, DAG and self-declared factual consistency. It does not by itself mean faithful extraction of the supplied states or known functions; the separate grounding/function scores expose those errors.
- A wrong unknown-rule flag can make ALT too narrow or unnecessarily uncertain. A correct compatible-family solver cannot recover uncertainty that synthesis failed to mark.
- B2 deliberately supplies one conditional model answer. Its nonabstaining singleton is scored as unsupported when the source family is underidentified; this operational metric is not a calibrated confidence probability.
- Deterministic explanation failures include trace-field names, numbers, identifiers, tie qualifiers and sentence-format failures. A valid-ID reviewer can still accept unsupported prose. Reviewer control accuracy and false acceptance are reported separately; no semantic human gold is available.
- Source ranking measures agreement with a frozen structural-slice label, not reading benefit or a minimal sufficient evidence set. In a factual-value control, known factual states and the stated intervention semantics can answer the question without all positively labeled downstream rules. A zero contrast can therefore make influence-based ranking unavailable while the relevance label remains positive. This metric mismatch is disclosed without changing its frozen definition.
- The explicit controlled texts do not independently vary source reliability. FULL versus uniform support therefore tests the behavior of the implemented weights on this corpus, not a general benefit from weighting heterogeneous narrative evidence.

- Controlled FULL adds family outcome sets to the explanation record but computes its paths and source priorities from one retained model. A ranking unavailable under that assumption can omit evidence relevant to unresolved family behavior. The ranking is not an alternative-mechanism aggregate; the frozen component has not demonstrated robustness to that uncertainty.

## Application-stage failures

Fresh transcript-based construction failed after retained schema, graph, mechanism and representation repairs. Its last composite-event mechanism contradicted its own factual state. A separately labeled refinement of the first earlier LLM proposal reached a six-node model only after dependency retraction, a single verbal-mechanism serialization diagnostic and lossless replay of an already generated literal operand. No researcher selected a story predicate or supplied a table entry.

The retained application has four fixed scope boundaries and only two connected functions. Its unequal six-path game exposes substitution, inhibition and player/reference sensitivity, but all seven directional judgments and all six weakest-link path scores remain unsupported/zero. It yields no evidence-weighted source ranking and only one functional interpretation. Those are failures to establish a grounded, robust war explanation, not reasons to raise scores or pad the graph.

The search is also constrained by an LLM-generated order, at most four direct parents, bounded passage contexts, outcome-ancestor pruning, finite mechanism tables, and active-parent validation. Source-reasoned retraction avoids forcing inactive dependencies but can leave unexplained fixed boundaries. Justified background factors are permitted, yet none survives in this model. No ablation isolates these restrictions from model capability or operational-definition errors; the resulting six nodes are not evidence that only six causes matter.

The application endpoint-reference policy coincides with the factual-null policy on every edge. Their identical zero games are a duplicate null-contrast check, not two distinct robustness scenarios. The different path-collection result remains informative about the specified estimand; no new reference scenario was chosen after inspecting shares.

The application prose is rejected for nonexistent numeric trace-field keys and excess actual sentences. Its reviewer covers all six actual sentence IDs; this is an explanation failure, not the version-1 invented-sentence-ID failure. The reviewer labels all prose sentences supported and scores 3/4 on strict controls, calling the invalid probability claim unverifiable instead of unsupported. This does not establish independent narrative entailment.

Targeted assistant inspection flags planned versus realized actions, composite/misaligned timing, an internally inconsistent outcome audit and reference-policy ambiguity. The raw model remains unchanged. These concerns and the generated scout-inhibition/war-necessity assumptions require researcher adjudication. Full context stays in the private review packet; public source links and equations remain available.

No paired retrieval ablation, second model, additional application seeds, human comprehension study or new northern/Daenerys experiment was run. The frozen controlled AST interface differs from the later application finite-table/serialization interface. Their comparison cannot identify which application repair improved narrative validity.
