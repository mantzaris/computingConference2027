# V3 bounded development delivery

**Implemented, offline-validated, and inference-blocked. The new generative method is not yet empirically demonstrated.** Versions 1 and 2 remain unchanged; their old held-out test set was not used for tuning. Independent researcher review remains pending.

## What changed

Mechanism records now govern construction rather than serving only as graph annotations. They connect variables, substantive edge/joint prose, source-exact locations, qualifications, functional constraints, explicit assumptions, retained alternatives, and fixed-family intervention results. A diagnosis/retrieval/revision loop precedes complete functions. Unknown rows need no invented output. Exhaustive families, sampled candidates, inconsistent constraints and unavailable executable scopes have distinct statuses.

Source→description review, description→function counterexamples and function→reported-result checks are separate. Negative checks withhold a mechanism instead of replacing its prose with generic table text. The graph renderer uses recorded specific phrases, visible evidence status and catalogue IDs. Source uncertainty can downgrade a display status but cannot upgrade unsupported evidence. No attribution formula or old source score was changed.

## Bounded A/B/C comparison

| Case | A: existing v2 | B: presentation only | C: mechanism first |
|---|---|---|---|
| beacon | Unrun | Unrun | Unrun |
| ferry | Unrun | Unrun | Unrun |
| five_kings | Unrun | Unrun | Unrun |

The three source packets, query references and per-arm allowances were fixed before any inference request. B shares A’s variables/functions and preserves all retained v2 hypotheses; immutable model hashes prevent a presentation-only change from becoming a modeling change. The runner records every stage and failure. All nine planned cells are unavailable, not failed syntheses or zero-accuracy observations. No component gain, prose-quality gain, source-grounding gain, repair success or human comprehension benefit can be estimated. No expansion was run.

The existing authenticated pod and cached Qwen3-14B-AWQ revision were present, with an idle RTX 4090. The dedicated v3 server failed during initialization: CUDA `cuInit(0)=999`, PyTorch reported CUDA unavailable, and opening `/dev/nvidia-uvm` returned `OSError [Errno 5] Input/output error`. Other inspected HTTP ports returned HTML, not a usable inference API. No driver, pod, billing or unrelated service change was attempted.

The immutable service window was 15:02:48–17:02:48 UTC on 2026-10-13, capped at 150,000 generated tokens. It was closed at 2026-10-13T15:09:56.320861+00:00. The failed startup/watchdog attempt lasted 7.1 minutes. **New inference requests: 0; generated tokens: 0; substantive v3 GPU inference: none.** Sampled GPU memory remained 1 MiB with 0% utilization. Only the v3 watchdog needed stopping; the failed model process had exited. The pod, SSH and Jupyter remain available. Billing cost is unknown.

## Offline evidence

| Check | Result | What it establishes |
|---|---:|---|
| Two-input partial-function families | 256/256 matched a bit-mask oracle | Finite constraint enumeration |
| Outcome sets across those families | 1,024/1,024 matched | Uncertainty preservation in the declared mathematical family |
| Authored controlled fixture queries | 8/8 reference sets matched | Execution and representation contracts, not extraction |
| Prior v2 application queries | 8/8 reproduced | Preservation/replay of old numerical results |
| Software tests | 71 passed | Structural, provenance, revision and process contracts; not literary validity |
| New A/B/C inference | 0/9 cells run | No empirical comparison available |

The partial ferry fixture retains eight compatible functions and returns `{0,1}` when the missing departure rule matters. Directly preventing crossing returns `{0}` under the explicit recording mechanism. Sampled agreement is never labeled identified; separately recorded certificates are limited to direct target interventions or witnesses exhausting the declared output domain. Missing intermediate and multiple missing mechanisms, contradictory constraints, background preservation, exact source provenance, invented reviewer IDs, misleading chronology, and concrete necessity/sufficiency counterexamples are covered by the tests.

The preserved v2 record confirms information loss: substantive prose is stored but replaced for operative descriptions; the capture candidate survives a false description-match flag; the renderer uses signs/blank edges. That flag’s reason conflates source interpretation and function agreement, so it is not taken as semantic gold. The actual capture function includes an inhibitory input unmentioned in its short description. The earlier seven unsupported directional judgments and unavailable path ranking remain untouched.

## Acceptance and limits

| Criterion | Status |
|---|---|
| Displayed edges have substantive phrases and evidence status | Implemented; demonstrated on authored fixtures |
| Known description/function contradictions withheld | Deterministically tested; semantic extraction unrun |
| Assumptions remain visible | Implemented in records/catalogue |
| Missing mechanisms survive without becoming complete rules | Exhaustive and sampled contract checks pass |
| Improvement beyond appearance is measured | Formal engine behavior checked; LLM A/B/C gains unmeasured |
| Natural narrative discovery and grounded mechanisms | Not demonstrated |

The finite prototype covers declared integer/categorical domains and at most 64 input rows per function. Enumeration is bounded at 4,096 local candidates and 512 global models; larger candidate spaces are explicitly sampled, and larger local domains remain unavailable. Fixed graph, determinism, omitted variables and hidden confounding are assumptions, not discoveries. Same-model semantic review can miss unsupported bridges or mistranslate prose into formal assertions. A correct solver cannot repair that failure. Source fidelity and researcher adjudication remain unresolved.

The controlled ferry deliberately contains an explicit scope statement for its missing function. It tests preserving uncertainty while interpreting some ordinary event prose, not unrestricted open-domain discovery. V2’s unchanged television wording is a domain mismatch on the two controlled cases; future measurements must disclose it. The presentation-only contrast shares A’s inference costs and cannot rescue a failed base model.

## Next experiment

Restore CUDA/UVM access through the pod operator, then authorize a fresh bounded service window without altering the completed v3 budget. Run the already specified three paired packets. Prioritize whether C extracts the omitted-rule scope, separates permission from action and later belief from cause, and whether its substantive descriptions survive exhaustive counterexamples. Independently adjudicate the Five Kings endpoint and causal bridges before expanding the corpus. If the source→description stage still fails, the next intervention should target evidence coverage or concept revision, not more decorative prose.

This delivery supports an engineering prototype and a sharper failure diagnosis. It does not yet support a new methodological performance claim or an application contribution. The earlier controlled-methods/failure-analysis manuscript remains the measured manuscript; no new completed-study manuscript is claimed.

## Reproduction

Run `PYTHONPATH=src python3 -m got_war.v3.report restore .`, then `PYTHONPATH=src python3 -m got_war.v3.report reproduce .`. Create the ignored temporary parent with `mkdir -p .cache`, then run `PYTHONPATH=src python3 -m pytest -q --basetemp=.cache/pytest_tmp` for the full suite. The compact bundle contains authored fixtures, compatible families, the unchanged v2 model/audit excerpt, protocol versions, blocker/accounting and validation inputs. It excludes full copyrighted passages, credentials, weights, and raw server logs. A fresh private source packet and a working authorized endpoint are needed for new inference.

Files: `docs/V3_METHOD.md`, `configs/v3_development.json`, `results/v3/comparison.json`, `results/v3/component_summary.json`, `results/v3/CATALOGUE.md`, `results/v3/REVIEW_PACKET.md`, `results/v3/validation.json`, `results/v3/reproduction.tar.gz`, and `figures/v3/{beacon,ferry}.{svg,pdf}`. The component table uses nulls for unrun quantities and distinguishes unsupported identification from a conditional singleton hypothesis. The figures are explicitly labeled offline authored contract examples.
