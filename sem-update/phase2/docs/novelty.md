# Scope of the proposed extensions

Phase two tests proposed extensions to this implementation. It makes no claim
that robust prediction objectives, energy scores or predictive mixtures are new.

- [DCDI (Brouillard et al., 2020)](https://arxiv.org/abs/2007.01754)
  establishes neural intervention-aware discovery, including the DSF variant.
  Use the [official source](https://github.com/slachapelle/dcdi) at the recorded
  revision; distinguish discovery from common-flow refitting.
- [Gneiting and Raftery (2007)](https://doi.org/10.1198/016214506000001437)
  establishes proper scoring rules including the energy score. Our fixed-sample
  distance-matrix objective is a computational implementation of that score,
  with an explicit initial-model anchoring penalty, not a new propriety theorem.
  The [author-hosted published article](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)
  provides an accessible primary copy. The anchoring penalty changes the
  optimization target; it does not inherit strict propriety automatically.
- [Yao et al., Bayesian Analysis (2018)](https://arxiv.org/abs/1704.02030)
  develops stacking of predictive distributions under proper scoring rules.
  Our weights are learned from a separate intervention calibration partition;
  this is not their leave-one-out Bayesian procedure or a causal posterior.
- [CauScientist](https://arxiv.org/abs/2601.13614) and the phase-one novelty review
  already establish LLM-guided graph refinement. Repairing our failed output
  interface does not establish novelty or invalidate that research method.
- [Hashimoto et al. (ICML 2018)](https://proceedings.mlr.press/v80/hashimoto18a.html)
  uses distributionally robust worst-case risk to control subgroup error. Our
  finite calibration-environment mean/max rule is not that algorithm and does
  not inherit its guarantees. Worst-case prediction criteria are established.

The narrow empirical question is whether worst-environment selection or an
anchored whole-SCM predictive mixture improves reliability when the fitted
candidate bank is held fixed. Literature priority and human scientific approval
remain unestablished. See the [source-linked historical review](../../docs/novelty.md)
for CMA, causal normalizing flows, ABAPC-LLM and residual/invariance antecedents.
Verified metadata for the additional extension references is retained in
[extension_references.bib](../paper/extension_references.bib).
