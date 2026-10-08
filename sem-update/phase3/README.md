# Phase three: causal-model repair at 20–100 nodes

This separate study investigates the earlier accuracy/reliability findings on
larger connected SCMs. Historical source and results at `ad21e60` and `8c452ac`
remain unchanged. The required matrix completed: **45 independent SCMs, 90 prior
settings, all six methods through 100 nodes**, using **19.483 additional GPU-job
hours**. M3 had the lowest observed mean T2 error at 20/50 nodes but retained G0
in every 100-node setting. M5 had no harmful repairs in 90 adjusted-policy settings,
versus two for M3 and one for M4; its 100-node gain was small. No DCDI discovery
strictly converged, although all capped/projected predictions were valid.
See the [evidence report](docs/evidence_report.md), [interpretation](docs/interpretation.md),
[claim ledger](docs/claim_ledger.md), [status](docs/status.md), the
[frozen protocol](results/protocol.json), [design](docs/protocol.md),
[decisions](docs/decisions.md), and [literature positioning](docs/positioning.md).

The frozen primary design has 45 independent SCMs and 90 corrupted-prior settings:
five SCMs for each size (20, 50, 100) and nonlinear family (additive or
heteroscedastic), plus five 50-node heteroscedastic SCMs for each dense, hub and
deep profile. Fixed and adjusted search budgets are repeated conditions, not new
independent systems. One optional 50-node fixed-total-budget dataset reused an
existing SCM. The optional 100-node sensitivity was not admitted by the frozen
reserve guard; no 200-node demonstration was run.

| Method | Meaning in this phase |
| --- | --- |
| M0 | Independent empirical observational marginals; density NLL unavailable |
| M1 | Linear Gaussian ridge SEM on the common corrupted G0; alpha 0.1 |
| M2 | Pinned official DCDI-DSF density with the documented optimizer adaptation, then common flows |
| M3 | Disturbance-guided search bank, mean calibration selection, one audit |
| M4 | The same bank, robust mean/worst-regime selection with rho 0.5 |
| M5 | The same bank, at most three complete-SCM mixture components, anchored energy-score weights |

Fixed-G0 and random repair are supplementary controls. Oracle flows appear only
on the prespecified first replicate of each cell. M3–M5 share an immutable bank;
each is charged its full logical construction cost. Actual execution savings,
discovery, mechanism fitting, selection and prediction are separately recorded.
Mixture weights express predictive combination, not probabilities of causal truth.

The GPU is the existing NVIDIA RTX PRO 4500 Blackwell with 32,623 MiB reported
device memory, driver 580.159.04, and PyTorch 2.8.0+cu128. Actual CUDA computation
and gradients passed. The final scientific source passed 61 tests. Three complete
development pilots at 20, 50 and 100 nodes took 26.7, 37.5 and 55.4 minutes,
respectively; these are pilot timings, not main performance results. The dense
profile was used for the 50-node pilot. Exact evidence is in
[hardware](results/hardware.json), [correctness](results/correctness.json), and
[pilot provenance](results/pilot_provenance.json).

Commands run from `sem-update/` on the existing Pod. The unchanged parent
`requirements.lock` and pinned DCDI revision
`594d328eae7795785e0d1a1138945e28a4fec037` define the dependencies. Source,
dependency, configuration and protocol hashes are recorded in
[frozen-source provenance](results/frozen_source.json). The installed environment
list and source snapshots stay with the ignored evidence.

```bash
export PYTHONPATH=src
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase3"
.artifacts/venv/bin/python -m sem_update.phase3.runner doctor
.artifacts/venv/bin/python -m sem_update.phase3.runner test
.artifacts/venv/bin/python phase3/tools/status.py
```

The doctor and tests above completed before freezing. Pilots used the separately
archived pilot source, followed by documented pre-freeze optimizations. Do not
rerun those pilots under the main source into their existing artifact identities.
`runner freeze` has already sealed the main protocol. The tested resume coordinator is:

```bash
.artifacts/venv/bin/python -u phase3/tools/execute_main.py
```

Do not start a second coordinator while the recorded process is alive. After an
interruption, inspect `runs/main_session.json`, the status tool and preserved
failure logs first. The same command resumes compatible jobs from atomic
checkpoints, then verifies the sealed inputs and selections before opening final
outcomes. It subsequently evaluates, renders, audits and checks figure
reproduction. A sealed partial result set stays immutable on resume. Numerical
failures are retained; only specified transient failures receive bounded retries.

The phase ceiling is 24 additional device hours including pilots, tests and
failures. Historical use is 16.09346408 hours. Accounting unions overlapping
intervals on one physical device; summed concurrent job wall times are a separate
quantity. Six workers use the same authorized GPU. Admission guards reserve
three hours for final evaluation and illustrations. A capped method with valid
predictions is distinguished from a missing prediction or a failed computation.

Final outputs include [per-condition metrics](results/metrics.csv),
[paired summaries](results/summary.csv), [reliability](results/reliability.csv),
[cost and coverage](results/compute.json), [PDF figures](paper/figures/), and
[publication tables](paper/). All 13 figures exist as PDF/SVG/PNG in ignored
artifacts; Git carries selected formats within the cumulative allowance.
The compact-input-only reproduction check passed byte-for-byte with CUDA hidden,
and all 13 PDFs plus two tables compiled in the official template without layout
warnings. These are tested post-evaluation commands:

```bash
.artifacts/venv/bin/python phase3/tools/audit_execution.py --predictions
.artifacts/venv/bin/python phase3/tools/summarize_interpretation.py
.artifacts/venv/bin/python phase3/tools/check_plot_reproduction.py
# On the local machine with the already downloaded official class and pdflatex:
python3 phase3/tools/check_figure_template.py
```

Final evaluation uses `tools/evaluate_frozen.py`, a tested CSV serialization adapter
for optional projection columns. It does not change the frozen scientific source
or recalculate completed predictions. Original failed output and tracebacks remain
preserved. A final local-graph layout refinement separates overlapping labels;
all node subsets, edges, weights and numeric inputs are unchanged.

Read the [preservation guide](docs/artifacts.md) before restoring evidence.
A Git push alone does not preserve trained models or generated observations.
The sealed model files were independently copied and hash-checked locally; the
full durable archive preserves data, generated outcomes, failed attempts,
logs, source snapshots and all figure formats. No experiment remains active.

```bash
python3 scripts/check_staged.py --base ef2e0cac3fd2d572caf16c98f68cf45392882d28
```

This audit checks actual indexed blobs and all intermediate committed project
blobs, including the historical 22.21707 MiB. Limits remain 5 MiB per file and
25 MiB cumulatively. Stage explicit source, documentation, metrics and selected
paper outputs only. No push, submission, new paid resource or Pod termination is
part of this workflow. Alex's scientific review remains pending.
