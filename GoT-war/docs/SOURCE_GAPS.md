# Source coverage and access gaps

The frozen application corpus contains 32 Wikipedia episode Plot summaries and 241 segmented passages, all from the HBO television continuity. Each application uses its own frozen lexical retrieval packet. Exact titles, permanent revision URLs, hashes, offsets, retrieval membership and license notes are in `data/manifests/`.

Primary-source access was limited. The attempted HBO episode synopsis returned HTTP 403; the television Fandom page also returned 403. The Emmy screenplay URL redirected to the Television Academy and returned 404. Exact URLs, timestamps and statuses are retained in `data/manifests/primary_access_audit.json`. These materials were not inserted into the source packets, and no access restriction was bypassed.

The summaries describe selected events rather than complete scripts or independently verified causal mechanisms. Repeated summaries belong to one dependent editorial source family. They cannot identify counterfactual laws, latent motivations, numerical causal probabilities, or a unique reference world. Short-span matching establishes traceability only; the final source critique can still flag actor/action, episode timing, duplicate-event or reference-state errors.

Robert's Rebellion was replaced by the northern campaign against Bolton rule at the corpus gate because the available retrospective mentions did not provide enough onset evidence. The three frozen outcome questions distinguish war onset, a regional campaign, and continued conquest from individual battle victories.

Graph-size shortfalls and incorrect generated mechanisms must not be attributed solely to source access. They also reflect limitations of retrieval, model synthesis and the explored construction protocols. The archived outcome-packet retrieval defect and its correction are recorded in `docs/DECISIONS.md`. Final node counts and unresolved source critiques are reported in `results/application_summary.csv` and `results/application_audit_summary.json`.
