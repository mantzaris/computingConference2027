# War of the Five Kings: first-season armed conflict: path-coalition behavior

Paths are shared-edge coalition players with explicit parent references. Edge union activates a shared edge once; allocations are neither independent event effects nor natural path-specific effects. Cross-model comparisons align the same node meanings and path sequences. The separately labeled path-set sensitivity changes the player collection and therefore the estimand.

| Model | Coalition outcome histogram | All paths required | Substitute path sets | Negative marginals | Allocation vector |
|---|---|---|---|---:|---|
| five_kings_v2_m00 | `{"0": 59, "1": 5}` | False | True | 1 | `[0.26667, 0.26667, -0.03333, 0.26667, 0.21667, 0.01667]` |

## Principal evidence-weighted paths

| Path | Node sequence | Signed allocation | Weakest directional support |
|---|---|---:|---:|
| p1 | X03 → W | 0.266667 | 0.00 |
| p2 | X06 → W | 0.266667 | 0.00 |
| p3 | X07 → X09 → W | -0.033333 | 0.00 |
| p4 | X08 → W | 0.266667 | 0.00 |
| p5 | X06 → X09 → W | 0.216667 | 0.00 |
| p6 | X08 → X09 → W | 0.016667 | 0.00 |

Ranking status: **unavailable: every evidence-weighted priority is zero**.

High-influence, weak-evidence paths remain visible in the table; zero evidence weights are never raised to create an ordering. Equal allocations are a model consequence, not automatically an informative explanation. In particular, unanimity and substitutable-path games can both have equal Shapley shares, so their coalition distributions must also be inspected.

## Reference and path selection sensitivity

| Scenario | Baseline | Full | Coalition histogram | All selected paths required | Shares |
|---|---:|---:|---|---|---|
| declared | 0.0 | 1.0 | `{"0": 59, "1": 5}` | False | `[0.26667, 0.26667, -0.03333, 0.26667, 0.21667, 0.01667]` |
| factual_null | 1.0 | 1.0 | `{"1": 64}` | False | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` |
| domain_endpoint_stress | 1.0 | 1.0 | `{"1": 64}` | False | `[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]` |
| four_paths | 0.0 | 1.0 | `{"0": 15, "1": 1}` | True | `[0.25, 0.25, 0.25, 0.25]` |

Factual-null and domain-endpoint references are explicit sensitivity checks, not necessarily meaningful alternative histories. Restricting the player set changes the estimand. A full selected-path coalition need not cover every explanatory route in a larger graph.

The factual-null and domain-endpoint edge-reference assignments are identical in this retained model. Their zero allocations are the same null-contrast result, not two distinct robustness scenarios. Only the declared versus null reference assignments differ here. No additional reference history was selected after inspecting allocations.

Principal minimal full-outcome coalitions: `[[1, 2, 4, 5], [1, 2, 4, 6]]`. Pair-interaction range: `[-1, 1]`.

## Aligned path-set sensitivity

| Shared node sequence | Full collection share | Four-path collection share |
|---|---:|---:|
| X03 → W | 0.266667 | 0.250000 |
| X06 → W | 0.266667 | 0.250000 |
| X07 → X09 → W | -0.033333 | 0.250000 |
| X08 → W | 0.266667 | 0.250000 |

These comparisons match the same node sequences within the fixed model. Changing the collection also changes which edges are coalition-controlled; edges outside the selected union retain their normal mechanisms. Shared-edge activation can consequently change an allocation or its sign without changing an equation. This sensitivity is a property of the defined coalition estimand, not a discovery that a narrative event changes historical causal responsibility.

Edges outside the four-path union: `[["X06", "X09"], ["X08", "X09"]]`. The four-path game has no substitute full-outcome coalition and requires all its players. The scout path bundles a needed downstream edge even when the scout input itself is screened off by another active parent. This explains why a positive bundled-path allocation need not imply a positive event effect.

A negative allocation concerns coalition contexts. It need not equal the effect of removing that event in the factual world. The intervention table supplies that distinct event-effect diagnostic. Neither quantity is a probability.

## Shared outcome queries

| Intervention | Outcome set across retained mechanisms |
|---|---|
| `{"X03": 0}` | `[0]` |
| `{"X06": 0}` | `[0]` |
| `{"X07": 0}` | `[1]` |
| `{"X08": "refuses to allow the army to cross without marriage agreement"}` | `[0]` |
| `{"X09": 0}` | `[0]` |
| `{"X03": 0, "X06": 0}` | `[0]` |
| `{"X03": 0, "X07": 0}` | `[0]` |
| `{"X03": 0, "X08": "refuses to allow the army to cross without marriage agreement"}` | `[0]` |
