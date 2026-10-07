# Intervention-guided repair of generative SCMs

Execution workspace for Computing Conference 2027. Everything maintained here
stays under `sem-update/`, on `main`. The user handles pushing. No submission or
registration is authorized. See [the complete plan](RESEARCH_PLAN.txt),
[current execution status](docs/status.md), and [deviations](docs/decisions.md), and [implemented protocol](docs/protocol.md).

This is a comparative study, not a claim that generated DAGs establish causality.
Conditional monotone spline flows implement independent-noise SCM mechanisms.
Search diagnostics schedule edits; a common intervention-prediction score accepts
them. Final intervention settings and targets are sealed until selection ends.

## Executed findings

The full matrix completed: **869 method runs over 66 datasets**, including
30 independent controlled SCMs, five semantic SCMs, and one Causal Chambers
apparatus. Recorded reserved-device time was **10.319 GPU-job hours** on the
existing RTX PRO 4500, within the 64-hour cap. All selections were frozen
before final evaluation. See the [evidence report](docs/evidence_report.md) and
[claim ledger](results/curated/claim_ledger.csv).

| Primary T2 comparison | Mean error difference | 95% interval |
| --- | ---: | ---: |
| Controlled: diagnostic − fixed | −0.07815 | [−0.10060, −0.05672] |
| Controlled: diagnostic − random | −0.04825 | [−0.06652, −0.03211] |
| Semantic: diagnostic − LLM edit | +0.03057 | [+0.01085, +0.05029] |
| Real, coherent: diagnostic − fixed | +0.00482 | [+0.00219, +0.00648] |

Negative favors diagnostic repair. Synthetic intervals resample independent
SCMs while preserving paired conditions; the real interval is conditional on
one apparatus, fixed models and ten-row acquisition blocks. These are different
uncertainty estimates. Controlled mean T2 SW1 was 0.09927 for diagnostic repair,
0.14752 for random repair, and 0.17742 for fixed graphs.

The adverse results matter: 10/120 controlled conditions remained harmful after
the audit, unchanged from before it; repair worsened semantic and coherent real
prediction. The LLM-edit adaptation produced **no admissible new candidate** in
18 conditions: 84 parsed one-edge outputs violated the complete-graph edit
contract, and 18 attempts violated assigned roots. It returned the initial graph
every time. This failed interface does not test CauScientist's published efficacy.
The equal 12-DAG maximum also yielded unequal achieved work: diagnostic versus
random averaged 9,047 versus 7,525 canonical fitting updates. No advantage at
equal achieved compute is claimed.

Eight [publication figures](paper/figures/) are available as PDF and SVG, with
[captions](paper/captions.md), two LaTeX tables, and traceable plotting inputs in
`results/curated/`. The [manuscript outline](paper/outline.md) is for Alex's review;
no final manuscript or author approval is implied.

## Environment and commands

Tested execution environment: Python 3.12.3, PyTorch 2.8.0+cu128, NVIDIA RTX PRO
4500 Blackwell, driver 580.159.04. CUDA compute capability 12.0 and compiled
sm_120 kernels verified with finite gradients. Local system Python 3.8 is not
supported. CPU checks do not count as GPU experiments.

From this directory on the existing GPU machine:

```bash
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts"
export PYTHONPATH="$PWD/src"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HOME="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/huggingface"
export PIP_CACHE_DIR="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pip"
export MPLCONFIGDIR="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/matplotlib"
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export PYTHONPYCACHEPREFIX="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pycache"
.artifacts/venv/bin/python -m sem_update.cli doctor
.artifacts/venv/bin/python -m sem_update.cli prepare-data
.artifacts/venv/bin/python -m sem_update.cli prepare-models
.artifacts/venv/bin/python -m sem_update.cli smoke
.artifacts/venv/bin/python -m sem_update.cli pilots
```

Doctor, data preparation, correctness checks and all three GPU pilots have
executed on the Pod. The latest 23-check CUDA suite passed; the pinned model bootstrap also completed.
The LLM smoke and benchmark stages generated actual local-model outputs. All
869 benchmark selections and their final evaluations completed. Failures from
development remain in the ledger; none are omitted as unfavorable observations.

