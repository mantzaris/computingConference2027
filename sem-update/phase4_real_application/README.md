# Wind-tunnel application

This study uses recorded Causal Chambers fan/hatch experiments to test prediction
of current and pressure changes on one physical apparatus. It preserves the
completed studies at `ad21e60`, `8c452ac` and `a17a8f7`. Start with the
[evidence report](docs/evidence_report.md), [interpretation](docs/interpretation.md),
[data audit](docs/data_audit.md) and [variable dictionary](docs/variables.md).
Human scientific review is pending; no equipment was operated and nothing was
submitted or pushed.

The capped DCDI comparator had the lowest observed primary error (0.2199);
fixed flows offered a useful moderate-cost compromise (0.3602; 29.44 seconds).
M3 scored 0.3310 and missed a measured hatch effect. The LLM prior worsened every
matched primary comparison. These are descriptive results from one apparatus.

The primary panel has 699 measured observations in five randomized acquisition
files, three actuator targets, and a ten-second response horizon. Eleven modeled
variables describe commands, fan speeds, calibrated currents and pressures.
Microphone-circuit changes are measured separately because training/test sensor
configurations are incompatible. Pressure is not airflow, current is not power,
and microphone voltage is not calibrated dB SPL.

All six methods, fixed-G0 flows and random repair use identical eligible records.
M0 is the empirical-marginal control; M1 is ridge Gaussian SEM; M2 is DCDI with
common flows; M3 is disturbance-guided repair; M4 is robust selection; M5 is the
anchored predictive ensemble. Marginal-control density likelihood is unavailable.
M2 is the existing capped/projected DCDI-DSF adaptation with common-flow refitting;
M3–M5 share a frozen candidate bank. Five grouped fitting-file resamples and one
actual Qwen3-8B semantic initialization are separate sensitivity comparisons.
See [protocol](docs/protocol.md), [frozen protocol](results/protocol.json),
[splits](results/split_manifest.json), [claims](results/claim_ledger.json) and
[decisions](docs/decisions.md). Acquisitions and repeated fits are not independent
apparatuses. No test outcomes or reference adjacency enter learning or prompts.

## Reproduction and resume

Commands below run from `sem-update/` on the existing CUDA environment. The
unchanged [dependency lock](../requirements.lock) records exact package versions;
the evidence archive also records the executed environment, sources and model
revisions. A fresh run needs the pinned public Qwen3-8B weights and DCDI source
used by the previous phases. Do not reset or replace the cumulative ledger.

```bash
cd sem-update
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase4_real_application"
export PYTHONPATH="src:phase4_real_application/tools"
PYTHON=.artifacts/venv/bin/python
$PYTHON phase4_real_application/tools/acquire.py
$PYTHON phase4_real_application/tools/audit_data.py
$PYTHON phase4_real_application/tools/application.py doctor
$PYTHON phase4_real_application/tools/application.py development
$PYTHON phase4_real_application/tools/application.py llm
$PYTHON phase4_real_application/tools/application.py test
$PYTHON phase4_real_application/tools/application.py freeze
$PYTHON -u phase4_real_application/tools/application.py run
$PYTHON -u phase4_real_application/tools/finish.py
```

Completed fit stages resume from their ledger/cache records. `finish.py` waits
for sealed selections, verifies every checkpoint, evaluates the reserved
observations, and produces reports/figures. After completion use the following
checks rather than launch duplicate fits. A scientific source mismatch stops
resume; it is not bypassed. Full logs and any failed attempts stay in artifacts.

```bash
$PYTHON phase4_real_application/tools/application.py status
$PYTHON phase4_real_application/tools/audit_execution.py
CUDA_VISIBLE_DEVICES= $PYTHON phase4_real_application/tools/render_figures.py
CUDA_VISIBLE_DEVICES= $PYTHON phase4_real_application/tools/check_plot_reproduction.py
CUDA_VISIBLE_DEVICES= $PYTHON phase4_real_application/tools/summarize.py
CUDA_VISIBLE_DEVICES= $PYTHON phase4_real_application/tools/engineering_checks.py
```

The figure renderer needs only committed plotting tables, graph JSON and
configuration. Its clean-directory check requires no raw observations,
checkpoints or CUDA. `--prepare` regenerates those tables from preserved full
precision evidence; routine figure reproduction should omit it. The official
Springer class layout check runs locally with TeX Live:

```bash
python3 phase4_real_application/tools/check_template.py
```

This uses the official conference template previously downloaded under
`.artifacts/data/raw/venue/`; the attempted fresh download returned HTTP 403.
See [venue check](docs/venue.md) and [figure captions](docs/figure_captions.md).

## Evidence and repository size

Full records, fitting arrays, checkpoints, generated observations, logs,
bootstrap draws and PDF/SVG/PNG graphics belong in the ignored artifact root.
Only curated compact outputs belong in Git. [Artifact preservation](docs/artifacts.md)
identifies the durable copy, checksums, excluded reproducible caches and exact
restore/verification commands. The Pod filesystem alone is not a verified
persistent copy. Prior evidence is retained unchanged.

The cumulative new-blob allowance is 25 MiB, with 5 MiB per file. This phase
started at 24.602955 MiB, leaving 416,332 bytes; accounting includes all earlier
committed blob versions. Inspect explicitly staged files with:

```bash
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

The current completion, validation, compute and size records are in
[status](docs/status.md). Preserve evidence before any separately authorized Pod
termination. Do not push, create another branch or operate physical equipment.

The two PDFs selected for Git are the main process graph and accuracy/cost
comparison. Both response figures, the effect heatmap, recorded tradeoff and
ensemble-component figures remain in the verified archive with every SVG/PNG
variant. All plotting inputs and rendering code are committed. `tools/curate.py`
preserves full-precision originals, losslessly compacts graph JSON, and rounds
curated CSV numbers to ten significant digits. Detailed semantic/refit/checkpoint
records remain in ignored evidence; compact summaries retain their coverage.
