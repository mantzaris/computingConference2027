# Execution status

The authorized full experiment matrix and final evaluation are complete. All
work is on main under sem-update; no push or submission has occurred. Alex's
scientific review and manuscript approval remain pending.

## Completed work

- 869 method runs across 66 dataset blocks: 775 controlled, 80 semantic and
  14 real-data runs. Thirty independent controlled SCMs and five semantic SCMs
  are the synthetic replication units; the real case is one apparatus.
- All selections froze at 2026-10-07 11:20:21 UTC before final evaluation began.
  Evaluation and initial paper export completed at 11:43:58 UTC. Frozen graphs,
  mechanism manifest, run index, scientific implementation and final metrics
  hashes were reverified after reporting edits.
- Actual CUDA gradients, 23 correctness tests, three timed GPU pilots, the
  separate-development DCDI sweep, frozen local Qwen inference, flow fitting,
  intervention generation and final evaluation executed on the existing Pod.
- Eight PDF/SVG figures and two LaTeX tables pass the downloaded official-class
  layout check with no overflow warnings. A clean curated-only copy with CUDA
  hidden reproduced all 18 vector/table files byte for byte; no numerical or
  graph input changed. Final reference arrays for all 66 datasets were preserved
  and checked against originally reported row counts and means.
- Evidence report, source-linked novelty review, protocol, data audit, sample
  manifests, actual metrics, adverse example, manuscript outline and supported/
  mixed/unsupported/untested claim ledger are present.

## Resource use and results

Measured device: NVIDIA RTX PRO 4500 Blackwell, 32,623 MiB, driver 580.159.04;
Python 3.12.3, PyTorch 2.8.0+cu128, CUDA 12.8, compiled sm_120 support. The ledger
records **10.318525 GPU-job hours of 64**, taking the union of overlapping device
reservation intervals. Peak sampled whole-device occupancy was 16,811 MiB;
maximum recorded method tensor allocation was 16,742,893,056 bytes. These memory
quantities have different definitions. See runtime_memory_summary.json.

No active ledger jobs remain. There are 1,775 completed jobs and three preserved
historical setup/development failures; no main-suite or final-evaluation failure
was dropped. No further GPU runtime is required for the frozen study.

Controlled T2 mean differences favor diagnostic repair: −0.07815 versus fixed
and −0.04825 versus random, with paired SCM intervals excluding zero. The audit
left ten harmful conditions among 120 both before and after checking. Semantic
and coherent real-case prediction worsened. The LLM-edit adaptation produced no
admissible new candidate in 18 conditions and retained all initial graphs;
report that interface failure, not a claim about CauScientist's efficacy.
Diagnostic and random shared a 12-DAG cap but used different achieved fitting
work. See docs/evidence_report.md for exact intervals, costs and limitations.

## Preservation and repository finalization

/workspace on the Pod is a 75 GiB container overlay, not a verified persistent
volume. The final remote inventory was checksum-verified in the existing local
checkout's ignored sem-update/.artifacts directory: 22,457 files,
2,982,804,998 bytes, every size and SHA256 matched. This includes raw data,
checkpoints, generated samples, raw LLM outputs, logs, source archives and a
consistent SQLite ledger snapshot. See durable_preservation.json. The actual
Git index and cumulative history passed the required size gates; the compact
numbers are in repository_size_check.json and the full audit is ignored under
.artifacts/logs/final-git-size-audit.json. This result package is committed on
main. Model/environment
caches are excluded from the mirror and pinned for reacquisition. Do not
terminate the Pod; termination was not requested. No access blocker exists.

## Exact compatible resume and verification commands

On the existing Pod, from /workspace/computingConference2027/sem-update:

```bash
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts"
export PYTHONPATH="$PWD/src"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HOME="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/huggingface"
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export PYTHONPYCACHEPREFIX="$SEM_UPDATE_ARTIFACT_ROOT/model_cache/pycache"
python3 scripts/progress.py
.artifacts/venv/bin/python -m sem_update.cli run --resume
.artifacts/venv/bin/python -m sem_update.cli evaluate --frozen-manifest results/curated/frozen_selections.json
.artifacts/venv/bin/python -m sem_update.cli export-paper --plots-only
.artifacts/venv/bin/python scripts/check_plot_reproduction.py
```

The first two scientific commands deduplicate completed compatible jobs; they
are recovery commands, not invitations to change the frozen protocol or tune
on exposed outcomes. Check the ledger and failure trace before any recovery.
Do not restart completed development jobs under a new implementation hash.

From the local sem-update directory, with the final mirror available:

```bash
python3 scripts/check_figure_template.py
python3 scripts/verify_mirror.py --expected-sha256 4d4d224179c322e85791d132d00ccdcfd1f92aa87a332bb39d417b1d37cce9d4
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

The verified final inventory digest is recorded in durable_preservation.json. The
full actual-index audit stays in .artifacts/logs; no blanket staging, Git LFS,
dataset, checkpoint or model upload is permitted. Initial implementation commit
on main: 569797e640ea229e7b4ce2083606bca522c809d8. Its 65 explicitly staged files
used 478,200 unique blob bytes. Final size accounting includes these historical
blobs and every newly staged version. Use `git log -1 --format=%H -- sem-update`
for the result-package commit. No authorized experiment or packaging work
remains; Alex's scientific and manuscript review is pending. The user handles
pushing.
