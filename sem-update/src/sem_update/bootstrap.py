"""Public, revision-pinned dependencies for the existing execution machine."""
from pathlib import Path
import os
import subprocess
from .runtime import artifact_root,configure_caches,PROJECT,atomic_json,read_json,command,file_hash

MODEL='Qwen/Qwen3-8B'
MODEL_REVISION='b968826d9c46dd6066d109eabc6255188de91218'

def prepare_models():
    configure_caches()
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
    os.environ['HF_HUB_ENABLE_HF_TRANSFER']='0'
    from .dcdi import REVISION
    source=artifact_root()/'third_party/dcdi'
    if not source.exists():
        source.parent.mkdir(exist_ok=True,parents=True)
        subprocess.run(['git','clone','https://github.com/slachapelle/dcdi',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'checkout','--detach',REVISION],check=True)
    if command('git','-C',str(source),'rev-parse','HEAD')!=REVISION:
        raise ValueError('existing DCDI checkout has another revision; preserve and investigate it')
    from huggingface_hub import snapshot_download
    snapshot=Path(snapshot_download(MODEL,revision=MODEL_REVISION,token=False))
    license_path=snapshot/'LICENSE'
    if not license_path.exists() or 'Apache License' not in license_path.read_text():
        raise RuntimeError('pinned model license could not be verified')
    revision={'model':MODEL,'revision':MODEL_REVISION,'license':'apache-2.0',
              'precision':'bfloat16','device':'cuda'}
    path=PROJECT/'results/curated/llm_revision.json'
    if path.exists() and read_json(path)!=revision:
        raise ValueError('model identity differs from existing project provenance')
    atomic_json(path,revision)
    report={'dcdi_commit':REVISION,'model':revision,'license_sha256':file_hash(license_path),
            'downloaded_file_bytes':{p.name:p.stat().st_size for p in snapshot.iterdir() if p.is_file()},
            'credentials':'public downloads with implicit token use disabled',
            'download_is_not_gpu_validation':True}
    atomic_json(PROJECT/'results/curated/prepared_models.json',report)
    return report
