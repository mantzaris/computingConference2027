# V3 mechanism catalogue

**Offline authored contract examples. These are not outputs of the new LLM pipeline, and no human review is claimed.**
The natural A/B/C comparison is unrun because the authorized pod cannot initialize CUDA. Original v2 records remain unchanged. Full machine-readable examples, families and provenance are in the reproduction archive.

## Beacon

Outcome: Beacon illuminated.

Family coverage: **exhaustive within declared family**; 1 compatible structural models. Scope assumptions concern this authored controlled system only.

| Variable | Meaning | Factual | Event time | Role |
|---|---|---:|---|---|
| G | Grid available during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 0 | fixed_context |
| B | Backup charged during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 0 | fixed_context |
| S | Safety shutter closed during the stated controlled inspection or trip; 1 means present, 0 absent. | 0 | 0 | fixed_context |
| P | Current available during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 1 | endogenous |
| Y | The harbor beacon is illuminated at noon. | 1 | 2 | endogenous |

<a id="beacon-e1"></a>
### e1: Supplies current without backup

G → P. Direction status: **explicit**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

The available grid supplies current even when the backup is unavailable.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: None within this controlled contract. Alternatives: No additional interpretation invented.

- [beacon_1](../../configs/v3_development.json), passage characters 92–170: Explicit substitution and absence rule in an authored controlled system.

<a id="beacon-e2"></a>
### e2: Supplies current without grid

B → P. Direction status: **explicit**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

The charged backup supplies current even when the grid is unavailable.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: None within this controlled contract. Alternatives: No additional interpretation invented.

- [beacon_1](../../configs/v3_development.json), passage characters 92–170: Explicit substitution and absence rule in an authored controlled system.

<a id="beacon-e3"></a>
### e3: Energizes the exposed lamp

P → Y. Direction status: **explicit**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

Current illuminates the beacon when the safety shutter is open.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: None within this controlled contract. Alternatives: No additional interpretation invented.

- [beacon_1](../../configs/v3_development.json), passage characters 246–339: Explicit joint condition for the finite controlled system.

<a id="beacon-e4"></a>
### e4: Blocks visible illumination

S → Y. Direction status: **explicit**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

A closed opaque shutter prevents illumination even when current is available.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: None within this controlled contract. Alternatives: No additional interpretation invented.

- [beacon_1](../../configs/v3_development.json), passage characters 246–339: Explicit joint condition for the finite controlled system.

### mP: joint/function record

The selector supplies current from either available source.

Grid and backup substitute for each other: either alone supplies current, and neither means no current.

Scope assumptions: The explicitly bounded controlled system is deterministic and has the declared inputs only..
Local coverage: exhaustive; 1 compatible functions. Inputs: G, B. Unknown rows: [].

| Input tuple | Compatible output values |
|---|---|
| `[0, 0]` | `[0]` |
| `[0, 1]` | `[1]` |
| `[1, 0]` | `[1]` |
| `[1, 1]` | `[1]` |

Constraints are traceable to evidence or assumptions individually:

