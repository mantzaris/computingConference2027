# Times New Roman verification

Verified on 11 October 2026. The updated source is `main.tex` and the compiled
paper is `draft.pdf` in this directory. Run `python3 build.py` here to compile
with XeLaTeX, or run `xelatex -halt-on-error main.tex` three times for `main.pdf`.

The existing system installation provides genuine Times New Roman version 2.82
through `ttf-mscorefonts-installer` 3.7ubuntu6. Regular, bold, italic and bold
italic files are under `/usr/share/fonts/truetype/msttcorefonts/`. Their internal
family names, Monotype copyright metadata, PostScript names and checksums were
checked. No font was downloaded, substituted or copied into the manuscript.

`fontspec` selects all four faces explicitly with its `no-math` option. The
compiler no longer loads `newtxtext`. The existing NewTX mathematical fonts,
sans-serif mathematical alphabet and monospaced code font remain in use.
The previous interword spacing of 0.25 em, stretch of 0.2 em, shrink of 0.1 em
and sentence-space increment of approximately 0.111 em are retained. Measured
body and small-text baselines remain 12 pt and 11 pt. The official class files,
text dimensions, margins, font sizes and document spacing commands are unchanged.

`pdffonts draft.pdf` confirms embedded Times New Roman regular, bold and italic
faces. The manuscript does not use bold italic text; a separate specimen using
the same preamble confirms that the genuine bold italic face also embeds.
All fonts in the paper are embedded.

| PDF font family | Use |
| --- | --- |
| TimesNewRomanPSMT, TimesNewRomanPS-BoldMT, TimesNewRomanPS-ItalicMT | Document text, title, headings, captions, tables and references |
| NewTXMI and related symbol fonts, TeXGyreTermes-Regular/Bold | Retained mathematics, including upright operators and numbers in math mode |
| TeXGyreHeros-Regular, t1xtt | Retained sans-serif mathematical alphabet and monospaced code |
| DejaVuSans, DejaVuSans-Oblique | Existing figure PDFs, unchanged |

TeX Gyre Termes is no longer the document text font. Its remaining uses were
checked in extracted PDF text runs and belong to the preserved mathematics.
All eight figure PDFs and the three bundled template files retain their previous
SHA-256 checksums. All source bytes from `\begin{document}` onward, including
wording, equations, tables, citations and figure commands, are unchanged.

The final PDF has **18 main-text pages and six additional pages**: appendix
pages 19-22 and references on pages 23-24. This meets the 18-page main-text and
seven-page combined appendix/reference limits without compression or editing.
All 24 pages were rendered at 140 dpi and inspected, including title, headings,
body, captions, tables, references and mathematical expressions. No missing
symbols, clipping, overlapping content, font substitutions, undefined citations
or overfull boxes were found. Three underfull vertical-box notices remain from
normal template page composition. The existing evidence validator passes.
Anonymous authorship and absence of identifying PDF author metadata are preserved.

Detailed evidence is in the local ignored `build/times_new_roman/` directory:
font provenance, font lists for the paper and individual figures, the four-face
specimen, spacing measurements, source-preservation checks, rendered pages and
`verification.json`. The previous source and PDF are preserved in its `before/`
subdirectory. No commit, push or submission was performed.
