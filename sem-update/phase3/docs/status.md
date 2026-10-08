# Phase-three status

Required experiments and analysis are complete as of 8 October 2026 UTC.
All work remains on main under sem-update/; historical studies are unchanged.

- Completed: 45 independent primary SCMs, 90 prior settings, both resource
  policies, all six main methods plus fixed/random controls, nine primary oracle
  SCMs, and one exploratory 50-node fixed-total dataset on an existing SCM.
- Largest evaluated graph: 100 nodes for every method. M2 has valid projected
  predictions but zero strict convergence in 45 primary discoveries.
- Actual additional GPU-job use: 19.482635 h; historical: 16.093464 h;
  cumulative: 35.576099 h. No GPU job is active. Remaining required GPU time: 0 h.
- Validation: 61 pre-evaluation tests; four later CPU serialization/statistics
  checks; final input/prediction audits; identical compact-only figure reproduction;
  13 PDFs and two tables compiled in the official template without layout warnings.
- Operational failure: optional CSV fields initially stopped export; a tested
  serialization-only adapter resumed sealed predictions. Original evidence remains.
- Strictly converged DCDI coverage is unavailable (0/45). Completed capped
  predictions remain valid; changing the optimizer or extending caps would require
  a separately identified protocol, not rewriting this frozen result.
- Omitted: optional 100-node fixed-total sensitivity (frozen admission guard),
  200-node demonstration and assumption-violation extensions. No new real/LLM panel.
- Durable preservation completed at 2026-10-08 21:52:02 UTC: 39,917 files,
  15,973,997,331 uncompressed bytes, a 13,426,087,062-byte archive on local ext4.
  Every member's SHA256/size passed, and local/remote archive hashes match.
  Archive file and parent directory were fsynced. No evidence was deleted.
  See `results/artifact_preservation.json`. No transfer or archive job is active.
- No scientific access blocker remains. The final indexed-blob audit passed; deliverables are committed locally on main.
  Use `git log -1` for the commit identity. No push, submission or Pod termination.

Results and limits are in [evidence_report.md](evidence_report.md) and
[claim_ledger.md](claim_ledger.md). The optional omitted cell remains unexecuted;
resuming the completed coordinator preserves the sealed selection set rather than
silently extending the study.

Tested inspection/resume commands on the existing Pod:

```bash
cd /workspace/computingConference2027/sem-update
export PYTHONPATH=src
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase3"
.artifacts/venv/bin/python phase3/tools/status.py
# Only after confirming no coordinator is alive; completed scientific jobs reuse evidence:
.artifacts/venv/bin/python -u phase3/tools/execute_main.py
```

The last successful coordinator PID was 1000978; state and logs are
`.artifacts/phase3/runs/main_session.json` and
`.artifacts/phase3/logs/main-visual-review.log`. It completed all ten stages.
The earlier failed and successful attempts are preserved separately.
Use [artifacts.md](artifacts.md) for restoration and local verification commands.
Alex's scientific review remains pending.
