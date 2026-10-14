# Manuscript revision and verification, 14 October 2026

The [anonymous paper](manuscript.pdf) and [editable LaTeX source](manuscript.tex) revise reviewed commit `955023a`. The paper contains 15 main-text pages, one reference page and four appendix pages, with a 204-word abstract. The seven publication figures, their short captions, the bibliography and all experimental records are unchanged. No inference campaign, new experiment, push or submission was performed.

## Substantive changes

The introduction now explains what readers can do: trace a passage-based interpretation, inspect how conditions combine, and find the assumption behind a hypothetical answer. Related work distinguishes executable joint mechanisms from event links and character networks without claiming that graphs or SCMs are new. The application discussions lead with the distinctions revealed by Blackwater, the Red Wedding, Winterfell and Astapor. The partial-family account now explicitly separates conservative, incomplete encoding from uncertainty necessarily present in the source. Useful short-story concepts receive credit while the Wolf factual error and historical 0/6 acceptance remain visible.

Section 4.5 traces Blackwater through actual source passages, proposals, refinement, equations and execution. The original source passes are `runs/application_v4_20261013/qwen/blackwater/pass_00.json` (wildfire control) and `pass_01.json` (the erroneous Tyrion-arrow attribution). Their content hashes match the curated archive. The correction history is in the Blackwater generation record in `results/v4/reproduction.json.xz`. The locators are the source site's own scene/line IDs: S02E05/S15 and S02E09/S14, S15L1, S16, S19 and S21. The build verifies their archived identity where the private corpus is available. Re-executing the existing ignition question gives local fleet damage 0 and assault repelled 1 in both complete scenarios. This is a documented assistant refinement, not an invented first-generation success.

Section 5.3 adds the benchmark comparison table, explicitly distinguishing the 72-SCM identified stratum from the 40-SCM changing stratum. `benchmark_values.tex` is generated from unrounded archived estimates. The build independently recomputes the means and paired difference from `results/v2/test_scm_scores.csv`: the gain is 21.0373459147969 percentage points, displayed as 21.0, with the archived 95% interval of 9.6 to 32.8. Sixteen failed syntheses remain in the primary denominator. The table makes carry-forward's 86.2% overall and 0% changing accuracy visible. No gain is attributed to source weighting or presentation.

The manuscript contains no temporary status, editorial instructions, pending-review wording or claim of completed independent adjudication. Preparation assistance is confined to the dedicated AI declaration. The actual research-generation roles remain in the methodology.

## Reproduction and inspection

This folder is self-contained for local LaTeX compilation: the seven figure PDFs and the official `svproc.cls`, `aliascnt.sty` and `remreset.sty` are beside `manuscript.tex`. They are byte-for-byte copies of the original publication assets; only the figure paths in the manuscript changed. With a LaTeX distribution containing the `newtx` fonts and the standard packages listed in the preamble, run from this folder:

```sh
pdflatex manuscript.tex
bibtex manuscript
pdflatex manuscript.tex
pdflatex manuscript.tex
```

The full repository audit below additionally compiles an isolated copy of these fourteen source/asset files with project search paths removed, checks that no other repository input is read, and compares its rendered text with the normal build. Its portability record includes hashes of all fourteen files. All 20 pages also render identically to the pre-portability PDF at 120 dpi, and extracted text is identical. No source content, equations, captions or figure artwork changed for this portability update.

From `GoT-war/`:

```sh
python3 scripts/build_narrative_paper.py
```

The build uses the official retained `svproc` class, its 122 mm text width, pdfLaTeX/BibTeX, Ghostscript and Poppler. It writes only the current manuscript outputs and ignored build products. [verification.json](verification.json) records input hashes, numerical checks, equation comparisons, existing query re-execution, seven figure hashes, embedded fonts, anonymity, references, page limits and caption lengths. The benchmark table is regenerated from the archive, not entered by subtracting rounded percentages. Private transcripts and full generation streams remain local.

The final 20-page PDF was inspected page by page at 120 dpi with figures at their actual 122 mm insertion width. The Crow intervention paragraph stays together; the Bolton calculation is not split by its figure; the Astapor float is cleared before the discussion. Appendix table headings are separated onto two lines. All seven figure captions occupy two lines, fonts are embedded, references resolve, and no overfull boxes, cropped labels or identifying author/repository metadata were found. The images and equations have not been restyled or semantically revised. This is assistant editorial inspection, not a human comprehension evaluation.

The official [conference page](https://saiconference.com/Computing) and [author instructions](https://saiconference.com/Computing/CallforPapers) were rechecked on 14 October 2026: anonymous review, 150-250 abstract words, 18 main pages plus seven reference/appendix pages, concise captions and an AI declaration. The template origin is recorded in [SOURCE.json](../template/SOURCE.json). The sharpened comparisons were checked against the primary [Li et al. paper](https://aclanthology.org/2025.wnu-1.10.pdf), [Koupaee et al. publication](https://aclanthology.org/2025.acl-long.1269/), [Bynum and Cho publication](https://aclanthology.org/2025.emnlp-main.107/) and [PAL publication](https://proceedings.mlr.press/v202/gao23f.html). The nine existing references remain unchanged and are all cited in the main text.

## Decisions for author editing

The principal scientific decision remains endorsement or revision of the case interpretations, distinguishing event evidence, directional support and functional assumptions; the existing independent-review packet remains unadjudicated. An anonymous artifact URL is optional and has not been invented. Crow remains the clearest introductory figure; Blackwater and Bolton offer complementary application views. The venue's human authorship and responsibility requirements remain the authors' responsibility, as stated in the paper's declaration. No submission approval or independent human review is claimed.
