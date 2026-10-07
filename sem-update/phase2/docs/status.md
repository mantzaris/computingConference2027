# Phase-two execution status

Last checked: 2026-10-07 23:38 UTC. Work remains on main; nothing has been
pushed. Historical commit ad21e60, its tracked source, results and negative
findings remain unchanged. The verified phase-one total is 869 method runs,
66 datasets and 10.318525 device hours.

All authorized minimum-matrix experiments and reporting are complete: 60
controlled settings from 15 fresh independent five-node SCMs, 15 semantic
settings from five fresh SCMs, and three metadata variants of one real case.
The six main methods cover 468 conditions; controls and fitting checkpoints
produce 2390 selected method-condition records and 5642 endpoint/stage rows.
There are no active GPU jobs or unresolved failed main jobs. Three interrupted
DCDI attempts resumed from the same optimizer/RNG checkpoints after the recorded
pre-evaluation mixture correction. No seeds were replaced. DCDI-DSF met its
strict convergence threshold on 35/36 dataset fits; one controlled fit was capped.

Measured additional device use is **5.774939441813363 hours**, including tests,
development, pilots, interrupted attempts, LLM inference, fitting, final samples,
response curves and real block intervals. Cumulative use is 16.09346407989661
hours. The additional ceiling remains 16 hours, with 10.225061 hours unused.
No further experiments are required for the frozen minimum matrix. Optional
ten-node expansion was omitted at protocol freeze for the documented storage
reason. Scientific review and final manuscript preparation by Alex remain open.

The existing GPU is NVIDIA RTX PRO 4500 Blackwell, 32,623 MiB, driver 580.159.04,
PyTorch 2.8.0+cu128 / CUDA 12.8, SM120. Actual CUDA matrix computation and gradients
passed. Peak allocated tensor memory across method stages was 15.558 GiB;
heartbeat telemetry observed at most 16,933 MiB device memory use. These two
memory measurements have different scopes.

Validation completed: 40 correctness tests, five statistical tests, two archive
integrity tests, all 36 frozen inputs, all 78 selection records, and all 596
prediction archives. The final audit checked 10,985,472 generated observations,
equal 2048-sample environment budgets, identical target draws and frozen model
identities. Nine PDF/SVG figures with PNG previews and two LaTeX tables reproduce
exactly from curated inputs with CUDA hidden (29 output files); their final
layout compiles in the official template without warnings. First renderings
and checks were archived before presentation refinements.

Main outcomes: M3 has the lowest controlled T2 error (0.10617), with corrected
paired differences from the other five main methods. M5 has the fewest observed
harmful repairs (1/60, versus M3 8/60 and M4 7/60) at higher mean error (0.13018).
M5 has the lowest observed semantic mean; ridge M1 is best on the new polarizer
regime. The semantic ranking is uncertain with five systems; real results are
conditional on one familiar apparatus and RGB remains exploratory. The functioning
LLM-edit comparator produced 122 valid new edits and 25 accepted search moves.
See evidence_report.md, interpretation.md and the claim ledger for limitations.

Protocol SHA256:
`a77be30ed7ca7a89c1f0c24e00f4b7f1f0059bd19b7cc8bbe5ecc42afa4249cf`.
Scientific source SHA256:
`ddcfef9c2dc87df3cbc196f67fbd35a9c0b4883e9dda5b3038ee6cf3fc1ec3f3`.

All experiments, analysis, figures and durable preservation are complete.
The local archive verified 10,058 files / 691,756,598 uncompressed bytes; its
503,811,430-byte compressed SHA256 matches the Pod copy. The local ext4 NVMe
mount and exact artifact hashes are in results/artifact_preservation.json.
All required implementation, experiments, analysis and preservation are complete.
There are no execution blockers or required experiment resumes. The staged-blob
audit passed: approximately 10.30 MiB of new unique blobs, 22.22 MiB cumulatively
including historical intermediate versions, and a largest file of 4,045,448 bytes.
The exact totals and 5 MiB / 25 MiB limits are in results/repository_size.json.
No raw datasets, model weights, checkpoints, caches or full logs are staged.
No push, paper submission or Pod termination has been performed.

Status/recovery commands on the existing Pod, from
`/workspace/computingConference2027/sem-update`:

```bash
export PYTHONPATH=src
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase2"
.artifacts/venv/bin/python phase2/tools/status.py
# Only resume after verifying that no recorded coordinator/workers are active:
.artifacts/venv/bin/python -u -m sem_update.phase2.runner run
.artifacts/venv/bin/python -u -m sem_update.phase2.runner evaluate
.artifacts/venv/bin/python -u -m sem_update.phase2.runner report
```

These commands reuse compatible completed work; do not rerun development or
replace the frozen protocol. See artifacts.md for restoration of the ledger and
raw evidence. Remote /workspace is overlay storage, not a verified persistent
volume. The preservation destination is the local ext4 NVMe checkout under
sem-update/.artifacts/phase2/archives/. A successful artifact_preservation.json
records completed transfer and verification; an intended path alone is not proof.
