# Intervention-guided repair of generative SCMs

Execution workspace for Computing Conference 2027. Everything maintained here
stays under `sem-update/`, on `main`. The user handles pushing. No submission or
registration is authorized. See [the complete plan](RESEARCH_PLAN.txt),
[current execution status](docs/status.md), and [deviations](docs/decisions.md).

This is a comparative study, not a claim that generated DAGs establish causality.
Conditional monotone spline flows implement independent-noise SCM mechanisms.
Search diagnostics schedule edits; a common intervention-prediction score accepts
them. Final intervention settings and targets are sealed until selection ends.

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
Consult status for current validation. The LLM smoke stage generated actual proposals. Main-suite
completion is recorded separately in `docs/status.md`; code or launch commands
alone are not experimental evidence.

The environment lock is `requirements.lock`; `scripts/bootstrap.sh` recreates
the project environment. The lock includes the tested PyTorch CUDA 12.8 wheel
and its [official wheel index](https://download.pytorch.org/whl/cu128).
The tested installation dry-run passed for all 68 locked distributions. Downloads,
model caches and virtual environments must stay under `.artifacts`.

Development and final-stage commands (consult status for which have completed):

```bash
.artifacts/venv/bin/python -m sem_update.cli run --config configs/development.yaml --resume
.artifacts/venv/bin/python -m sem_update.cli freeze --config configs/core.yaml
.artifacts/venv/bin/python -m sem_update.cli run --resume
.artifacts/venv/bin/python -m sem_update.cli evaluate --frozen-manifest results/curated/frozen_selections.json
.artifacts/venv/bin/python -m sem_update.cli export-paper
.artifacts/venv/bin/python -m sem_update.cli export-paper --plots-only
.artifacts/venv/bin/python -m sem_update.cli verify-artifacts
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

The plots-only export uses curated numerical inputs and graph JSON without
training or generating new samples. First export needs the preserved artifacts.

Do not change the frozen protocol after outcomes are exposed. Failed jobs remain
in the SQLite ledger; exact compatible checkpoints can resume. Already completed
jobs are deduplicated. The 64-hour budget is the union of device-reservation
intervals, including the local LLM and baselines, with individual job times also
retained. No paid resource creation is part of these tools.

## Storage and provenance

Default artifacts: the absolute project-local `.artifacts/`. An explicitly
configured `SEM_UPDATE_ARTIFACT_ROOT` overrides it. Do not invent an external
destination. The current Pod's `/workspace` is container overlay storage, not a
verified persistent network volume. Experiment evidence needs a verified local
mirror before Pod termination; ignored files are not automatically backed up.

Raw data, arrays, checkpoints, generated samples, model weights, logs and traces
are artifacts. Only compact metrics, reproducibility manifests, small graph JSON,
plotting tables and final vector figures belong in Git. `check_staged.py` reads
the actual Git index, enforces 5 MiB per file and 25 MiB aggregate new project
blobs, and rejects raw/cache/checkpoint/secret paths. Stage explicit files only.

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
