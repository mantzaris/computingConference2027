# Manuscript outline for human scientific review

Working title: Intervention-guided repair of generative structural equation
models. Include language-model proposals in the title only if measured evidence
supports their utility.

1. Introduction: fixed-budget model repair and prospective intervention
   prediction. Separate diagnostic scheduling from the value of metadata.
2. Related work: DCDI, CMA, causal normalizing flows, ABAPC-LLM and CauScientist.
   Do not claim novelty for combining LLMs, flows and graph verification.
3. Assumptions and method: causal sufficiency, independent disturbances, stable
   intact mechanisms, exact intervention replacement, environment-balanced NLL,
   diagnostic priorities, common score, canonical caching and one-time audit.
4. Experimental protocol: independent SCMs, data budgets including all selection
   observations, controlled corruption separate from real LLM proposals, sealed
   final settings/targets, adapted baselines and acquisition-block real splits.
5. Results: generated tables and Figures F2–F5 only. Report paired effects,
   confidence intervals across SCMs, achieved compute and negative comparisons.
6. Real and semantic cases: metadata controls, actual invalid LLM generations,
   limits of one physical apparatus, quantization and extrapolation.
7. Reliability and limitations: beneficial/neutral/harmful repairs before and
   after audit, adverse examples, convergence failures and model misspecification.
8. Conclusions: supported scope only, subject to Alex's review. No guarantee of
   graph identification, safety, individual counterfactual truth or acceptance.

## Evidence to carry into the results section

- Controlled corruption: 30 independent SCMs, 120 paired size/family/seed/budget/
  corruption conditions. Diagnostic minus fixed T2 SW1 is −0.07815 (95% paired
  SCM interval [−0.10060, −0.05672]); minus random is −0.04825
  ([−0.06652, −0.03211]). Use summary.csv, not individual samples as replicates.
- Achieved compute qualifies that result: a common 12-DAG cap yielded mean
  10.58 versus 9.52 candidates and 9,047 versus 7,525 canonical fitting updates
  for diagnostic versus random. Avoid claiming equal achieved compute.
- Reliability: 84 beneficial, 26 neutral, 10 harmful conditions both before and
  after audit. The largest harmful case rose from 0.246529 to 0.301508 despite
  an accepted graph correction and audit pass (F2_adverse). The uncorrupted
  control has one harmful condition among ten conditions from five SCMs.
- Semantic tasks: diagnostic minus LLM edit is +0.03057 ([+0.01085, +0.05029]),
  n=5 independent SCMs. All LLM-edit runs retained initial graphs because the
  output interface yielded no admissible new candidate. This comparison cannot
  establish the effectiveness or failure of CauScientist itself. Coherent
  metadata provides no clear predictive benefit over anonymous/shuffled controls.
- Real case: coherent diagnostic versus fixed SW1 is 0.090486 versus 0.085665;
  difference +0.004820, conditional ten-row block interval
  [+0.002187, +0.006481]. This is negative evidence for the proposed repair in
  one apparatus, not a causal-identification or apparatus-population estimate.
- Baseline limitations: 47/66 DCDI fits met the strict normalized constraint;
  28/66 required the declared graph projection. Keep all capped fits included.
  Flow versus additive fixed mechanisms has a mixed interval; avoid asserting
  general flow superiority. The restricted additive-repair comparison is more
  favorable but covers only five heteroscedastic SCMs.
- T1 and T3 are separate secondary endpoints, not substitutes for T2. Use
  endpoint_comparisons.csv, endpoint_summary.csv and the explicit claim ledger.

Possible narrow conclusion for Alex to evaluate: disturbance priorities improve
average intervention extrapolation after controlled graph corruption under a
common candidate cap, but the present audit does not remove harmful repairs and
the improvement does not transfer to these semantic and physical cases. Neither
LLM utility nor superiority at equal achieved fitting cost has been established.

Aim for 12–15 main-text pages; keep references and appendices within seven pages.
Use the official LNNS template and a 150–250 word abstract. Anonymous review PDF
must omit identifying names, affiliations, funding and the development repository
URL. Do not fabricate an anonymous artifact URL.

GenAI declaration must distinguish frozen Qwen graph proposal inference,
GPU-trained generative mechanisms, and coding/writing assistance. Human authors
must review and own the protocol, interpretations and final text. Approval has
not been recorded. No submission or registration has been performed.
