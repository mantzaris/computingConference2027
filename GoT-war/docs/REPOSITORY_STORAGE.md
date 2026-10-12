# Repository storage policy

Commit code, configurations, prompts, tests, scientific documentation, the manuscript source/PDF, publication SVG/PDF figures, source manifests and concise result tables. Keep the full campaign locally under ignored `runs/`, with private packets/prompts and caches in their existing ignored directories. Nothing was deleted from the original campaign when the release was slimmed.

The compact `results/reproduction.tar.gz` contains the exact frozen benchmark, all 120 controlled records with failed attempts, four retained application records, their paired baselines/final audits, and environment/usage provenance. `results/reproduction_manifest.json` lists every member, its size and SHA-256. Timing metadata is derived from all 956 requests without copying their raw response log. `python3 scripts/reproduction.py` validates the archive and restores missing inputs; it refuses to overwrite changed files. Repeating the command is safe. `--check` verifies without restoring and `--pack` rebuilds the curated archive from the complete local campaign.

Earlier application candidates, interrupted responses, transport/server logs, checkpoints and synchronization snapshots stay local. Failure counts, the failure inventory and final scientific caveats remain published; many failure-inventory paths refer to the local archive. Full developmental audit/replay requires that archive. Private source packets are still required for exact source-offset checks. The compressed archive is sufficient for the reported numerical analyses, model execution, figure rendering and manuscript generation, not a replacement for every campaign record.

Expanded benchmark JSONL, PNG previews, template examples/manuals, TeX build products, downloads, model weights and Git backup bundles are ignored. The template source URL/hash and the class/style files needed for compilation are retained. SVG/PDF figures and the compiled manuscript are intentionally published; their bytes are included in the release budget.

Before committing from the repository root:

```sh
git add -- GoT-war
python3 GoT-war/scripts/check_release.py --write-manifest
git add -- GoT-war/results/artifact_manifest.json
python3 GoT-war/scripts/check_release.py
git commit
```

The checker measures staged Git blobs, rejects staged files covered by `.gitignore`, and enforces **250 files, 8 MiB total, 2 MiB per file** for GoT-war. It does not install a repository-wide hook or affect other projects. Do not force-add ignored outputs. These limits leave room for normal manuscript and code updates while keeping an accidental campaign dump out of a routine commit.

On 2026-10-12, remote `main` was checked at `bfbe4889bfebe38f508c01a8d2350c50933b86fb`. All 13 subsequent commits concerned GoT-war and were still unpushed. They were consolidated into the compact delivery so earlier bulky blobs would not accompany the first push. Published history was preserved. The original unpushed history is recoverable from the ignored `.private/release_slimming/unpushed-history.bundle`, requiring that remote base commit; the working campaign files remain in place. Work stays on `main`, and pushing is left to the researcher.
