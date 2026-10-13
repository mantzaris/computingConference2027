# Publication figures and calibrated story assessment

Seven separate vector figures replace no previous artifact. The [compiled inclusion proof](example.pdf) places every figure and its caption in the actual `svproc` manuscript class. The [reassessment](../../experiments/simple_stories/REASSESSMENT.md) separates useful generated content, interface failures, incomplete encoding and substantive contradictions. No new generation was run.

| Figure | PDF | SVG | Model provenance |
|---|---|---|---|
| Humpty: attempted versus effective repair | [PDF](../../figures/publication/simple_stories/humpty.pdf) | [SVG](../../figures/publication/simple_stories/humpty.svg) | Frozen author reference |
| Wolf: warning, credibility and timely help | [PDF](../../figures/publication/simple_stories/wolf.pdf) | [SVG](../../figures/publication/simple_stories/wolf.svg) | Frozen author reference |
| Crow: raised water versus initial reach | [PDF](../../figures/publication/simple_stories/crow.pdf) | [SVG](../../figures/publication/simple_stories/crow.svg) | Frozen author reference |
| Blackwater: fuel, ignition and exposure (old 08) | [PDF](../../figures/publication/got/blackwater_mechanism.pdf) | [SVG](../../figures/publication/got/blackwater_mechanism.svg) | Unchanged Codex-assisted v4 hypothesis |
| Red Wedding: preparation and presence (old 11) | [PDF](../../figures/publication/got/red_wedding_mechanism.pdf) | [SVG](../../figures/publication/got/red_wedding_mechanism.svg) | Unchanged Codex-assisted v4 hypothesis |
| Bolton: mechanism and intervention sensitivity (old 14/15) | [PDF](../../figures/publication/got/bolton_mechanism_interventions.pdf) | [SVG](../../figures/publication/got/bolton_mechanism_interventions.svg) | Two unchanged Codex-assisted v4 scenarios |
| Astapor: purchase, attack and voluntary departure (old 16) | [PDF](../../figures/publication/got/astapor_overview.pdf) | [SVG](../../figures/publication/got/astapor_overview.svg) | Two unchanged Codex-assisted v4 scenarios |

**Recommended introduction: Crow.** Its distinct initial-reach route gives a compact reason that stones are not universally necessary. **Recommended Game of Thrones mechanism: Blackwater.** Six events distinguish the resource, actions and exposure converging on fleet fire losses. Bolton is a complementary methods figure: identical factual fit can conceal a different answer to a joint intervention. These recommendations concern explanatory specificity and presentation, not independently validated causal truth or measured reader comprehension.

## Typography, captions and insertion

The retained [class](../template/svproc.cls) sets `\textwidth=12.2cm` and `\textheight=19.3cm`; this is a single-column template, so a generic 85/178-mm target would be inappropriate here. Every figure is **122 mm wide**, with 9-point node/equation text and 8.5-point edge text at insertion size. Text is Times New Roman, with DejaVu Serif for the logical symbols unavailable in that font. The manuscript proof uses the existing Times-family `newtxtext/newtxmath` setup. PDFs embed every font and contain vectors; SVGs retain editable text and require the named fonts for identical display. Ghostscript subsets PDF fonts without rasterizing the artwork. Restrained grayscale styling uses a lightly shaded endpoint and, for Game of Thrones, dashed contextual versus solid explicit directional links. These statuses do not identify exact functions.

[captions.tex](captions.tex) contains a reusable manuscript caption for each figure. Each identifies author-reference versus assisted provenance, the scientific contrast, sources and assumptions. [example.tex](example.tex) is the minimal full inclusion example. For instance, after loading the captions and appropriate graphics path:

```tex
\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{simple_stories/crow.pdf}
  \caption{\CrowCaption}
  \label{fig:crow}
\end{figure}
```

Do not shrink these 122-mm exports to an 85-mm column: that would reduce 8.5-point type to approximately 5.9 points. The renderer accepts `--width-mm` for another venue and refuses layouts that do not fit at the fixed readable font sizes. A different-width manuscript needs its own inclusion check.

## Reproduction and verification

From `GoT-war/`, run:

