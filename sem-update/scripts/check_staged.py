#!/usr/bin/env python3
"""Validate actual staged blobs; never modify the user's index or data."""
import argparse
import json
import re
import subprocess
from pathlib import Path

BLOCKED_PARTS = {'.artifacts', '.venv', '__pycache__', 'raw', 'processed',
                 'checkpoints', 'model_cache', 'generated_samples', 'logs',
                 'runs', 'wandb', 'tensorboard', 'build'}
BLOCKED_SUFFIX = {'.pt', '.pth', '.ckpt', '.safetensors', '.npy', '.npz',
                  '.h5', '.hdf5', '.parquet', '.log'}

def git(*args):
    return subprocess.check_output(['git', *args])

def check(base=None):
    args=['diff','--cached','--name-only','--diff-filter=ACMR','-z']
    if base:
        args.append(base)
    entries = git(*args).split(b'\0')
    blobs, errors, unique = [], [], {}
    for name in filter(None, entries):
        path = name.decode()
        if not path.startswith('sem-update/'):
            continue  # Preserve unrelated staging.
        oid = git('rev-parse', ':' + path).decode().strip()
        size = int(git('cat-file', '-s', oid))
        unique[oid] = size
        p = Path(path)
        if set(p.parts) & BLOCKED_PARTS or p.suffix in BLOCKED_SUFFIX:
            errors.append(f'operational artifact: {path}')
        if p.name.startswith('.env') and p.name != '.env.example':
            errors.append(f'environment file: {path}')
        if size > 5 * 1024**2:
            errors.append(f'file exceeds 5 MiB; no exceptions currently declared: {path}')
        data = git('cat-file', 'blob', oid)
        patterns = [rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
                    rb'\b(?:hf_|ghp_)[A-Za-z0-9]{20,}', rb'\bAKIA[0-9A-Z]{16}\b',
                    rb'(?i)[?&](?:X-Amz-Signature|access_token|api_key)=[^\s"\']+']
        if any(re.search(pattern, data) for pattern in patterns):
            errors.append(f'possible credential: {path}')
        if path.startswith('sem-update/data/') and p.name != 'README.md':
            errors.append(f'dataset file: {path}')
        blobs.append({'path': path, 'blob': oid, 'bytes': size})
    total = sum(unique.values())
    if total > 25 * 1024**2:
        errors.append('aggregate staged project blobs exceed 25 MiB')
    return {'comparison_base':base or 'HEAD','files': blobs, 'total_unique_blob_bytes': total,
            'largest_blob_bytes': max(unique.values(), default=0), 'errors': errors,
            'limits': {'file_bytes': 5 * 1024**2, 'batch_bytes': 25 * 1024**2}}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output')
    parser.add_argument('--base',help='audit the entire submission against its initial commit, across intermediate commits')
    args = parser.parse_args()
    result = check(args.base)
    content = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(content + '\n')
    print(content)
    raise SystemExit(bool(result['errors']))
