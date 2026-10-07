"""Artifact locations, atomic records, compatible resumes and device-hour budget."""
from __future__ import annotations
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import time
import threading
import uuid

PROJECT = Path(__file__).resolve().parents[2]
_GPU_DEADLINE = None

def check_budget():
    if _GPU_DEADLINE is not None and time.monotonic() >= _GPU_DEADLINE:
        raise RuntimeError('GPU runtime ceiling reached; resume requires an explicitly increased allocation')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()

def artifact_root():
    root = Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT') or PROJECT / '.artifacts').resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ('data/raw', 'data/processed', 'runs', 'checkpoints', 'generated_samples',
                 'logs', 'model_cache', 'figures_preview', 'archives'):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root

def configure_caches():
    root = artifact_root()
    for key, name in {'HF_HOME': 'model_cache/huggingface', 'TORCH_HOME': 'model_cache/torch',
                      'XDG_CACHE_HOME': 'model_cache/xdg', 'MPLCONFIGDIR': 'model_cache/matplotlib',
                      'PIP_CACHE_DIR': 'model_cache/pip'}.items():
        os.environ.setdefault(key, str(root / name))
    return root

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with open(temp, 'w') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False, default=str)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def read_json(path):
    return json.loads(Path(path).read_text())

def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()

def source_state():
    commit = command('git', '-C', str(PROJECT), 'rev-parse', 'HEAD')
    files = sorted(p for p in (PROJECT / 'src').rglob('*.py'))
    sources={str(p.relative_to(PROJECT)): file_hash(p) for p in files}
    diff=subprocess.check_output(['git', '-C', str(PROJECT), 'diff', 'HEAD', '--', '.'])
    return {'repository_commit': commit, 'source_hash': digest(sources),
            'dirty_diff_hash':digest({'tracked_diff_sha256':hashlib.sha256(diff).hexdigest(),'source_files_including_untracked':sources})}

def doctor(require_cuda=True):
    import torch
    configure_caches()
    report = {'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'python': platform.python_version(), 'torch': torch.__version__,
              'cuda_runtime': torch.version.cuda, 'cuda_available': torch.cuda.is_available(),
              'packages': {p: importlib.metadata.version(p) for p in ('torch', 'numpy', 'networkx')},
              'storage_mount': command('findmnt', '-T', str(PROJECT), '-n', '-o', 'TARGET,SOURCE,FSTYPE'),
              'disk': command('df', '-B1', str(PROJECT)), **source_state()}
    if require_cuda and not torch.cuda.is_available():
        raise RuntimeError('CUDA required: CPU computation is not a production run')
    if torch.cuda.is_available():
        torch.manual_seed(1026)
        torch.cuda.reset_peak_memory_stats()
        x = torch.randn(256, 256, device='cuda', requires_grad=True)
        loss = (x @ x.T).square().mean()
        loss.backward()
        torch.cuda.synchronize()
        if not torch.isfinite(loss) or not torch.isfinite(x.grad).all() or x.grad.abs().sum() == 0:
            raise RuntimeError('CUDA gradient verification failed')
        properties = torch.cuda.get_device_properties(0)
        report.update(device=properties.name, compute_capability=list(torch.cuda.get_device_capability()),
                      memory_total_bytes=properties.total_memory, memory_free_bytes=torch.cuda.mem_get_info()[0],
                      gradient_device=str(x.grad.device), finite_loss=loss.item(),
                      gradient_norm=x.grad.norm().item(), peak_vram_bytes=torch.cuda.max_memory_allocated(),
                      nvidia_smi=command('nvidia-smi', '--query-gpu=name,uuid,driver_version,memory.total,memory.free', '--format=csv,noheader'),
                      compiled_cuda_arches=torch.cuda.get_arch_list())
    atomic_json(PROJECT / 'results/curated/hardware.json', report)
    return report

