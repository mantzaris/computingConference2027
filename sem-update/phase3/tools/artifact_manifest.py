#!/usr/bin/env python3
"""Inventory immutable evidence and snapshot SQLite; never delete artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

def sha(path):
    value=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):value.update(block)
    return value.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parents[2]
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',project/'.artifacts/phase3')).resolve()
    target=root/'artifact_manifest.json'
    if args.verify:
        record=json.loads(target.read_text());errors=[]
        for row in record['files']:
            path=root/row['path']
            if not path.exists() or path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
                errors.append(row['path'])
        print(json.dumps({'verified_files':len(record['files']),'bytes':record['bytes'],'errors':errors},indent=2))
        raise SystemExit(bool(errors))
    source=sqlite3.connect((root/'ledger.sqlite').as_uri()+'?mode=ro',uri=True)
    active=source.execute("SELECT id FROM jobs WHERE status='running'").fetchall()
    if active:raise RuntimeError('Final durable inventory requires quiescent jobs: '+str(active))
    backup=sqlite3.connect(root/'ledger_snapshot.sqlite');source.backup(backup);backup.close();source.close()
    files=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if path.is_symlink() or not path.is_file():continue
        # Clean plotting checks also create nested, reacquirable caches.
        if any(part in ('third_party','model_cache','__pycache__') for part in relative.parts):continue
        if str(relative)=='archives/durable-evidence.tar.gz':continue
        if path.name in ('artifact_manifest.json','ledger.sqlite','ledger.sqlite-wal','ledger.sqlite-shm'):continue
        if path.suffix=='.tmp':continue
        files.append({'path':str(relative),'bytes':path.stat().st_size,'sha256':sha(path)})
    record={'files':files,'bytes':sum(r['bytes'] for r in files),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'scope':'All phase-three experimental evidence, including failed/interrupted attempts, checkpoints, samples and logs; SQLite consistent snapshot',
        'reused_dependencies':{'historical_artifacts':'../ (historical verified inventory retained)',
            'DCDI_revision':'594d328eae7795785e0d1a1138945e28a4fec037',
            'runtime':'../venv; locked dependencies and installed environment recorded separately',
            'real_data_and_LLM':'No new real-data or LLM experiment in phase three; earlier evidence remains in its historical archive'},
        'excluded_reproducible_caches':['model_cache','third_party','__pycache__ (including nested validation caches)'],
        'excluded_consolidated_copy':'archives/durable-evidence.tar.gz (contains the inventoried evidence)',
        'pod_storage':'overlay, not independently verified persistent volume'}
    target.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'files':len(files),'bytes':record['bytes'],'manifest_sha256':sha(target)},indent=2))

if __name__=='__main__':main()
