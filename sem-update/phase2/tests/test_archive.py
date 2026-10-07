"""Durable-copy integrity checks on explicitly synthetic software fixtures."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

TOOL=Path(__file__).resolve().parents[1]/'tools/archive_evidence.py'

def fixture(tmp_path):
    payload=b'software verification fixture; not experimental evidence\x00\xff'
    (tmp_path/'trace.bin').write_bytes(payload)
    manifest={'files':[{'path':'trace.bin','bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}],
              'bytes':len(payload)}
    raw=(json.dumps(manifest)+'\n').encode();(tmp_path/'artifact_manifest.json').write_bytes(raw)
    return payload,raw

def execute(tmp_path,command,archive):
    env=dict(os.environ,SEM_UPDATE_ARTIFACT_ROOT=str(tmp_path))
    return subprocess.run([sys.executable,str(TOOL),command,'--archive',str(archive)],
                          env=env,text=True,capture_output=True)

def test_complete_archive_is_verified_without_extraction(tmp_path):
    payload,_=fixture(tmp_path);archive=tmp_path/'evidence.tar.gz'
    assert execute(tmp_path,'create',archive).returncode==0
    result=execute(tmp_path,'verify',archive)
    assert result.returncode==0
    record=json.loads(result.stdout)
    assert record['verified'] and record['files']==1 and record['uncompressed_bytes']==len(payload)

def test_equal_size_corruption_is_rejected(tmp_path):
    payload,manifest=fixture(tmp_path);archive=tmp_path/'corrupt.tar.gz'
    with tarfile.open(archive,'w:gz') as target:
        for name,data in [('artifact_manifest.json',manifest),('trace.bin',b'x'*len(payload))]:
            entry=tarfile.TarInfo(name);entry.size=len(data);target.addfile(entry,io.BytesIO(data))
    result=execute(tmp_path,'verify',archive)
    assert result.returncode!=0
    record=json.loads(result.stdout)
    assert not record['verified'] and record['errors']==['trace.bin']