```sh
python3 scripts/publication_figures.py --compile
```

This reads the frozen stories and archived generations; rebuilds the separate normalization/projection audit; validates displayed equation rewrites and exact edge selections; re-executes all 12 author-reference interventions and the six Bolton conditional answers; renders seven SVG/PDF pairs; compiles the actual-class example twice; checks embedded fonts and overfull boxes; and writes [verification.json](verification.json). It uses installed Python dependencies, Graphviz, Fontconfig/Times New Roman and DejaVu Serif, Ghostscript, Poppler and pdfLaTeX with newtx. No network, model service or GPU is required. PNG previews, DOT layouts and build logs remain under ignored `.private/publication_work/` or ignored TeX auxiliary paths. SVG/PDF dimensions, model identities, displayed edges, equations and file hashes are in the [figure manifest](../../figures/publication/manifest.json).

The assistant visually inspected all seven final vector exports through rendered previews at their intended 122-mm insertion width, and all seven compiled pages, checking captions, directions, signs, spacing, equations and clipping. Arrow-label padding was increased after inspecting the first drafts. Astapor was divided into two explicitly connected panels instead of shrinking the text: command variable C is repeated as a boundary, and every dependency appears exactly once. Bolton combines the original mechanism and scenario views. The proof has no overfull boxes; all PDF fonts are embedded. This inspection is not independent human review or a comprehension experiment.

Validation on this revision: **105 tests passed** (8.10 seconds), including seven new audit/publication tests; the existing quantified mutation checks remain intact. A clean export containing only publishable files reproduced the entire audit, all seven SVG/PDF pairs and the seven-page proof without private records. The diagnostic JSON matched exactly. All seven figure PDFs were checked for embedded fonts and absence of raster-image objects. Historical simple-story and v4 files remained unchanged. PDF container hashes can depend on tool/font versions; model identities, equations, dimensions and numerical answers are the reproducibility targets.

## Exact change ledger

| Artifact | Presentation/editorial change | Structural or substantive model change |
|---|---|---|
| Humpty, Wolf, Crow publication figures | Compact grayscale graphs; meaningful shortened labels; equations in mathematical notation; assumptions and sentence references moved to captions | **None.** The frozen author references, all factual values and all equations are unchanged; these are not corrected generator models |
| Blackwater | Re-layout of the same six-node, five-edge local mechanism from 08; shorter labels; compact joint equation | **None.** Fleet-loss slice, not an unqualified whole-battle model |
| Red Wedding | Same seven nodes and six edges as 11; “risk of betrayal” clarified to **Frey's risk in betraying Robb**, matching the retained process description; both plot-function alternatives shown | **No equation, endpoint or assumption change.** The label clarification is editorial disambiguation, not new supporting evidence |
| Bolton | Same seven-node/six-edge slice as 14; six answers from 15 in panel (b); scenario names become “Relief required” and “Untrapped advance” | **None.** Caption explicitly identifies the full-model equations used outside the local slice; no hidden edge is removed from the calculation |
| Astapor | All 11 variables and 12 edges from 16, partitioned into two panels; repeated C links them; both control-loss functions shown | **None.** Immediate departure remains the outcome; the graph does not claim lasting political control |
| Derived normalization audit | 28 unambiguous edge and 20 claim relocations; nine logged mechanism/root precedence resolutions | **Representation changes only in a derived view.** Original parent sets, facts, constraints and prose remain unchanged; seven ambiguous edge attachments remain unresolved |
| Balanced semantic assessment | Reclassifies incomplete encoding versus actual contradiction; treats abbreviated edge language in its joint context | **No corrected SCM created.** Substantive corrections are proposed and attributed, not applied or rescored |

The original strict compiler result remains 0/6; normalized strict acceptance is also 0/6. Nine controlled joint descriptions are compatible but not entailed by their partial encodings; two Wolf descriptions conflict with recorded observations. The row-only diagnostic projections are explicitly assisted audit views, not autonomous construction successes. Original direct-answer accuracy and every original score remain unchanged. Independent researcher adjudication remains pending for both the reassessment and the Game of Thrones interpretations.
