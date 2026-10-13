"""Check the staged GoT-war release, optionally write its content manifest.

Run after git add. Limits apply to this project, not other work in the repository.
Uses index blobs so untracked local archives cannot inflate the measured release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {'files': 320, 'bytes': 17 * 512 * 1024, 'single_file_bytes': 2 * 1024 * 1024}
MANIFEST = 'results/artifact_manifest.json'


def git(*args, data=None):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], input=data)


def check(write_manifest=False):
    entries = []
    for row in git('ls-files', '--stage', '-z', '--', '.').split(b'\0'):
        if not row:
            continue
        info, path = row.split(b'\t', 1)
        mode, oid, stage = info.decode().split()
        name = path.decode()
        if stage != '0' or mode not in ('100644', '100755'):
            raise ValueError('Release requires regular, resolved files: ' + name)
        data = git('cat-file', 'blob', oid)
        entries.append((name, len(data), hashlib.sha256(data).hexdigest()))
    if not entries:
        raise ValueError('No staged project files found')
    ignored = git('ls-files', '--cached', '--ignored', '--exclude-standard', '-z', '--', '.')
    failures = ['Ignored file is staged: ' + name.decode() for name in ignored.split(b'\0') if name]
    total = sum(size for _, size, _ in entries)
    if len(entries) > LIMITS['files']:
        failures.append('Too many files: %d' % len(entries))
    if total > LIMITS['bytes']:
        failures.append('Release too large: %d bytes' % total)
    failures += ['File too large: ' + name for name, size, _ in entries if size > LIMITS['single_file_bytes']]
    if failures:
        raise ValueError('\n'.join(failures[:15]) + ('\n... %d additional violations' % (len(failures)-15) if len(failures)>15 else ''))
    if write_manifest:
        manifest = {
            'scope': 'Published Git index content for GoT-war; excludes this self-referential manifest. Original campaign archives remain local.',
            'limits': LIMITS,
            'entry_fields': ['bytes', 'sha256'],
            'files': {name: [size, sha] for name, size, sha in entries if name != MANIFEST},
        }
        (ROOT / MANIFEST).write_text(json.dumps(manifest, separators=(',', ':')) + '\n')
    return {'files': len(entries), 'bytes': total, 'limits': LIMITS, 'passed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest', action='store_true')
    print(json.dumps(check(parser.parse_args().write_manifest), indent=2))
