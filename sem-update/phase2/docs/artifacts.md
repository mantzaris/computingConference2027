# Evidence preservation and recovery

Git contains the source, frozen protocol, compact metrics and plotting inputs,
parameter hashes, selected graphs, documentation, and selected final figures.
It does not contain experimental arrays, fitted weights, generated observations,
raw model responses, or execution logs. A Git push alone is not an evidence backup.

The execution root is
`/workspace/computingConference2027/sem-update/.artifacts/phase2` on the existing
Pod. Its filesystem is container overlay; it has not been verified as persistent
storage. The local preservation destination is
`/home/resort/Documents/repos/computingConference2027/sem-update/.artifacts/phase2/archives/durable-evidence.tar.gz`.
The completed [verification record](../results/artifact_preservation.json)
confirms 10,058 files, 691,756,598 uncompressed bytes, and a 503,811,430-byte
archive. Every file's size and SHA256 passed verification, and the archive hash
matches the Pod's original:
`be18ea94cdca45ec0c7d8cdeefb75e425e42982972b5d05cec1fcd82c8fe3884`.
The local archive and its parent directory were synchronized to the filesystem
before verification. No Pod termination is authorized.
The local checkout's mount was verified as ext4 on `/dev/nvme0n1p2`; the final
archive verification also records the destination filesystem reported by
`findmnt`. This is an independent local copy, not a claim of a separate cloud backup.

After all jobs are quiescent, `tools/artifact_manifest.py` takes a consistent
SQLite backup and inventories every phase-two evidence file by size and SHA256.
`tools/archive_evidence.py create` checks those hashes again while building the
compressed archive. The archive contains the inventory first, followed by its
listed files, including interrupted attempts, final and partial checkpoints,
raw LLM outputs, samples, traces, and validation logs. It excludes live SQLite
sidecars, reproducible caches and its own consolidated copy. No experimental
evidence is deleted to reduce disk use.

The local verification streams every archive member without extracting a second
copy. This detects corruption while avoiding a second unpacked copy:

```bash
# From sem-update/, after the archive has been copied here:
python3.10 phase2/tools/archive_evidence.py verify \
  --archive .artifacts/phase2/archives/durable-evidence.tar.gz \
  --output phase2/results/artifact_preservation.json
```

The phase-one inventory and local evidence remain separate and unchanged.
Phase two reuses their Causal Chambers source files, the pinned DCDI checkout,
and frozen Qwen3-8B weights. Reacquirable model/environment caches are excluded
from both evidence inventories; their exact revisions and dependency lock are
retained. See `results/hardware.json`, the parent `requirements.lock`, and
`results/protocol.json`. The original environment bootstrap is
`../scripts/bootstrap.sh`, relative to this phase-two directory.

To restore on a machine with sufficient free storage, first restore the parent
study's verified artifacts and locked environment. Use an empty project-local
destination and a verified archive. The following is a recovery procedure, not
a command to run over the active study:

```bash
# From sem-update/. mkdir deliberately fails if the destination already exists.
mkdir .artifacts/phase2-restored
tar -xzf .artifacts/phase2/archives/durable-evidence.tar.gz \
  -C .artifacts/phase2-restored
cp .artifacts/phase2-restored/ledger_snapshot.sqlite \
  .artifacts/phase2-restored/ledger.sqlite
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase2-restored"
export PYTHONPATH="$PWD/src"
.artifacts/venv/bin/python phase2/tools/artifact_manifest.py --verify
.artifacts/venv/bin/python phase2/tools/status.py
```

Restoring the live ledger from its snapshot is essential: the archive deliberately
does not copy a database while workers might be writing it. Keep the phase
boundary and historical entries intact; never create a fresh compute allowance.
Use the completed-study commands in the README only after checking the recorded
owners and compatible frozen hashes. Figure-only reproduction needs the curated
Git files and locked plotting dependencies, without raw data, checkpoints, CUDA,
or the evidence archive.
