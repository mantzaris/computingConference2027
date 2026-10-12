# Primary-source verification for the first draft

Checked 9 October 2026. This is an editorial record, not part of the paper.
The bibliography prefers published versions. No claim of first invention of
LLM-proposed, intervention-verified graph editing is made.

| Key | Primary publication or author source | Use and boundary |
| --- | --- | --- |
| pearl2009 | [Statistics Surveys](https://doi.org/10.1214/09-SS057), [author manuscript](https://ftp.cs.ucla.edu/pub/stat_ser/r350.pdf) | Mechanism replacement and SCM semantics. No identification theorem transferred to this study. |
| papamakarios2021 | [JMLR 22(57)](https://jmlr.org/papers/v22/19-1028.html) | Flow change of variables and tractable densities. |
| durkan2019 | [NeurIPS 32](https://proceedings.neurips.cc/paper/2019/hash/7ac71d433f282034e088473244df8c02-Abstract.html) | Rational-quadratic spline transformations. |
| pawlowski2020 | [NeurIPS 33](https://proceedings.neurips.cc/paper/2020/hash/0987b8b338d6c90bbedd8631bc499221-Abstract.html) | Deep structural mechanisms and exogenous-noise inference. |
| javaloy2023 | [NeurIPS 36](https://proceedings.neurips.cc/paper_files/paper/2023/hash/b8402301e7f06bdc97a31bfaa653dc32-Abstract-Conference.html) | Causal normalizing flows and intervention semantics. Its assumptions do not validate arbitrary learned DAGs. |
| brouillard2020 | [NeurIPS 33](https://proceedings.neurips.cc/paper/2020/hash/f8b7aa3a0d349d9562b424160ad18612-Abstract.html) | DCDI with intervention masking and DSF density. The executed optimizer is an adaptation, not exact native reproduction. |
| hauser2012 | [JMLR 13(79)](https://jmlr.org/papers/v13/hauser12a.html) | Structural information from interventions. |
| zheng2018 | [NeurIPS 31](https://proceedings.neurips.cc/paper/2018/hash/e347c51419ffb23ca3fd5050202f9c3d-Abstract.html) | Differentiable acyclicity background, not a substitute DCDI label. |
| peters2014 | [JMLR 15(58)](https://jmlr.org/papers/v15/peters14a.html) | Residual independence in additive-noise discovery. Diagnostic priorities do not inherit its identification results. |
| peters2016 | [JRSS B 78(5)](https://doi.org/10.1111/rssb.12167) | Invariance and its explicit assumptions. |
| gretton2012 | [JMLR 13(25)](https://jmlr.org/papers/v13/gretton12a.html) | MMD. Adaptive, row-permutation priorities are not calibrated causal tests. |
| gretton2007 | [NeurIPS 20](https://proceedings.neurips.cc/paper_files/paper/2007/hash/d5cfead94f5350c12c322b5b664544c1-Abstract.html) | HSIC independence testing; cited with the proceedings' 2007 year. |
| abdulaal2024 | [ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/fe90657b12193c7b52a3418bdc351807-Abstract-Conference.html) | Causal Modelling Agents already combine semantic graph proposals and deep structural models. |
| li2026 | [UAI 2026, PMLR 337](https://proceedings.mlr.press/v337/li26e.html) | Published ABAPC-LLM, 3631–3667. Fallible semantic constraints and memorization controls. |
| peng2026 | [arXiv:2601.13614](https://arxiv.org/abs/2601.13614) | CauScientist is a preprint. Hybrid initialization, edits and intervention verification predate this comparison. |
| hashimoto2018 | [ICML, PMLR 80](https://proceedings.mlr.press/v80/hashimoto18a.html) | Motivation for worst-case risk. The implemented finite mean/max rule is not its distributionally robust estimator. |
| yao2018 | [Bayesian Analysis 13(3)](https://doi.org/10.1214/17-BA1091) | Predictive stacking motivation, 917–1007 including discussion. This study does not perform Bayesian leave-one-out stacking. |
| gneiting2007 | [JASA 102(477)](https://doi.org/10.1198/016214506000001437) | Energy score. The added anchor penalty changes the optimization target. |
| gamella2025 | [Nature Machine Intelligence 7](https://doi.org/10.1038/s42256-024-00964-x) | Published physical benchmark, 107–118. Actual dataset protocols additionally audited in the application evidence. |
| yang2025 | [arXiv:2505.09388](https://arxiv.org/abs/2505.09388) | Qwen3 model technical report, labeled preprint. |
| holm1979 | [Scandinavian Journal of Statistics 6(2)](https://www.jstor.org/stable/4615733) | Sequential multiplicity correction, 65–70. |

The repository's source-linked novelty reviews were read alongside these sources.
The new contribution is framed as the evaluated diagnostic scheduling procedure,
relative-score selection and initial-model-anchored predictive mixture, together
with comparative evidence on prediction, harm and computation. No literature
review establishes a universal novelty priority for all parts of that combination.

Model provenance outside the reader-facing paper: Qwen/Qwen3-8B revision
`b968826d9c46dd6066d109eabc6255188de91218`, bfloat16; official DCDI source revision
`594d328eae7795785e0d1a1138945e28a4fec037`, with the recorded CUDA/optimizer adapters.
