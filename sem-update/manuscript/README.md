# Anonymous first manuscript draft

The paper synthesizes the completed experimental evidence. No experiments are
launched by its build or validation commands. Human scientific review is pending.

- Complete LaTeX source: [main.tex](main.tex), including all sections, tables,
  appendix and the formatted bibliography. Edit the manuscript in this file.
- Optional citation metadata: [references.bib](references.bib). Compilation does
  not read this file or require BibTeX. Update the bibliography in `main.tex`
  when editing references.
- All eight figure PDFs: [figures/](figures/).
- Official conference template: `svproc.cls`, `aliascnt.sty` and `remreset.sty`,
  alongside `main.tex`. File origins and checksums are in [assets.json](assets.json).
- Compiled draft: [draft.pdf](draft.pdf), beside `main.tex`.
- Author review: [REVIEW_MEMO.md](REVIEW_MEMO.md).
- Implementation and claims: [EVIDENCE_MAP.md](EVIDENCE_MAP.md).
- Evidence mapping: [claim_evidence.json](../.artifacts/manuscript_draft/claim_evidence.json).
- Build and evidence checks: [validation.json](../.artifacts/manuscript_draft/validation.json).
- Page inspection: [visual_review.json](../.artifacts/manuscript_draft/visual_review.json).

## Compile the paper

Run from `sem-update/manuscript/`:

```bash
python3 build.py
```

`build.py` checks the bundled asset checksums and runs XeLaTeX three times. It needs
Python's standard library, `xelatex` and `pdftotext`. It reads no external
manuscript assets, experimental results or template archive. It writes `draft.pdf`
beside `main.tex`. Intermediate files, logs and caches stay in the local `build/`
directory. Both are ignored by Git. From the repository root, the equivalent
command is `python3 sem-update/manuscript/build.py`.

The manuscript folder is also portable. Copy `main.tex`, `figures/`, `svproc.cls`,
`aliascnt.sty` and `remreset.sty` together, then run the following from the copied
folder to produce `main.pdf`:

```bash
xelatex -halt-on-error main.tex
xelatex -halt-on-error main.tex
xelatex -halt-on-error main.tex
```

No custom `TEXINPUTS`, BibTeX step, separate section sources or files elsewhere
in the repository are required. Standard installed LaTeX packages and fonts
remain prerequisites, including `fontspec`, `newtxmath`, `xurl`, `hyperref`,
`amsmath`, `amssymb`, `graphicx`, `booktabs`, `array` and `multicol`. The tested
environment uses TeX Live 2019. No packages or data are downloaded by the build.

Main document text uses genuine Times New Roman regular, bold, italic and bold
italic faces from the existing system installation. A legitimate Times New Roman
installation is required on any machine compiling this source; no substitute
font is configured. This machine provides the faces through
`ttf-mscorefonts-installer` under `/usr/share/fonts/truetype/msttcorefonts/`.
`newtxmath` retains the existing mathematical symbols, alphabets and upright
operators, including its TeX Gyre Termes math fonts. Existing figure fonts are
unchanged. The compiler no longer loads `newtxtext` for document text. Its
existing interword spacing and sentence spacing are retained explicitly, along
with the unchanged template dimensions and line spacing. See
[FONT_VERIFICATION.md](FONT_VERIFICATION.md) for the font audit and page counts.

## Reproduce figures and check evidence

These optional commands use the existing repository evidence and artifact
storage. They are not required to compile the portable manuscript:

```bash
python3 sem-update/manuscript/build.py --refresh-figures
python3 sem-update/manuscript/validate.py
mkdir -p sem-update/.artifacts/manuscript_draft/pages
pdftoppm -r 140 -png sem-update/manuscript/draft.pdf sem-update/.artifacts/manuscript_draft/pages/page
```

Refreshing recomposes five figures and three table bodies from compact results,
copies the eight final PDFs into `figures/`, and updates their checksums. The
three existing process/component graphs are copied unchanged from their
preserved sources. The table bodies are embedded in `main.tex`; validation
checks them against the evidence tables. The bibliography is embedded using
the previously verified output of the official `spmpsci` style.

Evidence reproduction uses Python 3.8, NumPy 1.22.1, pandas 1.3.4 and
Matplotlib 3.1.2. Validation also needs `pdfinfo`, and rendering needs `pdftoppm`.
Source hashes for plotting inputs are recorded in
`../.artifacts/manuscript_draft/figure_inputs.json`. Full PDF/SVG/PNG variants,
rendered pages and numerical editorial evidence remain in that ignored
artifact directory. Original assets and historical results are preserved.

The official template is linked from the
[conference call](https://saiconference.com/Computing/CallforPapers). The bundled
class and supporting styles are unchanged copies from the archive with SHA-256
`d5ed3f489b336450dd98e4f33844c44e842a6d022f84b0ef868dc19dcf84abc8`.
The previous split sources are preserved under
`../.artifacts/manuscript_draft/before_single_tex/`, and the source state before
local asset packaging is under `../.artifacts/manuscript_draft/before_local_assets/`.

## Scope and preservation

The principal controlled comparison, scaling tests, light-tunnel polarizer case
and wind-tunnel intervention application have separate endpoints and units.
The paper preserves adverse findings and distinguishes the executed DCDI
adaptation from converged native DCDI. Historical experimental reports and
results are unchanged.

Nothing was staged, committed or pushed. The existing cumulative unique-blob
usage is 26,206,707 bytes against 26,214,400 bytes, leaving 7,693 bytes. Even the
manuscript text and bibliography exceed that remainder. This draft intentionally
remains available as untracked source and ignored build artifacts. It requires a
separate repository-budget decision before any future commit. No evidence was
deleted and no history was rewritten. Exact incremental sizes are in
`../.artifacts/manuscript_draft/source_sizes.json`. The final PDF hash is in
`validation.json`; the independent Git audit is in
`.artifacts/manuscript_draft/repository_check.json`.
