# Prior-work check and narrow empirical question

Search cutoff: 6 October 2026 (America/New_York); retrieval on 7 October UTC.
This is an execution review for Alex, not human approval or a priority claim.

| Primary source and method inspected | Established overlap | Remaining comparison |
| --- | --- | --- |
| [DCDI, Brouillard et al., NeurIPS 2020, §§3, B](https://arxiv.org/html/2007.01754v2) | Intervention-aware neural densities, shared intact mechanisms, flow variant, differentiable graph learning and unseen-intervention evaluation. | Limited local repair of an imperfect supplied DAG, measured against intervention-aware discovery. |
| [CMA, Abdulaal et al., ICLR 2024, §3 and Algorithm 1](https://proceedings.iclr.cc/paper_files/paper/2024/file/fe90657b12193c7b52a3418bdc351807-Paper-Conference.pdf) | LLM hypotheses, DSCM fitting, graph likelihood feedback, memory, global and local edge amendment. Full PDF downloaded and method text inspected after OpenReview browser challenges. | Diagnostics as an explicit scheduling policy under matched candidate limits; independent intervention prediction and harmful-repair measurement. |
| [Causal normalizing flows, Javaloy et al., 2023, §§3–5](https://arxiv.org/html/2306.05415) | Architectural causal consistency, exogenous-noise inversion and do/counterfactual operations. | No claim that spline mechanisms or their causal semantics are new. Test the graph masks and intervention implementation. |
| [ABAPC-LLM, Li and Russo, UAI 2026](https://proceedings.mlr.press/v337/li26e.html) | Defeasible structural suggestions from LLMs, observational constraints and metadata/memorization concerns. Method inspected in the linked [preprint](https://arxiv.org/html/2602.16481v1); final bibliographic record verified as PMLR 337:3631–3667. | Continuous intervention-distribution prediction with anonymous and shuffled metadata controls. |
| [CauScientist, Peng et al., arXiv:2601.13614v1, §§3 and B](https://arxiv.org/html/2601.13614v1) | Hybrid initialization; LLM add/delete/reverse edits; intervention-aware masked neural likelihood; complexity penalty; rejected-edit memory. | Disturbance priorities, a common candidate-DAG cap, a common continuous flow verifier, separate audit and independent T2 predictions. Achieved fitting work must also be reported. LLM-edit baseline is explicitly a continuous-data adaptation, not a reproduction of published scores. |

The combination of LLM proposals, causal flows, and intervention-scored editing
is established. Our testable hypothesis is whether held-out disturbance
diagnostics improve the allocation of a small graph-fitting budget relative to
uniform scheduling and actual LLM edits. An unsuccessful hypothesis remains a
reliability result; do not rename mixed or adverse findings as success.

[EvoCause, arXiv:2607.27290](https://arxiv.org/html/2607.27290) further establishes
LLM graph refinement with validation and anonymous controls, in alarm-based
root-cause analysis. [CausalSteward, arXiv:2607.01936](https://arxiv.org/html/2607.01936)
is an additional agentic discovery comparison. These sources rule out broad
claims of first LLM graph repair. This focused review does not establish absence
of an identical diagnostic policy elsewhere. No new identifiability theorem,
safety guarantee, or state-of-the-art claim is authorized by this review.

Residual independence and environment invariance are also established tools.
[RESIT and additive-noise discovery](https://jmlr.org/papers/v15/peters14a.html)
use regression residual independence for graph discovery.
[Invariant causal prediction](https://arxiv.org/abs/1501.01332) uses stability
across environments and provides inference guarantees under its assumptions.
Our adaptive, capped diagnostic scores do not inherit those guarantees. The
proposed contribution remains a comparative repair-budget and reliability study,
not the invention of residual diagnostics or causal invariance.

Scientific gate: proceed with a controlled comparative reliability study. Final
novelty wording requires Alex's review of the evidence and closest methods.

Post-evaluation qualification: the controlled-corruption prediction comparisons
favor diagnostic scheduling, but achieved fitting updates differ between
methods. The present LLM-edit output interface yielded no admissible new
candidate; semantic and real-case repair results are adverse. These outcomes
support a narrowly scoped repair/reliability report, not superiority over
CauScientist, a general benefit from semantic metadata, or equal-compute
efficiency. The detailed failed adaptation is retained in the evidence report.