- `P_r0` (evidence): inputs `{'G': 1}` permit `[1]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 92–170: Explicit substitution and absence rule in an authored controlled system.
- `P_r1` (evidence): inputs `{'B': 1}` permit `[1]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 92–170: Explicit substitution and absence rule in an authored controlled system.
- `P_r2` (evidence): inputs `{'G': 0, 'B': 0}` permit `[0]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 92–170: Explicit substitution and absence rule in an authored controlled system.

### mY: joint/function record

The exposed lamp illuminates when supplied with current.

Current and an open shutter jointly enable illumination; closure blocks illumination even with current.

Scope assumptions: The explicitly bounded controlled system is deterministic and has the declared inputs only..
Local coverage: exhaustive; 1 compatible functions. Inputs: P, S. Unknown rows: [].

| Input tuple | Compatible output values |
|---|---|
| `[0, 0]` | `[0]` |
| `[0, 1]` | `[0]` |
| `[1, 0]` | `[1]` |
| `[1, 1]` | `[0]` |

Constraints are traceable to evidence or assumptions individually:

- `Y_r0` (evidence): inputs `{'P': 0}` permit `[0]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 246–339: Explicit joint condition for the finite controlled system.
- `Y_r1` (evidence): inputs `{'S': 1}` permit `[0]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 246–339: Explicit joint condition for the finite controlled system.
- `Y_r2` (evidence): inputs `{'P': 1, 'S': 0}` permit `[1]`. Literal controlled rule or factual row; not a literary generalization.
  [beacon_1](../../configs/v3_development.json), passage characters 246–339: Explicit joint condition for the finite controlled system.

### Fixed-family intervention results

| Query | Intervention | Outcome set | Coverage |
|---|---|---|---|
| q1 | `{'G': 0}` | `[1]` | exhaustive_set |
| q2 | `{'G': 0, 'B': 0}` | `[0]` | exhaustive_set |
| q3 | `{'S': 1}` | `[0]` | exhaustive_set |
| q4 | `{'B': 0}` | `[1]` | exhaustive_set |

These numbers execute the authored contract; they measure neither discovery accuracy nor reader comprehension. Every intervention reuses the same family and factual boundary values.

## Ferry

Outcome: Delivery recorded.

Family coverage: **exhaustive within declared family**; 8 compatible structural models. Scope assumptions concern this authored controlled system only.

| Variable | Meaning | Factual | Event time | Role |
|---|---|---:|---|---|
| P | Permit possessed during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 10 | fixed_context |
| B | Boat ready during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 10 | fixed_context |
| C | Parcel crosses during the stated controlled inspection or trip; 1 means present, 0 absent. | 1 | 11 | endogenous |
| Y | The parcel is recorded as delivered at the far-bank station by noon. | 1 | 12 | endogenous |

<a id="ferry-e1"></a>
### e1: Possible departure authorization

P → C. Direction status: **unresolved**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

Permit possession is a proposed departure input; the missing rule leaves its influence unresolved.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: Unobserved function rows. Alternatives: No additional interpretation invented.

- [ferry_3](../../configs/v3_development.json), passage characters 274–324: The departure rule is explicitly partial; no unobserved value is identified.

<a id="ferry-e2"></a>
### e2: Possible transport availability

B → C. Direction status: **unresolved**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

Boat readiness is a proposed crossing input; the missing rule leaves its functional role unresolved.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: Unobserved function rows. Alternatives: No additional interpretation invented.

- [ferry_3](../../configs/v3_development.json), passage characters 274–324: The departure rule is explicitly partial; no unobserved value is identified.

<a id="ferry-e3"></a>
### e3: Triggers the delivery record

C → Y. Direction status: **explicit**. Endpoint support: {"parent": "controlled factual input", "child": "controlled factual state"}.

A crossing parcel is recorded as delivered; no crossing means no delivery record in this controlled system.

Conditions: As qualified in the process and joint mechanism. Qualifications: Author-defined contract example; not LLM discovery..
Gaps: None within this controlled contract. Alternatives: No additional interpretation invented.

- [ferry_2](../../configs/v3_development.json), passage characters 46–212: Explicit complete recording mechanism in the controlled system.

### mC: joint/function record

The departure mechanism is not specified beyond the observed joint input row.

Permission and readiness may interact or substitute, or an input may be irrelevant; the text leaves the other three configurations unknown.

Scope assumptions: The explicitly bounded controlled system is deterministic and has the declared inputs only..
Local coverage: exhaustive; 8 compatible functions. Inputs: P, B. Unknown rows: [0, 1, 2].

| Input tuple | Compatible output values |
|---|---|
| `[0, 0]` | `[0, 1]` |
| `[0, 1]` | `[0, 1]` |
| `[1, 0]` | `[0, 1]` |
| `[1, 1]` | `[1]` |

Constraints are traceable to evidence or assumptions individually:

- `C_r0` (evidence): inputs `{'P': 1, 'B': 1}` permit `[1]`. Literal controlled rule or factual row; not a literary generalization.
  [ferry_3](../../configs/v3_development.json), passage characters 217–273: One known input-output row under the declared two-input scope.

### mY: joint/function record

The station records delivery exactly when the parcel crosses before noon.

One parent; no multi-parent interaction is asserted.

Scope assumptions: The explicitly bounded controlled system is deterministic and has the declared inputs only..
Local coverage: exhaustive; 1 compatible functions. Inputs: C. Unknown rows: [].

| Input tuple | Compatible output values |
|---|---|
| `[0]` | `[0]` |
| `[1]` | `[1]` |

Constraints are traceable to evidence or assumptions individually:

- `Y_r0` (evidence): inputs `{'C': 0}` permit `[0]`. Literal controlled rule or factual row; not a literary generalization.
  [ferry_2](../../configs/v3_development.json), passage characters 46–212: Explicit complete recording mechanism in the controlled system.
- `Y_r1` (evidence): inputs `{'C': 1}` permit `[1]`. Literal controlled rule or factual row; not a literary generalization.
  [ferry_2](../../configs/v3_development.json), passage characters 46–212: Explicit complete recording mechanism in the controlled system.

### Fixed-family intervention results

| Query | Intervention | Outcome set | Coverage |
|---|---|---|---|
| q1 | `{'P': 0}` | `[0, 1]` | exhaustive_set |
| q2 | `{'B': 0}` | `[0, 1]` | exhaustive_set |
| q3 | `{'C': 0}` | `[0]` | exhaustive_set |
| q4 | `{'P': 1, 'B': 1}` | `[1]` | exhaustive_set |

These numbers execute the authored contract; they measure neither discovery accuracy nor reader comprehension. Every intervention reuses the same family and factual boundary values.

## Preserved v2 interpretation audit

This is replay and inspection of earlier LLM output, not a new v3 application result. All seven v2 directional judgments remain unsupported; source priorities remain unavailable. No new edge labels or source judgments were authored to rescue the literary graph.

### V2 X03: Tywin's forces attack Riverrun

Original generated description: Tywin's decision to attack Riverrun is a direct response to Ned Stark's legal and political challenge, aimed at asserting Lannister dominance and retrieving Jaime.

Declared parents: []. Actual local configurations: 1.
Retained same-model description check: True.
Necessary conditions for output one within the assumed function: `[]`.

### V2 X06: Robb calls Northern banners to war

Original generated description: Robb's declaration of independence and mobilization of Northern forces is not causally influenced by the prior event of Stark men being slaughtered by the City Watch.

Declared parents: []. Actual local configurations: 1.
Retained same-model description check: True.
Necessary conditions for output one within the assumed function: `[]`.

### V2 X07: Robb deceives Lannister scout

Original generated description: Robb deceives Lannister scout by sending him to falsely claim 20,000 men against Tywin, regardless of Tywin's forces attacking Riverrun

Declared parents: []. Actual local configurations: 1.
Retained same-model description check: True.
Necessary conditions for output one within the assumed function: `[]`.

### V2 X08: Frey alliance conditional on marriage

Original generated description: Walder Frey allows Stark army passage if Robb and Arya agree to marry his children, regardless of Robb's declaration of war

Declared parents: []. Actual local configurations: 1.
Retained same-model description check: True.
Necessary conditions for output one within the assumed function: `[]`.

### V2 X09: Robb captures Jaime Lannister

Original generated description: Robb captures Jaime Lannister if Robb calls Northern banners to war and Frey alliance is conditional on marriage

Declared parents: ['X06', 'X07', 'X08']. Actual local configurations: 8.
Retained same-model description check: False.
Necessary conditions for output one within the assumed function: `[]`.

- `X06` has positive behavior; example `[{"context": {"X06": 0, "X07": 0, "X08": "refuses to allow the army to cross without marriage agreement"}, "set_to": 1, "before": 0, "after": 1}]`.
- `X07` has inhibitory behavior; example `[{"context": {"X06": 0, "X07": 0, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying"}, "set_to": 1, "before": 1, "after": 0}]`.
- `X08` has categorical or unresolved behavior; example `[{"context": {"X06": 0, "X07": 0, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying"}, "set_to": "refuses to allow the army to cross without marriage agreement", "before": 1, "after": 0}]`.
### V2 W: Conflict outcome

Original generated description: Conflict outcome is active by the end of season 1 if Robb calls Northern banners to war, Tywin's forces attack Riverrun, Frey alliance is conditional on marriage, and Robb captures Jaime Lannister.

Declared parents: ['X06', 'X03', 'X08', 'X09']. Actual local configurations: 16.
Retained same-model description check: True.
Necessary conditions for output one within the assumed function: `[{"X06": 1}, {"X03": 1}, {"X08": "agrees to allow the army to cross... in return for Robb and Arya marrying"}, {"X09": 1}]`.

- `X06` has positive behavior; example `[{"context": {"X06": 0, "X03": 1, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying", "X09": 1}, "set_to": 1, "before": 0, "after": 1}]`.
- `X03` has positive behavior; example `[{"context": {"X06": 1, "X03": 0, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying", "X09": 1}, "set_to": 1, "before": 0, "after": 1}]`.
- `X08` has categorical or unresolved behavior; example `[{"context": {"X06": 1, "X03": 1, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying", "X09": 1}, "set_to": "refuses to allow the army to cross without marriage agreement", "before": 1, "after": 0}]`.
- `X09` has positive behavior; example `[{"context": {"X06": 1, "X03": 1, "X08": "agrees to allow the army to cross... in return for Robb and Arya marrying", "X09": 0}, "set_to": 1, "before": 0, "after": 1}]`.

The capture rule retained a negative semantic agreement flag, but that reviewer reason discusses actors and source entailment rather than a precise truth-table contradiction. It is evidence of a nonbinding/mixed review gate, not independent literary adjudication. A one-way “if” statement need not claim necessity. The actual rule also contains scout inhibition absent from its concise prose; this is a mechanism-coverage gap requiring review.
