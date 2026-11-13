# Final GoT-war conference paper

**[Open the complete paper: GoT-war_final_paper.pdf](GoT-war_final_paper.pdf)**

Title: *Explaining Narrative Events with Generative AI and Structural Causal Models*.
The anonymous manuscript has 22 pages: 16 main-text pages, two reference pages
and four appendix pages.

This is the final manuscript folder, formerly `paper/narrative_maps_2027/`.
It contains the [editable source](manuscript.tex), bibliography, seven figure
PDFs and conference class files. The figure PDFs are individual illustrations;
`GoT-war_final_paper.pdf` is the complete paper.

From the repository root, compile and verify it with:

```bash
python3 GoT-war/scripts/build_narrative_paper.py
```

The build writes `GoT-war_final_paper.pdf` here and updates
[verification.json](verification.json). It checks the preserved scientific
results, citations, figures, fonts, page counts and isolated compilation.
It uses existing results and runs no new inference. Temporary compiler output
stays in the ignored `GoT-war/.private/narrative_maps_2027/` directory.

See [EDITORIAL.md](EDITORIAL.md) for the manuscript's review history and
standalone compilation instructions. Earlier papers remain in `paper/` and
`paper/v2/` as historical versions.
