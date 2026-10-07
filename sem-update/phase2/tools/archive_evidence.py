#!/usr/bin/env python3
"""Build/verify a durable evidence archive without extracting a second copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import time
import subprocess

def sha(path):
    value=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):value.update(block)
    return value.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['create','verify'])
    parser.add_argument('--archive',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    project=Path(__file__).resolve().parents[2]
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',project/'.artifacts/phase2')).resolve()
    archive=args.archive or root/'archives/durable-evidence.tar.gz'
    if args.command=='create':
        record=json.loads((root/'artifact_manifest.json').read_text())
        if archive.exists():raise RuntimeError('Archive already exists; verify it before deciding whether a replacement is necessary')
        archive.parent.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive,'w:gz',compresslevel=4) as target:
            target.add(root/'artifact_manifest.json',arcname='artifact_manifest.json',recursive=False)
            for row in record['files']:
                source=root/row['path']
                if source.stat().st_size!=row['bytes'] or sha(source)!=row['sha256']:
                    raise RuntimeError('Evidence changed since inventory: '+row['path'])
                target.add(source,arcname=row['path'],recursive=False)
        print(json.dumps({'archive':str(archive),'archive_bytes':archive.stat().st_size,'sha256':sha(archive)},indent=2))
        return
    seen=set();errors=[];record=None;manifest_hash=None
    with tarfile.open(archive,'r|gz') as source:
        for member in source:
            if not member.isfile() or member.name.startswith('/') or '..' in Path(member.name).parts:
                raise RuntimeError('Unexpected archive entry: '+member.name)
            stream=source.extractfile(member)
            if member.name=='artifact_manifest.json':
                raw=stream.read();record=json.loads(raw);manifest_hash=hashlib.sha256(raw).hexdigest()
                expected={row['path']:row for row in record['files']};continue
            if record is None:raise RuntimeError('Evidence manifest must be the first entry')
            digest=hashlib.sha256();size=0
            for block in iter(lambda:stream.read(2**20),b''):digest.update(block);size+=len(block)
            row=expected.get(member.name)
            if member.name in seen or row is None or size!=row['bytes'] or digest.hexdigest()!=row['sha256']:
                errors.append(member.name)
            seen.add(member.name)
    if record is None:raise RuntimeError('Missing evidence manifest')
    errors+=sorted(set(expected)-seen)
    try:
        filesystem=subprocess.check_output(['findmnt','-T',str(archive),'-n','-o','TARGET,SOURCE,FSTYPE'],
            text=True,stderr=subprocess.STDOUT,timeout=10).strip()
    except (OSError,subprocess.SubprocessError):filesystem=None
    result={'verified':not errors,'files':len(seen),'uncompressed_bytes':record['bytes'],
        'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
        'artifact_manifest_sha256':manifest_hash,'errors':errors,
        'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'verification':'Every archived evidence file checked against its recorded SHA256 and byte size, without extraction',
        'archive_path':str(archive),'archive_filesystem':filesystem,'pod_termination_authorized':False}
    if args.output:args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(bool(errors))

if __name__=='__main__':main()
