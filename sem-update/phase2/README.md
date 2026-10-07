# Phase two: six-method intervention prediction comparison

Separate follow-up to the completed study at `ad21e60`. Start with
[execution status](docs/status.md), [protocol](docs/protocol.md),
[decisions](docs/decisions.md), and [novelty scope](docs/novelty.md).
The completed [evidence report](docs/evidence_report.md) and
[interpretation](docs/interpretation.md) report actual outcomes, including
negative findings. Scientific review by Alex remains pending.
Historical results, including negative findings, remain under the parent study.
`results/historical_verification.json` recomputes the earlier headline counts,
errors, harm counts and compute total from the preserved metrics and ledger.
The [artifact recovery guide](docs/artifacts.md) distinguishes the Git deliverable
from the separately preserved experimental evidence.

| ID | Method |
| --- | --- |
| M0 | Independent empirical marginals; no continuous-density likelihood |
| M1 | Linear Gaussian ridge SEM on the supplied G0; development-selected alpha 0.1 |
| M2 | Official DCDI-DSF density and CUDA discovery adapter, followed by common flows |
| M3 | Current disturbance-guided bank with the disclosed average-calibration selection refinement |
| M4 | The same bank, mean/worst-environment selection with rho 0.5 |
| M5 | The same bank, an at-most-three-component predictive mixture anchored to G0 with tau 0.01 |

Fixed-G0 flows, random repair, rho=0, tau=0, uniform mixtures and a functioning
local LLM-edit adaptation are separate controls. M3 is not an exact rerun of the
historical 0.09927 result. Mixture weights do not express causal graph truth.

All 78 settings were executed: 60 controlled settings from 15 fresh independent
SCMs, 15 semantic settings from five more SCMs, and three metadata variants of
one real case. There are 468 six-method conditions, 2390 selected records with
controls/checkpoints, and 5642 endpoint/stage metric rows. These are not 2390
independent systems. Additional device use was **5.774939 hours** on the existing
RTX PRO 4500, within the 16-hour cap; cumulative use is 16.093464 hours.

| Method | Controlled mean T2 SW1 | Harmful repairs / 60 |
| --- | ---: | ---: |
| M0 | 0.32501 | N/A |
| M1 | 0.19396 | N/A |
| M2 | 0.27225 | N/A |
| M3 | 0.10617 | 8 |
| M4 | 0.11755 | 7 |
| M5 | 0.13018 | 1 |

M3 has the best controlled average, including Holm-corrected paired differences
against the other five main methods. M5 has the lowest observed repair harm and
the lowest observed semantic error; M1 is best on the new polarizer regime.
The semantic ranking remains uncertain with five SCMs. RGB is exploratory and
the real case is one familiar apparatus. M2 converged strictly on 35/36 dataset
fits (29/30 controlled); capped fits and projection are separately reported.
The corrected local LLM comparator generated 122 valid new edits and accepted
25 search moves. None of these results establishes causal graph truth.

Commands below run from `sem-update/` on the existing CUDA machine, using the
unchanged `requirements.lock` and `.artifacts/venv` environment. The first block
records the already completed preparation sequence. It is not a resume recipe:
do not rerun `development` or `freeze` over an existing frozen study, because
development writes its preparatory configuration. Preserve the final configuration
and the authoritative frozen `results/protocol.json`.

```bash
export PYTHONPATH=src
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase2"
.artifacts/venv/bin/python -m sem_update.phase2.runner doctor
.artifacts/venv/bin/python -m sem_update.phase2.runner test
.artifacts/venv/bin/python -m sem_update.phase2.runner development
.artifacts/venv/bin/python -m sem_update.phase2.runner pilots
.artifacts/venv/bin/python -m sem_update.phase2.runner llm-check
```

The doctor, 40 correctness tests, development selection, both timed pilots,
actual local LLM check, main experiments and final evaluation completed on the
RTX PRO 4500. The protocol, splits and selections are frozen. The following
commands are the executed main sequence; `freeze` is historical preparation,
not a command to replace the existing protocol:

```bash
.artifacts/venv/bin/python -m sem_update.phase2.runner freeze
.artifacts/venv/bin/python -m sem_update.phase2.runner run
.artifacts/venv/bin/python -m sem_update.phase2.runner evaluate
.artifacts/venv/bin/python -m sem_update.phase2.runner report
.artifacts/venv/bin/python phase2/tools/status.py
```

Jobs resume from atomic checkpoints and a cumulative SQLite ledger; completed
compatible jobs are reused, incompatible resumes fail, and retries are bounded.
The new artifact root contains a copy of the historical ledger plus phase-two
jobs. It reuses the historical pinned local Qwen weights and DCDI source. It
does not reset the 16-hour additional runtime cap or modify old evidence.
Do not launch a second coordinator while the recorded owner is alive. The tested
status tool reads the ledger without creating a GPU job or modifying selections.

Validation also passed five CPU statistical tests, two archive-integrity tests,
the development aggregation checks, all 36 input manifests, all 78 selections,
and all 596 final prediction archives. Nine final figures are supplied as
PDF/SVG with PNG previews, with two LaTeX tables. The figures/tables reproduce
from curated files with CUDA hidden and compile locally in the official template
without layout warnings. The Pod lacks pdflatex; the actual layout check used
the local TeX Live installation.

```bash
.artifacts/venv/bin/python phase2/tools/verify_history.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python -m pytest -q phase2/tests/test_reporting.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python phase2/tools/development_report_check.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python phase2/tools/audit_frozen_inputs.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python phase2/tools/audit_selected_models.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python phase2/tools/audit_final_predictions.py
CUDA_VISIBLE_DEVICES="" PYTHONPATH=src .artifacts/venv/bin/python phase2/tools/check_plot_reproduction.py
# Tested locally, where pdflatex is installed:
python3.10 phase2/tools/check_figure_template.py
```

Input and selection audits do not load final outcomes. The final-prediction
audit verifies already executed results, including equal sample counts and
identical intervention assignments. Figure-only reproduction copies no raw
data or models and requires no GPU. Read the [recovery guide](docs/artifacts.md)
before restoring the complete evidence archive or resuming cached jobs.

Raw data, samples, models, traces, logs and full bank records are ignored under
`.artifacts/phase2/`. Compact manifests, source, tests, metrics and final figures
belong in Git. The existing artifact ignore rules cover both phases. Use
explicit staging and the cumulative blob audit from the original repository
base, preserving the historical 11.92 MiB already counted:

```bash
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

Limits remain 5 MiB per file and 25 MiB for all unique project blobs, including
intermediate committed versions. No push, submission or Pod termination occurs
as part of these commands.
