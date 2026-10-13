# Conference draft: editorial and verification note

Open [the anonymous review PDF](manuscript.pdf). The complete [LaTeX source](manuscript.tex), [bibliography](references.bib), [short captions](captions.tex), and [machine-readable verification](verification.json) form a separate draft. Earlier manuscripts, experiments, generation records, reassessment and publication figures are preserved byte-for-byte. No inference, push or submission was performed for this draft.

The central argument is an integrated method for connecting narrative interpretation to readable mechanisms and executable scenario comparison. Crow introduces context-dependent reachability; the six-case television application is the main contribution. Blackwater distinguishes possession from use, the Red Wedding separates preparation and attendance, Bolton locates the assumption behind a changed answer, and Astapor separates command, force and voluntary service. Humpty and Wolf are appendix reference examples. The older controlled benchmark supports execution over explicit rules; it does not evaluate these final application models or establish a benefit from presentation/source weighting. Factual carry-forward's high overall accuracy and zero changing-outcome accuracy are both retained for perspective.

## Build and format

From `GoT-war/`:

```sh
python3 scripts/build_narrative_paper.py
```

Use the existing Python project dependencies, pdfLaTeX/BibTeX, `newtxtext`/`newtxmath`, Ghostscript and Poppler. The command uses the retained official `svproc.cls`, a 122 mm text width and unchanged 122 mm publication figures; it creates no model-service requests. Intermediate TeX files, the raw PDF, extracted text and inspection previews stay in `.private/narrative_maps_2027/`. Standard BibTeX `plain` supplies numbered alphabetical references within the actual class. The bibliography contains verified DOI metadata where available. The build checks page limits, abstract/caption lengths, references, anonymity fields, font embedding, figure identity and selected numerical/equation transcriptions against the retained artifacts. It also re-executes the archived application queries and reference-story interventions. PDF timestamps can differ between builds; the scientific inputs and figure hashes are recorded.

