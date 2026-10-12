# War of the Five Kings: first-season armed conflict: evidence and mechanism audit

Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1.

Automated same-model contextual assessment; independent researcher adjudication pending.

Variables and dependencies initialize from an earlier LLM-generated proposal. Operational states/references are regenerated against the new transcript context, all nonroot mechanisms are newly proposed, and dependency retractions remain possible. This is conditional refinement, not successful fresh variable/dependency discovery.

6 variables, 7 edges, 1 retained functionally distinct models, and 1 distinct intervention-outcome vectors.

Alternative coverage: At most 12: baseline, up to eight round-robin single-function changes in reverse topological order, then bounded joint changes including the all-last-option choice and seeded combinations (seed 2801). Chosen before outcomes/allocations; not exhaustive across combined mechanisms or alternative graphs. No frequency interpretation.

| Variable | Operational definition | Factual state | Event status | Function status |
|---|---|---|---|---|
| X03 | Tywin Lannister assigns half of his forces to Jaime Lannister to attack Riverrun, Catelyn Stark's homeland, as part of a strategy to assert Lannister dominance and pressure the Stark-led coalition. | 1 | established | partially_constrained |
| X06 | Robb Stark formally declares war and mobilizes Northern forces under his command. | 1 | established | unidentified |
| X07 | Robb sends a captured Lannister scout to falsely claim 20,000 men against Tywin | 1 | established | unidentified |
| X08 | Walder Frey allows Stark army passage in exchange for Robb Stark marrying one of his daughters and Arya Stark marrying one of his sons | agrees to allow the army to cross... in return for Robb and Arya marrying | established | partially_constrained |
| X09 | Robb Stark takes Jaime Lannister prisoner during the events of season 1 | 1 | unsupported | unidentified |
| W | Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1. | 1 | established | partially_constrained |

All source references, directional judgments, exact equations and unresolved questions appear in `five_kings_evidence_audit.csv`. Endpoint event support does not establish a causal direction; directional support does not identify the function. Repeated transcriptions/summaries of one episode do not count as independent corroboration. A retained unresolved hypothesis is not an established evidence-compatible mechanism.

## Mechanism behavior

- **X03**: `1`; exhaustive. Necessary conditions for output one: `[]`; individually sufficient: `[]`.
- **X06**: `1`; exhaustive. Necessary conditions for output one: `[]`; individually sufficient: `[]`.
- **X07**: `1`; exhaustive. Necessary conditions for output one: `[]`; individually sufficient: `[]`.
- **X08**: `'agrees to allow the army to cross... in return for Robb and Arya marrying'`; exhaustive. Necessary conditions for output one: `[]`; individually sufficient: `[]`.
- **X09**: `if(eq(X06, 0), if(eq(X07, 0), if(eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), 1, 0), 0), 1)`; exhaustive. Necessary conditions for output one: `[]`; individually sufficient: `[{"X06": 1}]`.
- **W**: `and(X06, X03, eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), X09)`; exhaustive. Necessary conditions for output one: `[{"X06": 1}, {"X03": 1}, {"X08": "agrees to allow the army to cross... in return for Robb and Arya marrying"}, {"X09": 1}]`; individually sufficient: `[]`.

These necessity/sufficiency statements concern the assumed function over its declared domain. They do not assert what would historically have happened in the narrative. Truth tables and all candidate expressions are retained for reproduction and reviewer inspection.

## Construction and mechanism limits

4 of 6 retained variables are parentless scope boundaries; their upstream causes are unexplained. Only 2 retained equations connect endogenous variables. The ten-node reporting target is not met. No nodes are added to meet it.

The fresh source-construction attempt failed and remains separately recorded in `development_audit.json`. Conditional refinement does not demonstrate fresh concept or dependency discovery. Its literal-operand parser recovery preserved an already generated equality predicate and category value; it supplied no story function.

Functionally distinct retained interpretations: 1. A single interpretation cannot establish robust agreement across interpretations. The apparent singleton outcome sets below are single-hypothesis consequences, not source identification.

Displayed figure mechanism summaries are derived from actual behavior. Original generated descriptions/short labels remain in the records; an upstream causal phrase attached to a retracted constant boundary is not displayed as an operative mechanism.

## Targeted inspection flags

Targeted AI-assistant inspection of retained passages, not independent human adjudication and not a sampled error-rate estimate.

No variable, dependency, equation, or evidence score is silently replaced by this inspection. Flags remain visible for researcher adjudication.

- **I03 / X03**: The event label describes an attack while the operational definition describes assignment of forces. The generated short mechanism describes retaliation, but the retained equation is a parentless constant after dependency retraction. Does the variable denote a military order or a realized attack? What directional evidence remains after retraction, and should its generated short mechanism be withheld?
- **I04 / X06**: The source audit treats a late declaration of kingship and allegiance as formal war declaration and mobilization. The generated time is episode 10; the earlier proposed dependency on the episode-9 crossing agreement was retracted. Does the operational state distinguish mobilization, declaration and recognition of kingship, or conflate events at different times?
- **I05 / W**: The event audit labels the factual outcome supported while its reason says the supplied context does not explicitly confirm active armed conflict by the endpoint. Its time and information assessments remain unresolved; every incoming directional score is zero. Does the supplied context establish the specified armed-conflict state at the endpoint? Which evidence supports any exact necessary conditions rather than co-occurring events?
- **I06 / X08**: The categorical states describe allowing passage in return for a marriage agreement versus refusing passage without an agreement. Those phrases can describe the same conditional policy under different unstated circumstances. The model treats them as distinct intervention values. Does the reference mean refusal despite an existing agreement, absence of an agreement, or the same conditional policy? What context remains fixed in the intervention?
