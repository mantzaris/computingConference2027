# Execution status

Updated 2026-10-07 02:58 UTC.

The complete supplied plan was read and copied unchanged to RESEARCH_PLAN.txt.
The existing checkout is on main. No unrelated changes were present, no branches
were created, and the user will push. No paper submission is authorized.

## Completed execution

- Existing RunPod connected; NVIDIA RTX PRO 4500 Blackwell, 32623 MiB,
  driver 580.159.04, Python 3.12.3, PyTorch 2.8.0+cu128, sm_120.
  Actual CUDA computation and finite gradients passed.
- Causal Chambers lt_interventions_standard_v1 downloaded and audited: 46
  columns, assignment protocols, fixed sensor settings and temporal dependence.
  Six-variable acquisition-block design prepared; total non-test experimental
  budget is 7,856 rows (6,656 reference plus 1,200 mid-RGB assignments).
- Qwen3-8B pinned BF16 CUDA inference produced two valid smoke proposals.
  Public model/bootstrap verification and scripts/bootstrap.sh both executed.
- Latest correctness suite: 23 passed in 3.71 seconds on the GPU machine.
  Dependency lock: 68 distributions, installation dry-run and bootstrap passed.
- Original three full 12-candidate GPU pilots completed in 157.57, 130.96,
  315.32 seconds. A fresh three-process cold-cache pilot group completed in
  331.62 seconds; individual times 214.78, 175.53, 328.86 seconds.
- All 18 DCDI development fits completed. Regularization 0.1 selected by mean
  development search score 1.40551 versus 1.55766 for 1.0. Some fits reached
  their update cap before the strict normalized acyclicity tolerance; flags,
  graph projections and all development failures remain recorded.
- Closest-work review includes CauScientist, DCDI, CMA, causal normalizing flows,
  ABAPC-LLM and residual independence/invariance literature. Official venue
  formatting, anonymity and GenAI requirements reviewed; Alex's review pending.

## Active phase and runtime

No GPU jobs are active at this checkpoint. Protocol freeze and the full benchmark
are next; no final benchmark outcomes have been opened. Runtime plan selects
30 controlled SCMs (d=5,10), five semantic SCMs, one real case, 66 datasets and
869 method runs, preserving all matched comparisons. Three controlled-dataset
workers share the existing device; LLM stages are separate from flow fitting.

Measured reserved-device time before the main matrix: 1.592 hours.
Forecast remaining: 38.57 hours including analysis and recovery allowance;
planning upper estimate: 52 hours, below the remaining 62.41-hour cap.
These are forecasts, not results. See results/curated/runtime_plan.json.
The SQLite ledger enforces a 64-hour union of recorded device-reservation
intervals, including baselines and LLM inference. No new resource is provisioned.

## Preservation and blockers

/workspace is a 75 GiB container overlay, NOT a verified persistent volume.
No network volume is mounted. A provisional local .artifacts mirror contains
raw data, checkpoints, logs, run records, source archives and a consistent ledger
snapshot. Final checksum verification is pending; do not terminate the Pod.
Local free space is about 3.5 GB and will be monitored. Model/environment caches
are reacquirable from the pinned revisions and lock. No access blocker exists.
No experiment dataset, checkpoint or model is staged. Actual staged-blob checks
are required before every commit and cumulatively against the initial commit.

## Exact continuation commands

On the existing Pod, from /workspace/computingConference2027/sem-update:

```bash
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts"
export PYTHONPATH="$PWD/src"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HOME="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/huggingface"
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export PYTHONPYCACHEPREFIX="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pycache"
.artifacts/venv/bin/python -m sem_update.cli freeze --config configs/core.yaml
.artifacts/venv/bin/python -m sem_update.cli run --resume
.artifacts/venv/bin/python -m sem_update.cli evaluate --frozen-manifest results/curated/frozen_selections.json
.artifacts/venv/bin/python -m sem_update.cli export-paper
```

Do not open final outcomes until every selection is frozen and its hashes verify.
Read runtime_ledger.json and preserved worker logs before resuming a failed job.
Do not restart the completed development grid under a new source hash.
Remote connection details are intentionally not committed.