The official [Computing Conference page](https://saiconference.com/Computing) and [author instructions](https://saiconference.com/Computing/CallforPapers) were checked on 2026-10-13. They specify anonymous double-blind review, a 150–250-word abstract, at most 18 main-text pages and seven additional pages for references/appendices, and short captions ideally no longer than two lines. The retained template comes from the official [conference LaTeX download](https://saiconference.com/Downloads/SAI_Paper_Format_Latex_Conference.zip), with acquisition metadata in [SOURCE.json](../template/SOURCE.json).

The delivered draft has a 207-word abstract, 14 main-text pages, one reference page and four appendix pages. Its seven figure captions are 18–19 words and occupy two lines or fewer. Main figures are Crow, Blackwater, Red Wedding, combined Bolton mechanism/interventions, and Astapor; appendix figures are Humpty and Wolf. All are vectors with embedded fonts and retain the 8.5–9 pt publication labels. Figures and equations are unchanged; only new short captions and manuscript prose were written. The `Author`, `Creator`, affiliation and acknowledgment fields are empty; no identifying project/repository URL appears in the review PDF. The live public repository remains internal provenance, not an anonymous artifact link.

## Evidence and reference audit

| Manuscript claim | Retained basis / check |
|---|---|
| Six cases, 69 variable records, 71 relationships, 41 episode pages, 924 containers | `results/v4/reproduction.json.xz`; counts checked by the new build script |
| 18 selected questions; six scenario disagreements; all broad sets `{0,1}` | All 18 partial and 36 conditional query results reproduced with the existing solver |
| Four application figures' equations and alternatives | Expression transcriptions compared with retained scenario dictionaries; every publication PDF matched its existing manifest hash |
| Crow, Humpty and Wolf equations / worked interventions | Compared with `experiments/simple_stories/frozen.json`; all 12 original reference questions and the six manuscript contrasts re-executed |
| Simple-story acceptance, direct answers, factual assertion counts, resources | Archived `records.json.xz` and `reassessment.json`; original results preserved |
| Prose-rule assessments, nine compatible descriptions and two conflicts | `experiments/simple_stories/REASSESSMENT.md` and its retained audit; semantic judgments remain assistant assessments |
| 77.8% versus 56.7%; +21.0 pp [9.6, 32.8]; 16 failed syntheses; changing-outcome strata | `results/v2/test_summary.json`; paired model-level bootstrap and primary denominators checked, with no test inference or retuning |
| Benchmark split and question count | `configs/v2_frozen_protocol.json` and `results/v2/RESULTS.md`: 120 generating models, 24/24/72 split, 1,080 held-out questions |
| Inference resources | Retained application and story usage records; request duration separated from service residency; Codex build/tokens unavailable |

The source-location replay additionally verified 74 retained quote locations against the private corpus using `python3 scripts/v4_reproduce.py --source-check`. This establishes stable passage identity, not independent source entailment. Twenty-two relevant existing tests passed (`test_simple_stories.py`, `test_story_reassessment.py`), including quantified contradiction checks and publication/model agreement. These checks do not replace scientific adjudication.

Primary publication pages/PDFs were checked for authors, title, year, venue, pages and the claims actually cited:

- Pearl (2009), *Causal inference in statistics: An overview*: [author-hosted published PDF](https://ftp.cs.ucla.edu/pub/stat_ser/SS-2009-57-Sup.pdf), DOI 10.1214/09-SS057. The publisher HTML was not readable through the available browser; the PDF supplies the journal metadata and SCM formulation.
- Chambers and Jurafsky (2008), narrative event chains: [ACL paper](https://aclanthology.org/P08-1090.pdf), pp. 789–797.
- Elson, Dames and McKeown (2010), literary dialogue networks: [ACL paper](https://aclanthology.org/P10-1015.pdf), pp. 138–147. Middle initials follow the paper itself.
- Bosselut et al. (2019), COMET: [ACL publication](https://aclanthology.org/P19-1470/), pp. 4762–4779.
- Gao et al. (2023), PAL: [PMLR publication](https://proceedings.mlr.press/v202/gao23f.html), volume 202, pp. 10764–10799.
- Li, Pan and Pi (2025), narrative causal graphs: [published ACL paper](https://aclanthology.org/2025.wnu-1.10.pdf), pp. 36–51. The bibliography uses the published workshop paper, corresponding to the requested [arXiv record](https://arxiv.org/abs/2504.07459); the colon in the title follows the PDF.
- Koupaee et al. (2025), semantic relation experts: [ACL publication](https://aclanthology.org/2025.acl-long.1269/), pp. 26169–26199.
- Bynum and Cho (2025), language-model-defined mechanisms: [EMNLP publication](https://aclanthology.org/2025.emnlp-main.107/), pp. 2096–2115.
- [ScreenScripts television collection](https://screenscripts.com/game-of-thrones/): the actual source family used, explicitly identified as dependent transcription material. Episode references and case limits were checked against the retained passage/model records. The HBO series page returned HTTP 403; no claim of fresh direct episode viewing or official transcript verification is made.

All nine references are cited in the main text. No unsupported priority claim is made. No citations to unrelated SEM-update experiments are imported.

## Editorial inspection

The complete compiled PDF was read and rendered for page-by-page inspection at 110–120 dpi, with the seven figures held at their actual 122 mm insertion width. Revisions shortened an overflowing line, corrected the case table's justification and episode wrapping, placed figures after their introducing text, kept each toy appendix together, and removed a two-line spill of the AI declaration onto an otherwise empty page. Captions were moved from the old explanatory paragraphs to concise identifiers; interpretation, source episodes and assumptions now appear in the body. Final inspection checked figure arrows and equations, mathematical negation/conjunction/disjunction, heading/page breaks, bibliography, table readability and caption length. This is assistant editorial inspection, not a human comprehension study.

## Decisions for the authors

1. Review the literary interpretations item by item using the existing v4 review packet: endpoint/event support, causal direction and functional assumptions are separate judgments. The paper retains the pending status in one consolidated discussion passage.
2. Confirm the methodological/application framing and the four detailed GoT views. Blackwater is the clearest compact mechanism; Bolton is its strongest complement for assumption-sensitive comparison. Crow is the best introductory example. No figure is represented as an untouched autonomous-generation success.
3. Arrange an appropriately anonymous artifact package/link if one is to accompany submission. None exists in this draft, and no anonymous URL has been invented. Review availability and permitted distribution of the source material; full transcripts remain local.
4. Perform substantive author review and revision of the manuscript and its scientific claims before submission. The conference's AI policy requires human responsibility for ideas, arguments, results and conclusions; its required declaration is included once before the references. No human approval is claimed here.

The current draft is a complete, compiled conference manuscript for that review. The unrun v3 comparison, historical synthesis failures and all original results remain preserved in their separate records.
