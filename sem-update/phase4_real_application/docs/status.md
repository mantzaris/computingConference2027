# Phase-four execution status

Experiments and scientific analysis completed on 9 October 2026 UTC. No GPU jobs
remain active. Human scientific review remains pending. Historical studies and
their negative findings are unchanged. Work is on `main`; no push, submission,
new paid resource or physical equipment operation occurred.

All six main methods, fixed flows, random repair, five grouped training-file
refits and the actual LLM semantic-prior comparison ran. Fifty-one evaluated
method records include the matched-compute checkpoints; they are analyses of
**one apparatus**, not 51 independent systems. The primary panel contains 699
measurements/five acquisition files; the shorter-wait panel contains 3,200/three.
The model has eleven variables. All nine banks (216 candidate records), 98
selections and 512 generated arrays (2,097,152 model draws in 32 unique files)
passed the integrity audit.

Additional device-job usage is **0.793967733 hours** (2,858.284 seconds), including
pilot, tests, LLM, failed logging attempt and corrective resume. Previous usage
was 35.576099443 hours; cumulative usage is **36.370067176 hours**, below this
phase's twelve-hour ceiling and the remaining project authorization. The RTX PRO
4500 Blackwell performed actual CUDA gradients, fitting, sampling and distribution
computations. Peak allocated memory was 16,624,408,576 bytes during local LLM use;
main fitting/inference peaks are recorded separately in costs.csv. DCDI produced
valid capped/projected predictions after 40,000 steps, without strict convergence.

M2 has the best observed primary error (0.2199); M3/random are nearly tied
(0.3310/0.3320). Fixed flows offer a useful cost compromise (0.3602; 29.44 seconds).
Repair harm counts tie at zero/five under the unchanged definition, but predictive
coverage is below nominal and the M3 graph misses the measured hatch effect.
Every matched LLM prior worsens primary error. All methods make identical recorded
operating decisions. Formal superiority and verified control benefits are not
supported. Full qualifications are in evidence_report.md and interpretation.md.

Validation: 61 scientific tests passed on CUDA; intervention assignments,
calibration, split separation, root masks, flow semantics, selection arithmetic
and full prediction hashes passed. The logging-import fix changed no prediction
file or output table. All 24 final PDF/SVG/PNG files reproduce byte-for-byte from
compact inputs, including the corrected fan-duty/hatch-degree labels. Six main
figures plus the comparison table compile in the official Springer template with
no layout warnings. Template and figure hashes are recorded in results/.

Full evidence is preserved under `.artifacts/phase4_real_application/`; durable
archive verification and final repository-size checks are recorded in
`results/artifact_preservation.json` and `results/repository_size.json`.
Only two selected PDFs are intended for Git; all remaining final formats and
full precision results remain preserved and reproducible. No experiment remains
to launch. On the original Pod, these exact commands verify or resume completed
stages without resetting the ledger:

```bash
cd /workspace/computingConference2027/sem-update
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase4_real_application"
export PYTHONPATH="src:phase4_real_application/tools"
.artifacts/venv/bin/python phase4_real_application/tools/application.py status
.artifacts/venv/bin/python phase4_real_application/tools/application.py run
.artifacts/venv/bin/python phase4_real_application/tools/finish.py
```

The completed run command skips fitted stages. See README.md for figure,
template, artifact and staged-blob checks. Additional physical experiments are
recommendations for human review, not unfinished authorized jobs.
