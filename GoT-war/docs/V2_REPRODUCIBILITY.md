# Reproduce version 2 without inference

Version 1 remains under the original `results/`, `paper/`, and reproduction archive. Its instructions and measured results are preserved. The new experiment uses `configs/budget_v2.json`, `configs/v2_frozen_protocol.json`, `results/v2/`, `figures/v2/`, and `paper/v2/`.

From `GoT-war`:

```sh
python3 scripts/v2_reproduction.py
PYTHONPATH=src python3 -m got_war.v2.analysis --split test
PYTHONPATH=src python3 scripts/v2_verify.py
python3 scripts/v2_resources.py
PYTHONPATH=src python3 -c 'from got_war.v2.reporting import benchmark_reports, manuscript_tables; benchmark_reports("."); manuscript_tables(".")'
PYTHONPATH=src python3 scripts/v2_error_analysis.py
PYTHONPATH=src python3 -m got_war.v2.figures
```

The archive validator checks every member and hash before restoring only missing files into ignored paths. It refuses to overwrite different existing records. The archive retains every fixed controlled record, including failed synthesis, selected development records, accepted application models and numerical/provenance inputs. Full prompts, transcript context and the larger development failure trail remain in the original ignored run/private folders. They are not redistributed as a copyrighted source corpus.

`analysis` regenerates component tables, paired SCM bootstrap intervals and the compact SCM scores. `v2_verify.py` re-executes accepted equations, compatible families and exact coalition games and checks the frozen hashes. Mathematical consistency is not source validation. Public application audit tables and source links can be regenerated without full transcripts only from their published artifacts; regenerating the private contextual review HTML requires the original `.private/v2/five_kings_packet.json` or a matching-hash lawful reacquisition. Numerical verification and figures do not need private source text.

The commands above work on a release-only checkout. The additional `PYTHONPATH=src python3 -m got_war.v2.reporting` command regenerates application review artifacts and therefore requires the private packet. The published application audit remains available without it. No absent private packet is counted as a passing source audit.

Compile twice from `paper/v2` with `TEXINPUTS=.:../template: pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex`. Graphviz `dot`, the logged Python dependencies and the retained template files are needed. PNG previews and LaTeX build intermediates stay ignored. Visual inspection is recorded separately from figure generation and is not a reader study.

The campaign is complete only when its completion marker and accounting are written. Its deadline cannot be extended by restoring files. New inference requires a separately authorized campaign; offline reproduction does not. The remote SSH configuration is private and is never included in the release. Resource figures distinguish response-reported tokens, cumulative server tokens, overlapping request durations, approximate utilization-weighted GPU hours and unknown billing cost.

For updates, stage only the intended release files, run `python3 scripts/check_release.py --write-manifest`, stage `results/artifact_manifest.json`, then run `python3 scripts/check_release.py` before committing to `main`. The limits remain 250 files, 8 MiB total and 2 MiB per file. Do not push automatically.

Maintainers can run `python3 scripts/v2_reproduction.py --validate-release` after staging the final archive and manuscript. It exports the staged project into an isolated directory under `.cache`, restores its curated records twice, re-executes the numerical analyses and tests, regenerates reports/figures, and compiles the manuscript twice. It compares stable outputs byte-for-byte; PDF metadata timestamps are not a numerical reproducibility criterion. It does not access the original private transcript packet and cannot certify source entailment.

The original fixed run was launched remotely with `PYTHONPATH=src .venv/bin/python scripts/v2_launch_benchmark.py`; the package was not installed into that isolated environment. A first launch without that source path exited before inference and remains in the logs. Auxiliary development/calibration summary tables regenerate locally and stay ignored; their full fixed records remain in the curated archive.
