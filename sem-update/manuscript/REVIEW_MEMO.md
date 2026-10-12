# First-draft review memo

This is a complete anonymous first draft, not an approved submission. No new
experimental study was run. The paper synthesizes evidence preserved at
`ad21e60`, `8c452ac`, `a17a8f7` and `6b836ef`. Those identifiers and this memo do
not appear in the reader-facing PDF.

## Scientific review decisions

1. **Confirm the contribution and physical interpretation.** The paper presents
   disturbance-guided scheduling, shared-bank robust selection and anchored
   predictive combination as methodological developments and empirical tests.
   It makes no priority claim for combining an LLM, a graph and an intervention
   verifier. The wind-tunnel static model remains a predictive approximation
   with serial dependence, omitted pathways and one apparatus. Its missing
   hatch pathway is checked against randomized total effects, not direct-edge
   identification. Alex should review these assumptions and the claim strength.

2. **Resolve the DCDI reporting convention in future research documentation.**
   The principal small-system implementation stopped using
   `h(A) / max(1, h(A_allowed)) <= 1e-8`, where `A_allowed` is the binary permitted
   adjacency matrix, together with a thresholded DAG. Its compact table records
   29/30 optimizer-stopping successes. None satisfies the separate raw `h(A)/d`
   criterion used by the scaling and wind studies. Five controlled outputs
   require projection. The manuscript states both criteria explicitly rather
   than calling the 29 fits strictly converged under a common rule. No result,
   fitted graph or historical report was changed. Review the distinction before
   using the historical word “strict” again. Relevant code is
   `src/sem_update/dcdi.py`, `src/sem_update/phase2/discovery.py` and
   `src/sem_update/phase3/discovery.py`; the source-linked numerical checks are in
   the manuscript evidence mapping.

3. **Review authorship, prior dissemination and AI-policy compliance.** The
   declaration accurately covers coding, execution workflows, analysis support
   and drafting. It does not claim completed human approval. The current
   [venue policy](https://saiconference.com/Computing/CallforPapers) requires
   human critical review and editing and reserves development of the scientific
   ideas, arguments, results and conclusions to human authors. Recorded
   assistance was broader than language editing. Human responsibility alone
   does not establish compliance with that restriction. Alex must assess the
   actual division of work and the declaration against the policy before any
   submission. If clarification is needed, that is a separate author action.
   The full author list, prior-publication overlap and any author-specific
   self-citations or disclosures also require human confirmation. No approval,
   organizer contact or submission is claimed.

## Scientific consistency checks

The automated claim mapping recomputes controlled means and harm counts,
checks independent-system counts and method coverage, verifies scaling
retention and convergence, checks wind-target aggregation and measured
contrasts, and verifies the shared bank and missing hatch edges. It also
checks references, anonymity strings, page limits and the abstract length.
These checks establish correspondence to the saved evidence, not correctness
of every causal assumption. Equations were read against the flow, fitting,
diagnostic, selection, mixture, audit and evaluation implementations.

The manuscript keeps important distinctions explicit:

- Fifteen independent five-node SCMs produce 60 principal conditions. Forty-five
  scaling/topology SCMs produce 90 adjusted-resource conditions. Repeated priors
  and budgets are not independent systems.
- The wind study has 699 primary measurements in five acquisition files on one
  apparatus, with only one hatch acquisition. The 3,399 non-test count includes
  one preprocessing-only row in addition to 3,398 retained modeling rows.
- Confidence intervals over acquired measurements condition on fitted models
  and fixed Monte Carlo streams. Grouped refit sensitivity and predictive
  intervals are different quantities. The 100-node ensemble difference is
  small and does not include variation over alternative Monte Carlo seeds.
- The graph heatmap averages repeated fan acquisitions. The response curves
  and numerical engineering examples use the prespecified individual files.
- The light case uses a reserved stronger polarizer regime on an already known
  apparatus. It remains exploratory. Its endpoint and timing convention differ
  from those of the wind study.
- Wind current is not power, relative pressure is not airflow, and microphone
  circuit voltage is not sound pressure level. The offline choices do not
  establish energy savings or an algorithmic operating advantage.

## Format, sources and remaining editorial information

The [official call](https://saiconference.com/Computing/CallforPapers) was
rechecked on 9 October 2026. The draft uses the official archived `svproc`
class and `spmpsci` bibliography style unchanged. The template's written font
instruction says Times New Roman, although its unmodified sample defaults to
Computer Modern. The font-only update on 11 October 2026 uses genuine Times New
Roman text through XeLaTeX and retains the NewTX mathematical fonts. The class's
original 10-point size, margins and line spacing are unchanged, and the previous
interword spacing settings are retained. No size or spacing reduction was used
to reach the page limit. Font provenance, embedding and visual checks are in
`FONT_VERIFICATION.md`.

There are six main figures, three main tables, eight equation groups, one
supplementary table and one component-graph figure. One appendix precedes references, following
the supplied template. The 205-word abstract and the final page counts are
recorded by `validation.json`. Rendered-page inspection notes are separate.
PDF author metadata is empty. No author, affiliation, acknowledgment, funding
statement or identifying project link appears in the paper.

Primary publication pages and full texts were checked for substantive background
claims. ABAPC-LLM is cited in its published UAI 2026 form. CauScientist and the
Qwen3 technical report are labeled preprints. The 21 bibliography entries are
all cited. Details and URLs are in `LITERATURE_CHECK.md`.

No identifying code-release link was inserted. An anonymized supplementary
package or later public release requires an author decision. The complete
experimental evidence already exists, but this draft does not pretend a
double-blind release has been deposited. The source and bibliography exceed
the remaining 7,693-byte cumulative Git allowance. They remain uncommitted,
as requested, with compiled/build artifacts in ignored storage.
