# Evidence preservation and recovery

The execution root is
`/workspace/computingConference2027/sem-update/.artifacts/phase3` on the existing
Pod. The local destination is
`/home/resort/Documents/repos/computingConference2027/sem-update/.artifacts/phase3`.
The Pod's filesystem is overlay; independent persistence has not been verified.
The local checkout is ext4 on `/dev/nvme0n1p2`. **Durable local preservation passed
at 2026-10-08 21:52:02 UTC.** The archive file and parent directory were synchronized
to disk, every member's SHA256/size matched its inventory, and the complete archive
matched the Pod's SHA256. There were no verification errors. Neither a manifest
alone nor the Git repository is a backup of the raw evidence.

| Preserved item | Verified value |
| --- | --- |
| Local archive | `sem-update/.artifacts/phase3/archives/durable-evidence.tar.gz` |
| Archive bytes | 13,426,087,062 |
| Evidence files | 39,917 |
| Uncompressed inventoried bytes | 15,973,997,331 |
| Archive SHA256 | `45c85e03a551f8a4e8e682e222a1a6c40206a24570b196070d228b8b57cf825f` |
| Inventory SHA256 | `c6650327a42bd9c5dd1af2f1cdaa60530e66c7e116467b15a38fd083958d91ab` |

The full check is [artifact_preservation.json](../results/artifact_preservation.json).
A separate earlier local copy verified all 16,472 sealed checkpoint files
(555,120,920 bytes); its detailed record is
`.artifacts/phase3/sealed_checkpoint_copy.json`. The full archive additionally
preserves partial/failed attempts, data and all generated predictions. No evidence
was deleted. The Pod remains running; termination is not authorized.

The frozen main source is `archives/frozen_source.tar.gz`; the earlier pilot
source is `archives/pilot_source.tar.gz`. Their hashes are recorded separately.
Preserve both: pilots preceded the documented memory/accounting/resume changes.
The final executed code and curated outputs are also preserved in
`archives/executed_code_and_outputs.tar.gz`, SHA256
`9944cd471e3a7009246610d0beb99c95d3001093844e6ec68ffaf54d3d765f6a`.
Eighty-six local source/test/tool/configuration/dependency files match that
snapshot byte-for-byte; generated editable-install metadata is excluded from
that source comparison. Final narrative and preservation records are in Git.
The live ledger contains the unchanged historical intervals plus phase-three
jobs. Its phase boundary retains 16.09346408 historical device hours and the
additional 24-hour maximum. Do not initialize a new allowance when restoring.

After all jobs stop, `tools/seal_evidence.py` archives the executed code and
curated outputs, then `tools/artifact_manifest.py` takes a consistent SQLite
snapshot and inventories arrays, complete and partial checkpoints, samples,
graphs, traces, failures, logs and all figure formats. It excludes reacquirable
caches, the reused DCDI checkout, live SQLite sidecars, and the consolidated copy
itself. `archive_evidence.py create` rechecks every input hash while archiving.
No evidence is deleted to reduce repository or disk size.

```bash
# From sem-update/, on the quiescent execution machine:
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase3"
# This completed run already has a sealed archive; do not overwrite it.
# For a new quiescent run, send stdout outside the inventoried root:
.artifacts/venv/bin/python phase3/tools/seal_evidence.py \
  > .artifacts/phase3-preservation.log 2>&1
```

Transfer the resulting `archives/durable-evidence.tar.gz` to the local ignored
destination, synchronize the file and parent directory, then verify all members:

```bash
# Standard-library-only verification on the local machine:
python3 phase3/tools/archive_evidence.py verify \
  --archive .artifacts/phase3/archives/durable-evidence.tar.gz \
  --output .artifacts/phase3/reverification.json
```

The verifier streams every member and compares its size and SHA256 without
extracting another full copy. Its result records the archive hash and destination
filesystem. Compare that hash with the execution machine's archive hash. A Pod
termination still requires separate authorization after successful preservation.
The example writes a new ignored record, preserving the completed transfer/fsync
record rather than overwriting it with a later verification-only result.

Recovery requires the locked CUDA environment, pinned upstream DCDI source, the
curated Git files and the verified archive. Restore into an empty project-local
directory, preserving historical evidence:

```bash
mkdir .artifacts/phase3-restored
tar -xzf .artifacts/phase3/archives/durable-evidence.tar.gz \
  -C .artifacts/phase3-restored
cp .artifacts/phase3-restored/ledger_snapshot.sqlite \
  .artifacts/phase3-restored/ledger.sqlite
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase3-restored"
export PYTHONPATH="$PWD/src"
.artifacts/venv/bin/python phase3/tools/artifact_manifest.py --verify
.artifacts/venv/bin/python phase3/tools/status.py
```

These are recovery instructions, not commands to overwrite active evidence.
The archive intentionally contains a quiescent ledger snapshot rather than a
database copied while workers write. Compatible frozen selections are immutable;
an incomplete sealed matrix cannot silently become a different final study.
Figure-only reproduction uses compact Git plotting inputs and locked plotting
dependencies, with CUDA hidden and no raw data or fitted models.

Earlier real-data, semantic and LLM evidence remains in the separate phase-two
archive. Phase three neither expands the apparatus variables nor generates new
LLM proposals. All project paths, including caches and restored evidence, stay
under `sem-update/`.
