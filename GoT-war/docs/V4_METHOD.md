# Version 4: application mechanisms and figure portfolio

The delivered [gallery and catalogue](../results/v4/GALLERY.html) covers six television cases; [results](../results/v4/RESULTS.md) distinguish executed scenarios from unresolved narrative counterfactuals. V1–v3 results and the closed v3 inference budget are preserved. This is exploratory application development, not a new benchmark or a controlled comparison.

## Diagnosis and changes

V3 had persistent provenance, partial finite functions and the factual-consistency guard added in `1688384`. Its application wrapper limited a case to seven variables/eight edges, episode ranks 101–110, a 14,000-character packet and retrieval within seven selected scenes. Question selection flipped early variables, and reports foregrounded offline fixtures with fixed unrun statements. Those constraints limited coverage; they did not explain the independent CUDA device failure. V3 still has zero inference and nine unrun A/B/C cells. V2's 77.8% execution versus 56.7% direct accuracy on explicit-rule text does not validate the literary graphs, weighting or richer presentation.

V4 reuses the finite engine and factual guard. The new `v4/corpus.py` acquires whole episode corpora across seasons, records stable scene/line identities and searches beyond a current packet. A scene container can merge locations: context must be read, not accepted as a causal unit. `v4/inference.py` performs separate source passes. The per-pass six-event/five-mechanism response bound is not a case bound; case limits are configurable (22 variables, 32 edges, three parents). Source packets have no case-wide character truncation. Full texts remain local.

Qwen supplied fallible propositions and questions. Current Codex read packets, selected additional context, constructed the final mechanisms, generated explicitly hypothetical functions, and corrected actor/scope errors. This is a disclosed assistant-mediated construction route, not automatic Qwen discovery. Exact prompts, raw responses, original drafts and retrieval/revision histories are retained locally. The public bundle supplies source identities, locations/hashes, final mechanisms, assumptions, scenario specifications, question/results records and request accounting. Same-assistant review is not independent adjudication.

## Mathematical contract

For a fixed acyclic representation, finite domain and declared boundary context, each endogenous variable has

`X_j = f_j(Pa_j, U_j)`, with `F_j(E,A) = { f : f satisfies C_j(E) and C_j(A) }`.

Event occurrence, directional support, functional restriction and computed consequence have separate records. No directional label automatically implies universal necessity, sufficiency or monotonicity. In this portfolio, evidence constraints fix only the observed parent/output configuration. All other rows remain unknown. The choice of graph, Boolean contrasts and fixed boundary is itself an assumption. This broad family can therefore include locally inactive edges despite qualitative evidence for an influence; it is a conservative computational envelope, not the unique family entailed by the narrative.

Every local table is enumerated (at most eight rows here). Limits remain 64 rows, 4,096 local candidates and 512 joint candidates; they were not increased. Global products range from 65,536 to 8,388,608. A sampled singleton never establishes identification. The reported binary sets `{0,1}` are certified because valid compatible witnesses attain both domain values, even though global enumeration is sampled. Coverage is relative to the declared scope.

Two functionally distinct complete scenarios per case add explicit assumptions, not additional evidence. Restricted Boolean ASTs compile to finite tables with declared parents. Every observed state must remain compatible, including factual absence of post-relief encirclement. Scenarios may hold decisions, implementation success and background opportunities fixed; these assumptions are visible, not free residuals fitted per question. The alternatives explore substantive unresolved functions and are not exhaustive natural interpretations or posterior samples.

Two or three case-specific questions are saved before execution. `do(X=x)` replaces only targeted equations; the remaining functions and factual background are reused unchanged. A scenario answer is conditional on its full assumptions. The same two scenarios agreeing is not evidence identification, an individual-event responsibility allocation, or a causal probability. No new path-weighting claim is made.

## Checks and depiction

A: source/description checks combine literal location/hash verification with current-Codex contextual interpretation. Literal matching is navigation, not entailment. B: source phrases and joint descriptions are inspected alongside every finite table; 36 selected formal prose claims are exhaustively checked and must quote actual mechanism/scenario prose. This formalization is incomplete semantic review, not proof of every natural-language sentence. Contradictions produce concrete counterexamples and bounded repair records. Facts cannot be silently relaxed. C: reported outcomes are re-executed. Rendering refuses hidden operative edges or false result fields; its model fingerprint includes functions and questions.

Overview figures show all operative edges, including inactive-in-one-scenario hypotheses. Detail figures identify their local scope and joint mechanism; the overview remains the complete model. Intervention views report all selected questions. Edge labels come from accepted records. Colors distinguish direction evidence, not certainty of equations. Red-tinted nodes mark factual absence. Source and assumption registers, truth tables and unresolved questions are expandable sections in the gallery. No independent review or comprehension study occurred.

## Reproduction and resources

From `GoT-war/`, with the project Python dependencies, Graphviz `dot` and Poppler `pdftoppm` installed:

```sh
python3 scripts/v4_reproduce.py
python3 scripts/v4_reproduce.py --render --expand-gallery
python3 scripts/v4_reproduce.py --source-check
mkdir -p .cache
PYTHONPATH=src python3 -m pytest -q tests/test_v4.py tests/test_v3.py tests/test_v2_runtime.py --basetemp=.cache/v4_pytest
```

The first command checks archive integrity, reconstructs partial/complete families and reproduces results/claims without inference or private transcripts. `--render` produces the 18 SVGs, individual local PDFs/PNGs, combined public PDF and gallery. `--source-check` additionally requires the retained private corpus. Source verification after reacquisition must match the saved passage hashes; changed web pages must not silently replace them. `--pack` requires the original campaign. Raw failed generations and exact source-filled requests remain private, with hashes/accounting in the public bundle.

The self-contained gallery losslessly gzip-compresses its HTML to respect the release cap. Chromium opening was checked. `--expand-gallery` creates an ignored ordinary HTML copy without browser decompression. SVGs are directly accessible; the published PDF contains all 18 pages, while individual PDF exports and PNGs regenerate locally. These packaging choices change no scientific content.

The immutable v4 clock began 2026-10-13 17:09:51 UTC: four-hour target, six-hour ceiling. GPU inference had its own 150,000-token/two-hour ceiling; it stopped after 36,659 generated tokens and 31.5 minutes of service residency. The new authorized pod was healthy; project-only vLLM 0.10.2/Transformers 4.56.2 used pinned Qwen3-14B-AWQ, 12,288 context, half precision, 0.88 GPU fraction, one sequence, thinking disabled, temperature 0.2. Initial output cap 3,000 caused three truncated JSON responses; repaired passes used 4,500 with a smaller per-pass schema. `configs/models.json` is a historical default; `scripts/v4_service.py` contains the actual v4 launch overrides. No paid infrastructure was provisioned. Only owned, identity-verified process groups were stopped.

There is no new novelty claim. PAL and narrative causal-graph positioning remain reviewed in [V3_METHOD.md](V3_METHOD.md); the contribution still needs adjudicated application evidence beyond program execution and fluent graph labels.
