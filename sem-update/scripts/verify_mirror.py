#!/usr/bin/env python3
"""Verify a local evidence mirror against an inventory hashed on the Pod.

Run only after the remote experiment writers have stopped and a consistent
ledger snapshot and final artifact inventory have been copied locally.
Model downloads and environment caches are revision-pinned, not mirrored.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-sha256', required=True,
                        help='SHA256 of the final remote artifact_manifest.json')
    args = parser.parse_args()
    root = Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT', PROJECT / '.artifacts')).resolve()
    manifest = root / 'artifact_manifest.json'
    if digest(manifest) != args.expected_sha256:
        raise RuntimeError('Copied inventory does not match the expected remote SHA256')
    entries = json.loads(manifest.read_text())['files']
    failures, checked, total = [], set(), 0
    for entry in entries:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or entry['path'] in checked:
            raise RuntimeError('Invalid or duplicate inventory path: ' + entry['path'])
        checked.add(entry['path'])
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise RuntimeError('Inventory path escapes the artifact root: ' + entry['path'])
        if not path.is_file():
            failures.append({'path': entry['path'], 'reason': 'missing'})
        elif path.stat().st_size != entry['bytes']:
            failures.append({'path': entry['path'], 'reason': 'size mismatch'})
        elif digest(path) != entry['sha256']:
            failures.append({'path': entry['path'], 'reason': 'SHA256 mismatch'})
        total += entry['bytes']
    report = {
        'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'remote_manifest_sha256': args.expected_sha256,
        'destination_policy': 'SEM_UPDATE_ARTIFACT_ROOT or project-local .artifacts',
        'files_checked': len(checked), 'expected_bytes': total,
        'all_files_verified': not failures, 'failures': failures,
        'reacquirable_exclusions': ['model_cache', 'venv'],
        'ledger_snapshot_sha256': digest(root / 'ledger_snapshot.sqlite'),
        'scope': 'Every file in the final remote inventory; excludes mutable live SQLite files',
    }
    target = PROJECT / 'results/curated/durable_preservation.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(target)
    display={k:v for k,v in report.items() if k!='failures'}
    display['failure_count']=len(failures)
    display['first_failures']=failures[:10]
    print(json.dumps(display, indent=2))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
