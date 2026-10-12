"""Pack or restore the small, lossless set of inputs for offline reproduction.

Default: validate the complete archive, then restore only missing files. Existing
files must match their recorded hashes; no overwrite or network access occurs.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'results/reproduction.tar.gz'
MANIFEST = 'results/reproduction_manifest.json'
MAX_FILES = 200
MAX_BYTES = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def allowed(name, campaign):
    path = PurePosixPath(name)
    return (not path.is_absolute() and '..' not in path.parts
            and name == path.as_posix()
            and (name == 'benchmark/cases.jsonl'
                 or name.startswith('runs/' + campaign + '/')))


def pack(root):
    campaign = json.loads((root / 'configs/budget.json').read_text())['campaign_id']
    run = root / 'runs' / campaign
    # Timing/count metadata suffices to recompute usage; raw response logs remain local.
    ledger = run / 'usage_ledger.jsonl'
    rows = [json.loads(line) for line in (run / 'requests.jsonl').read_text().splitlines()]
    ledger.write_text(''.join(json.dumps({k: v for k, v in row.items() if k != 'response'},
                                      ensure_ascii=False, separators=(',', ':')) + '\n'
                              for row in rows))
    paths = [root / 'benchmark/cases.jsonl']
    paths += sorted((run / 'benchmark').glob('*.json'))
    for pattern in ('*/alternative_*.json', '*/baselines.json',
                    '*/explanation_audit_*.json', '*/final_source_review.json'):
        paths += sorted((run / 'application').glob(pattern))
    paths += [run / name for name in (
        'COMPLETE', 'usage_ledger.jsonl', 'gpu_samples.jsonl', 'processes.json',
        'completion.json', 'inference_finished.json', 'service_counters.json',
        'environment.json', 'pilot_summary.json', 'controlled_contract_audit.json',
        'shutdown_verification.json', 'watchdog_final.json')]
    payload = {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(paths)}
    if len(payload) > MAX_FILES or sum(map(len, payload.values())) > MAX_BYTES:
        raise ValueError('Curated reproduction inputs exceed the release bounds')
    with (root / ARCHIVE).open('wb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0, compresslevel=9) as zipped:
            with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name, data in payload.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    member.mode = 0o644
                    archive.addfile(member, io.BytesIO(data))
    manifest = {
        'schema': 1, 'campaign_id': campaign,
        'archive': ARCHIVE, 'archive_sha256': digest((root / ARCHIVE).read_bytes()),
        'archive_bytes': (root / ARCHIVE).stat().st_size,
        'expanded_bytes': sum(map(len, payload.values())), 'file_count': len(payload),
        'scope': 'Frozen benchmark, 120 controlled records including failed attempts, four final application records, paired baselines, final audits and usage provenance. Expanded files are ignored by Git.',
        'local_only': 'Raw request responses, earlier application candidates, private source packets/prompts, logs, caches and original Git history remain in the original local workspace; they are not in this archive.',
        'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in payload.items()},
    }
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    return {k: manifest[k] for k in ('file_count', 'archive_bytes', 'expanded_bytes')}


def restore(root, check_only=False):
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text())
    source = root / ARCHIVE
    if digest(source.read_bytes()) != manifest['archive_sha256']:
        raise ValueError('Reproduction archive hash does not match its manifest')
    expected = manifest['files']
    if len(expected) > MAX_FILES or sum(x['bytes'] for x in expected.values()) > MAX_BYTES:
        raise ValueError('Reproduction manifest exceeds the release bounds')
    payload = {}
    with tarfile.open(source, 'r:gz') as archive:
        for member in archive:
            if (member.name not in expected or member.name in payload or not member.isfile()
                    or not allowed(member.name, manifest['campaign_id'])
                    or member.size != expected[member.name]['bytes']):
                raise ValueError('Unexpected archive member: ' + member.name)
            data = archive.extractfile(member).read()
            if digest(data) != expected[member.name]['sha256']:
                raise ValueError('Record hash mismatch: ' + member.name)
            payload[member.name] = data
    if set(payload) != set(expected):
        raise ValueError('Archive is missing records')
    # Preflight every destination before writing anything. Never follow a link
    # outside the project, replace an edited artifact, or extract tar metadata.
    missing = []
    for name, data in payload.items():
        destination = root / name
        resolved = destination.resolve()
        if root not in resolved.parents or destination.is_symlink():
            raise ValueError('Unsafe destination: ' + name)
        if destination.exists():
            if not destination.is_file() or destination.read_bytes() != data:
                raise ValueError('Existing record differs; preserve it and use a fresh checkout: ' + name)
        else:
            missing.append((destination, data))
    if not check_only:
        for destination, data in missing:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as target:
                target.write(data)
    return {'verified_records': len(payload), 'restored_records': 0 if check_only else len(missing)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--pack', action='store_true', help='Maintainer: build from the full local campaign')
    mode.add_argument('--check', action='store_true', help='Verify without restoring missing inputs')
    args = parser.parse_args()
    print(json.dumps(pack(ROOT) if args.pack else restore(ROOT, args.check), indent=2))
