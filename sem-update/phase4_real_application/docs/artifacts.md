# Durable evidence and size accounting

The complete phase-four evidence root is
`sem-update/.artifacts/phase4_real_application/`, both in the local checkout and
under `/workspace/computingConference2027/` on the existing Pod. The Pod reports
an overlay filesystem; it is not the independently durable copy. The archive
`archives/durable-evidence.tar.gz` is copied to the local ext4 filesystem and
verified file by file. Exact checksums, byte counts, filesystem and verification
results are recorded in `results/artifact_preservation.json`.

The archive contains actual source CSVs and ZIPs, acquisition protocols/licenses,
development diagnostics, processed split arrays, frozen candidate banks,
checkpoints, all 32 unique prediction files, observed bootstrap draws, full
precision metrics, failed-attempt records, ledger intervals, source/environment
snapshots and all scientific figures. A consistent `ledger_snapshot.sqlite`
preserves cumulative usage from previous phases. Earlier archives are retained
unchanged; no history or experimental evidence is deleted to meet the Git cap.

The inventory excludes reproducible caches and dependency symlinks. Pinned
Qwen3-8B weights remain in the existing shared model cache at revision
`b968826d9c46dd6066d109eabc6255188de91218`; DCDI source is pinned to
`594d328eae7795785e0d1a1138945e28a4fec037`. They are referenced rather than
duplicated into a second multi-gigabyte archive. The dependency lock and actual
`pip freeze` are preserved in `source_snapshot/`. Newly trained mechanisms and
every generated prediction are included in the archive.

Verification from `sem-update/` uses the existing tested archive checker:

```bash
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase4_real_application"
python3 phase3/tools/archive_evidence.py verify \
  --archive "$SEM_UPDATE_ARTIFACT_ROOT/archives/durable-evidence.tar.gz" \
  --output phase4_real_application/results/artifact_preservation.json
```

For restoration into an empty phase-four artifact root, extract the verified
archive there and copy `ledger_snapshot.sqlite` to `ledger.sqlite` only if no
live ledger exists. Restore/reacquire the pinned dependencies before invoking the
README commands. Never overwrite a newer ledger or rerun arbitrary seeds.
The archive inventory lists SHA256 and byte size for every included file; the
verification command streams every archive member without needing another copy.

Only two final PDFs are selected for Git: `A_process_graph.pdf` and
`D_accuracy_cost.pdf`. The complete vector/raster set is under artifact `figures/`:
the two selected panels, pressure and current responses, effect heatmap, recorded
pressure/current tradeoff and two M5 component graphs. The official-template
gallery is `paper_layout_check/layout.pdf`. Compact plotting tables reproduce all
24 PDF/SVG/PNG files without observations, checkpoints or a GPU.

Other intentionally ignored material includes `reports/all_metrics.csv`,
`reports/all_effects.csv`, `reports/graphs_full.json`,
`reports/speed_predictions.csv`, full-precision copies of curated tables,
initial figure variants, model caches and full logs. They are absent from Git
because the cumulative allowance was already 24.603 MiB, not because they
contradict the study. Curation retains ten significant digits in CSVs and does not
change frozen protocol/LLM/selections files. The reporting-import correction was
verified to leave all 32 prediction files and ten result tables byte-identical.

`results/repository_size.json` records actual staged-blob accounting against
`ef2e0cac3fd2d572caf16c98f68cf45392882d28`, including intermediate historical blob
versions. Limits remain 5 MiB per file and 25 MiB cumulative. The full checker
inventory remains ignored. No push or Pod termination is authorized by this
preservation record.