class Ledger:
    """SQLite stores job/interval history; intervals are unioned, not summed."""
    def __init__(self, root=None, cap_hours=64):
        self.root = Path(root or artifact_root())
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'ledger.sqlite', timeout=60)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, config TEXT, status TEXT, attempts INTEGER, error TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS intervals (token TEXT PRIMARY KEY, job TEXT, start REAL, end REAL)')
        if 'owner' not in [r[1] for r in self.db.execute('PRAGMA table_info(jobs)')]:
            self.db.execute('ALTER TABLE jobs ADD COLUMN owner TEXT')
        if 'heartbeat' not in [r[1] for r in self.db.execute('PRAGMA table_info(intervals)')]:
            self.db.execute('ALTER TABLE intervals ADD COLUMN heartbeat REAL')
        for job,owner in list(self.db.execute("SELECT id,owner FROM jobs WHERE status='running' AND owner IS NOT NULL")):
            if not self.owner_alive(owner):
                self.db.execute('UPDATE intervals SET end=MIN(?,COALESCE(heartbeat,start)+10) WHERE job=? AND end IS NULL',(time.time(),job))
                self.db.execute('UPDATE jobs SET status=?,error=? WHERE id=?',('failed','owner exited; recovered on ledger open; checkpoints retained',job))
        self.db.commit()
        self.cap_seconds = cap_hours * 3600

    def used_seconds(self):
        intervals = sorted((a, b or time.time()) for a, b in self.db.execute('SELECT start,end FROM intervals'))
        total, end = 0., 0.
        for a, b in intervals:
            total += max(0., b - max(a, end))
            end = max(end, b)
        return total

    def claim(self, job_id, config, expected_seconds=0):
        key = digest(config)
        row = self.db.execute('SELECT config,status,attempts,owner FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row:
            if row[0] != key:
                raise ValueError('incompatible resume configuration for ' + job_id)
            if row[1] == 'complete':
                return False
            if row[1] == 'running':
                if row[3] is None or self.owner_alive(row[3]):
                    raise RuntimeError('job already running; cannot claim: ' + job_id)
                # A dead owner is an interrupted compatible task. Bound its last
                # reserved interval by the last 10-second heartbeat, retaining it.
                self.db.execute('UPDATE intervals SET end=MIN(?,COALESCE(heartbeat,start)+10) WHERE job=? AND end IS NULL',(time.time(),job_id))
                self.db.execute('UPDATE jobs SET status=?,error=? WHERE id=?',('failed','owner exited; resumed from atomic checkpoint',job_id))
                self.db.commit()
            if row[2] >= 3:
                raise RuntimeError('initial attempt plus two retries exhausted: ' + job_id)
        if self.used_seconds() + expected_seconds > self.cap_seconds:
            raise RuntimeError('GPU runtime ceiling would be exceeded')
        owner=str(os.getpid())+':'+Path('/proc/self/stat').read_text().split()[21]
        self.db.execute('INSERT OR REPLACE INTO jobs (id,config,status,attempts,error,owner) VALUES (?,?,?,?,?,?)', (job_id, key, 'running', (row[2] if row else 0)+1, None,owner))
        self.db.commit()
        return True

    @staticmethod
    def owner_alive(owner):
        pid,start=owner.split(':')
        try:
            stat=Path('/proc')/pid/'stat'
            values=stat.read_text().split()
            return values[21]==start and values[2]!='Z'
        except (FileNotFoundError,PermissionError):
            return False

    def finish(self, job_id, error=None):
        self.db.execute('UPDATE jobs SET status=?,error=? WHERE id=?', ('failed' if error else 'complete', error, job_id))
        self.db.commit()

    @contextlib.contextmanager
    def device_interval(self, job_id):
        global _GPU_DEADLINE
        previous_deadline=_GPU_DEADLINE
        # Leave a small checkpoint/cleanup margin inside the hard ceiling.
        deadline=time.monotonic()+max(0.,self.cap_seconds-self.used_seconds()-30)
        _GPU_DEADLINE=min(deadline,previous_deadline) if previous_deadline is not None else deadline
        token = uuid.uuid4().hex
        started=time.time()
        self.db.execute('INSERT INTO intervals (token,job,start,end,heartbeat) VALUES (?,?,?,NULL,?)', (token, job_id, started,started))
        self.db.commit()
        stop=threading.Event()
        def heartbeat():
            db=sqlite3.connect(self.root/'ledger.sqlite',timeout=60)
            while not stop.wait(10):
                now=time.time()
                db.execute('UPDATE intervals SET heartbeat=? WHERE token=?',(now,token))
                db.commit()
                try:
                    sample=command('nvidia-smi','--query-gpu=utilization.gpu,memory.used,power.draw','--format=csv,noheader,nounits')
                    path=self.root/'logs/gpu_utilization.csv'
                    path.parent.mkdir(exist_ok=True,parents=True)
                    with open(path,'a') as f:
                        f.write(f'{now},{job_id},{sample}\n')
                except (OSError,subprocess.SubprocessError):
                    pass
            db.close()
        worker=threading.Thread(target=heartbeat,daemon=True)
        worker.start()
        try:
            yield
        finally:
            _GPU_DEADLINE=previous_deadline
            stop.set()
            worker.join(timeout=1)
            self.db.execute('UPDATE intervals SET end=? WHERE token=?', (time.time(), token))
            self.db.commit()

    def snapshot(self):
        return {'cap_seconds': self.cap_seconds, 'used_seconds': self.used_seconds(),
                'jobs': [dict(zip(('id','config_hash','status','attempts','error'), row)) for row in self.db.execute('SELECT id,config,status,attempts,error FROM jobs')]}

def verify_artifacts(root=None):
    root = Path(root or artifact_root())
    # Model downloads and install caches are separately revision pinned; preserve run evidence.
    entries = []
    for directory in ('data', 'runs', 'checkpoints', 'generated_samples', 'logs', 'archives','figures_preview','third_party'):
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and not path.name.endswith('.tmp'):
                entries.append({'path': str(path.relative_to(root)), 'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    snapshot=root/'ledger_snapshot.sqlite'
    if snapshot.exists():
        entries.append({'path':snapshot.name,'bytes':snapshot.stat().st_size,'sha256':file_hash(snapshot)})
    manifest = {'root_policy': 'SEM_UPDATE_ARTIFACT_ROOT or project-local .artifacts', 'files': entries}
    atomic_json(root / 'artifact_manifest.json', manifest)
    return {'files': len(entries), 'bytes': sum(e['bytes'] for e in entries), 'manifest_sha256': file_hash(root / 'artifact_manifest.json')}
