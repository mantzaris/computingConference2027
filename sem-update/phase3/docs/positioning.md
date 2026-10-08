# Scope of the scaling contribution

The proposed contribution is a controlled study of disturbance-guided repair,
robust selection and anchored prediction under finite fitting resources, using
independent intervention prediction and harmful-repair evaluation. Phase three
tests its limits on connected, relabeled 20–100-node systems and specified dense,
hub and deep topologies. It does not establish a new causal identification
theorem or the novelty of flow-based causal discovery, robust objectives or
predictive mixtures.

[DCDI (Brouillard et al., 2020)](https://arxiv.org/abs/2007.01754) already combines
interventional discovery with expressive neural conditional densities. Its
Section 4.2 and Appendix C.3 report scalability experiments through 100 nodes.
Therefore, merely executing a flow-based causal method at 100 nodes is not a
novelty claim. Our DCDI-DSF comparison uses the pinned upstream density with the
documented phase-two optimizer adaptation, followed by common flow refitting.
This is not a reproduction of every published tuning choice. Resource caps,
soft-constraint residuals, graph projections and coverage must accompany its
prediction results. A capped adaptation cannot establish that fully converged
DCDI generally performs poorly.

[CauScientist (Peng et al., 2026)](https://arxiv.org/abs/2601.13614) already uses
LLM graph proposals, a statistical verifier and iterative refinement with error
memory. Its experiments include a 37-node benchmark. Neither the proposal/verify
loop nor testing larger graphs is claimed as our invention. Phase three is a
controlled-corruption comparison, with no new LLM generations. It cannot support
claims about large-graph LLM proposal quality. The functioning phase-two LLM
adaptation and its interface diagnosis remain separate evidence.

The [phase-two source-linked review](../../phase2/docs/novelty.md) retains the
comparisons with CMA, causal normalizing flows and ABAPC-LLM. These citations
motivate a narrow empirical claim, conditional on the frozen generators,
partitions, common mechanism class and measured computation. The proposed
extensions remain proposed extensions; a broader priority claim would need a
separate, more exhaustive review. Primary sources above were rechecked on
8 October 2026 UTC. Alex's scientific review remains pending.
