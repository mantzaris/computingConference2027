"""Inventory quiescent evidence and preserve a consistent ledger/source snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

PHASE=Path(__file__).resolve().parents[1];PROJECT=PHASE.parent
ROOT=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase4_real_application')).resolve()

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for b in iter(lambda:stream.read(2**20),b''):h.update(b)
    return h.hexdigest()

def main():
    source=sqlite3.connect((ROOT/'ledger.sqlite').as_uri()+'?mode=ro',uri=True)
    if source.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]:
        raise RuntimeError('Evidence inventory requires all jobs to finish')
    backup=sqlite3.connect(ROOT/'ledger_snapshot.sqlite');source.backup(backup);backup.close();source.close()
    snapshot=ROOT/'source_snapshot';snapshot.mkdir(exist_ok=True)
    for folder in [PHASE,PROJECT/'src',PROJECT/'tests',PROJECT/'phase2/tests',PROJECT/'phase3/tests']:
        for path in folder.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or '.pytest_cache' in path.parts:continue
            dest=snapshot/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    shutil.copyfile(PROJECT/'requirements.lock',snapshot/'requirements.lock')
    (snapshot/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    dcdi=PROJECT/'.artifacts/third_party/dcdi'
    shutil.copytree(dcdi/'dcdi',snapshot/'pinned_dcdi',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('LICENSE','LICENSE.txt'):
        if (dcdi/name).exists():shutil.copyfile(dcdi/name,snapshot/('DCDI_'+name))
    files=[]
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink():continue
        if any(p in ('archives','third_party','model_cache','__pycache__') for p in rel.parts):continue
        if path.name in ('artifact_manifest.json','ledger.sqlite','ledger.sqlite-wal','ledger.sqlite-shm'):continue
        if path.suffix=='.tmp':continue
        files.append({'path':str(rel),'bytes':path.stat().st_size,'sha256':sha(path)})
    record={'files':files,'bytes':sum(f['bytes'] for f in files),
        'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'scope':'Phase-four recorded data, protocols, development evidence, every fitting attempt, checkpoint, sample, bootstrap, log, final graphic and source/environment snapshot; consistent SQLite backup',
        'reused_dependencies':{'DCDI_revision':'594d328eae7795785e0d1a1138945e28a4fec037',
            'Qwen3-8B_revision':'b968826d9c46dd6066d109eabc6255188de91218',
            'model_cache':'../model_cache/huggingface; pinned public weights, not duplicated in this archive',
            'DCDI_source':'source_snapshot/pinned_dcdi; actual imported package also preserved',
            'historical_evidence':'Earlier verified archives remain preserved unchanged'},
        'excluded_reproducible_caches':['model_cache','third_party','__pycache__'],
        'excluded_consolidated_copy':'archives/',
        'pod_storage':'overlay; local checksum-verified durable copy required'}
    target=ROOT/'artifact_manifest.json';target.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'files':len(files),'bytes':record['bytes'],'manifest_sha256':sha(target)}))

if __name__=='__main__':main()
