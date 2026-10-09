"""Isolated phase-four provenance and a non-resetting device-hour ledger."""
import contextlib
import os
from pathlib import Path
import sqlite3
import time
import traceback
from sem_update import runtime as old

PROJECT = old.PROJECT
PHASE = PROJECT / 'phase4_real_application'
RESULTS = PHASE / 'results'
ROOT = Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT', PROJECT / '.artifacts/phase4_real_application')).resolve()
os.environ['SEM_UPDATE_ARTIFACT_ROOT'] = str(ROOT)
os.environ.setdefault('HF_HOME', str(PROJECT / '.artifacts/model_cache/huggingface'))
os.environ.setdefault('HF_HUB_DISABLE_IMPLICIT_TOKEN', '1')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'model_cache/matplotlib'))
atomic_json, read_json, digest, file_hash = old.atomic_json, old.read_json, old.digest, old.file_hash

def setup():
    old.configure_caches()
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name in ('raw', 'protocols', 'third_party', 'figures', 'reports'):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    link = ROOT / 'third_party/dcdi'
    if not link.exists():
        link.symlink_to(PROJECT / '.artifacts/third_party/dcdi', target_is_directory=True)
    boundary = ROOT / 'phase_boundary.json'
    if not boundary.exists():
        previous = PROJECT / '.artifacts/phase3/ledger.sqlite'
        src = sqlite3.connect(previous.as_uri() + '?mode=ro', uri=True)
        if src.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]:
            raise RuntimeError('Historical jobs remain active')
        dst = sqlite3.connect(ROOT / 'ledger.sqlite'); src.backup(dst); dst.close(); src.close()
        book = old.Ledger(ROOT); used = book.used_seconds(); book.db.close()
        atomic_json(boundary, {'historical_gpu_seconds': used, 'additional_cap_seconds': 43200,
            'cumulative_cap_seconds': min(64*3600, used+43200), 'historical_commit': 'a17a8f7',
            'historical_ledger_sha256': file_hash(previous), 'initialized_unix': time.time()})
    return read_json(boundary)

def source_hash():
    files = {p.name: file_hash(p) for p in Path(__file__).parent.glob('app_*.py')}
    from sem_update.phase3.runtime import scientific_hash
    files['unchanged_historical_science'] = scientific_hash()
    return digest(files)

def snapshot():
    b = setup(); book = old.Ledger(ROOT, b['cumulative_cap_seconds']/3600)
    v = book.snapshot(); book.db.close()
    return {**b, 'phase4_gpu_seconds': v['used_seconds']-b['historical_gpu_seconds'],
            'cumulative_gpu_seconds': v['used_seconds'],
            'jobs': [r for r in v['jobs'] if r['id'].startswith('phase4-')]}

@contextlib.contextmanager
def job(name, identity):
    b = setup(); book = old.Ledger(ROOT, b['cumulative_cap_seconds']/3600); name = 'phase4-'+name
    if not book.claim(name, identity):
        book.db.close(); yield False; return
    try:
        with book.device_interval(name): yield True
        book.finish(name)
    except BaseException:
        error = traceback.format_exc(); book.finish(name, error)
        atomic_json(ROOT/'logs'/f'failure-{time.time_ns()}.json', {'job': name, 'traceback': error})
        raise
    finally:
        book.db.close(); atomic_json(ROOT/'runtime_snapshot.json', snapshot())

def cuda():
    import torch
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required; no CPU substitution')
    torch.set_num_threads(4); torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False

def doctor():
    import torch, platform
    setup(); cuda()
    with job('doctor', {'purpose': 'actual CUDA gradients'}) as active:
        if active:
            x = torch.randn(128, 128, device='cuda', requires_grad=True)
            loss = (x @ x.T).square().mean(); loss.backward(); torch.cuda.synchronize()
            assert x.grad.is_cuda and torch.isfinite(x.grad).all() and x.grad.norm()>0
            atomic_json(RESULTS/'hardware.json', {'device': torch.cuda.get_device_name(),
                'torch': torch.__version__, 'cuda': torch.version.cuda, 'python': platform.python_version(),
                'memory_bytes': torch.cuda.get_device_properties(0).total_memory,
                'gradient_norm': float(x.grad.norm()), 'gradient_device': str(x.grad.device),
                'nvidia_smi': old.command('nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'),
                'storage': old.command('findmnt', '-T', str(ROOT), '-n', '-o', 'TARGET,SOURCE,FSTYPE')})
    return read_json(RESULTS/'hardware.json')
