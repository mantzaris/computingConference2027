# Explanation generation and reviewer quality

Software creates the outcome/intervention record before prose generation. The LLM uses supplied values, and software assigns fixed sentence IDs before review. Invalid IDs are reviewer failures; unsupported or numerically invalid prose is an explanation failure. A schema-valid reviewer can still be wrong.

| Component | Estimate [95% SCM interval] |
|---|---:|
| explanation_generated | 0.778 [0.681, 0.875] |
| explanation_deterministic_pass | 0.569 [0.458, 0.681] |
| reviewer_valid_ids | 0.778 [0.681, 0.875] |
| explanation_same_model_supported | 0.681 [0.569, 0.778] |
| explanation_displayable | 0.556 [0.444, 0.667] |
| reviewer_control_accuracy | 0.698 [0.608, 0.788] |
| reviewer_control_false_acceptance | 0.021 [0.000, 0.049] |
| reviewer_control_missing | 0.222 [0.125, 0.319] |

Each controlled reviewer probe includes a true factual value, a flipped factual value, an invalid probability interpretation, and an explicit model/reference-dependence statement. Expected labels are withheld from its prompt. These software-defined controls evaluate simple trace fidelity and interpretation, not subtle literary entailment. Numeric checks verify allowed values, declared field/value claims, identifiers and tie qualifications; they are not a complete natural-language theorem prover. The same model generates and reviews prose, so its judgments are dependent. Independent researcher review remains pending unless a separately recorded response says otherwise.

## Conditional and diagnostic counts

56 explanations contain retained prose; 56 have valid review IDs; 56 control reviews have valid IDs. The primary component table keeps all 72 planned SCMs, including unrun stages. In particular, missing reviews are not false acceptances: read that rate together with reviewer-control missingness.

Among ID-valid control reviews only, strict agreement is 201/224 judgments and false acceptance is 3/112 deliberately unsupported judgments. These are secondary descriptive counts conditional on reaching review, with four repeated controls per SCM; they are not independent-sample confidence estimates.

9 explanations were semantically accepted by the same model despite failing deterministic/format checks. This is a disagreement between limited checks, not an independently measured semantic error rate. A post-hoc whitespace word count finds 2 explanations above the requested 110-word cap; the frozen displayability code does not enforce that cap and its reported scores are unchanged.

Final deterministic error types (one count per SCM/type): `{"invalid_structured_number": 12, "number_not_in_record": 1, "unqualified_largest_among_ties": 1}`. Generation-attempt format errors (one count per SCM/message): `{"At most four actual sentences after software splitting": 7}`.

| Control ID | Expected verdict | Returned verdict | SCM count |
|---|---|---|---:|
| S01 | supported | supported | 41 |
| S01 | supported | unsupported | 15 |
| S02 | unsupported | supported | 3 |
| S02 | unsupported | unsupported | 53 |
| S03 | unsupported | unsupported | 51 |
| S03 | unsupported | unverifiable | 5 |
| S04 | supported | supported | 56 |

The expected verdicts distinguish an unsupported claim from an unverifiable one. Treating the invalid probability interpretation as unverifiable reduces strict accuracy but does not count as falsely accepting it. These controls are repeated measurements, not four independent samples per SCM.

The conditional Five Kings explanation is rejected: six actual sentences exceed the four-sentence request, and numerical claim keys do not exist in the structured record. Its reviewer covers every actual sentence ID and marks all text supported. It scores 3/4 on the separate controls, with no false acceptance. See `application_explanation_audit.json`; source entailment remains unadjudicated.
