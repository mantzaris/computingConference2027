"""Reproducibility inventory with no credentials, hostnames, or public endpoint details."""
import hashlib,importlib.metadata as metadata,json,platform,subprocess,time
from pathlib import Path
from .budget import Budget,atomic_json


def collect(root):
    root=Path(root);b=Budget(root);packages={}
    for name in ('torch','vllm','transformers','tokenizers','huggingface-hub','numpy','networkx','pydantic','requests','matplotlib','xgrammar'):
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]=None
    try:gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],timeout=10).decode().strip()
    except (OSError,subprocess.SubprocessError):gpu=None
    cfg=json.loads((root/'configs/models.json').read_text()) if (root/'configs/models.json').exists() else {}
    token_files={}
    cache=root/'.cache/huggingface/hub'
    for pattern in ('**/snapshots/*/tokenizer_config.json','**/snapshots/*/config.json','**/snapshots/*/generation_config.json'):
        for file in cache.glob(pattern):token_files[str(file.relative_to(cache))]=hashlib.sha256(file.read_bytes()).hexdigest()
    report={'campaign':b.config,'python':platform.python_version(),'system':platform.system(),'machine':platform.machine(),'packages':packages,'gpu':gpu,'model':cfg,'tokenizer_and_config_hashes':token_files,'endpoint_scope':'project-created loopback service; private connection details excluded','collected_epoch':time.time()}
    atomic_json(b.run/'environment.json',report)
    return report