The environment lock is `requirements.lock`; `scripts/bootstrap.sh` recreates
the project environment. The lock includes the tested PyTorch CUDA 12.8 wheel
and its [official wheel index](https://download.pytorch.org/whl/cu128).
The tested installation dry-run passed for all 68 locked distributions. Downloads,
model caches and virtual environments must stay under `.artifacts`.

The following development and final-stage commands were executed successfully.
Completed jobs resume from compatible records. Keep the frozen files unchanged;
do not rerun development tuning after inspecting final outcomes.

```bash
.artifacts/venv/bin/python -m sem_update.cli run --config configs/development.yaml --resume
.artifacts/venv/bin/python -m sem_update.cli freeze --config configs/core.yaml
.artifacts/venv/bin/python -m sem_update.cli run --resume
python3 scripts/progress.py
.artifacts/venv/bin/python -m sem_update.cli evaluate --frozen-manifest results/curated/frozen_selections.json
.artifacts/venv/bin/python -m sem_update.cli export-paper
.artifacts/venv/bin/python -m sem_update.cli export-paper --plots-only
.artifacts/venv/bin/python -m sem_update.cli verify-artifacts
python3 scripts/check_figure_template.py
.artifacts/venv/bin/python scripts/check_plot_reproduction.py
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

The plots-only export uses curated numerical inputs and graph JSON without
training or generating new samples. First export needs the preserved artifacts.
The template-check command requires local pdflatex and the downloaded official
ZIP under `.artifacts/data/raw/venue/`; it creates an ignored internal figure
gallery, not a submission manuscript. All eight figures and two tables passed
the official-class layout check without overflow warnings; see
`figure_template_check.json`. The clean reproduction check uses only curated
inputs with CUDA hidden; it records exact output hashes in
`plot_reproduction_check.json`. This CPU presentation check is not a GPU experiment.

Do not change the frozen protocol after outcomes are exposed. Failed jobs remain
in the SQLite ledger; exact compatible checkpoints can resume. Already completed
jobs are deduplicated. The 64-hour budget is the union of device-reservation
intervals, including the local LLM and baselines, with individual job times also
retained. No paid resource creation is part of these tools.

## Storage and provenance

Default artifacts: the absolute project-local `.artifacts/`. An explicitly
configured `SEM_UPDATE_ARTIFACT_ROOT` overrides it. Do not invent an external
destination. The current Pod's `/workspace` is container overlay storage, not a
verified persistent network volume. The final local mirror at
`/home/resort/Documents/repos/computingConference2027/sem-update/.artifacts`
passed size and SHA256 checks for all 22,457 inventoried files (2,982,804,998
bytes). See `results/curated/durable_preservation.json`. The Pod copy remains at
`/workspace/computingConference2027/sem-update/.artifacts`. Model downloads and
environment caches are excluded, with revisions/locks retained for reacquisition.
The Pod has not been terminated. Ignored artifacts require this separate backup;
a Git push alone does not preserve them.

Raw data, arrays, checkpoints, generated samples, model weights, logs and traces
are artifacts. Only compact metrics, reproducibility manifests, small graph JSON,
plotting tables and final vector figures belong in Git. `check_staged.py` reads
the actual Git index, enforces 5 MiB per file and 25 MiB aggregate new project
blobs, including intermediate committed versions, and rejects
raw/cache/checkpoint/secret paths. Stage explicit files only. The final actual-
index audit passed; its compact totals are in
`results/curated/repository_size_check.json`, and its complete blob list is
`.artifacts/logs/final-git-size-audit.json`.

The pinned DCDI source is stored at `.artifacts/third_party/dcdi`, revision
`594d328eae7795785e0d1a1138945e28a4fec037`, from the
[official repository](https://github.com/slachapelle/dcdi). The GPU adapter is
documented in `docs/decisions.md`. Qwen weights use the exact revision in
`results/curated/llm_revision.json`, Apache-2.0; no fine-tuning or web retrieval is
used for proposals. Full raw LLM outputs remain artifacts, with sanitized
proposals and hashes curated for reproducibility.

## Scientific interpretation

The primary endpoint is macro joint non-target sliced Wasserstein-1 on T2 (new
intervention settings); T1 and T3 remain separate. Independent SCMs, rather than
optimization seeds or generated samples, are bootstrap units. Real-case
interpretation is conditional on one apparatus and its acquisition protocol.
See [the source-linked novelty review](docs/novelty.md),
[dataset audit](docs/dataset_audit.md), and [venue rules](docs/venue.md).
Alex's scientific review remains pending.
