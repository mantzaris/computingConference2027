"""Phase-three paths, immutable historical records, and cumulative device budget."""
import contextlib
import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import traceback
from sem_update import runtime as legacy

PROJECT=legacy.PROJECT
PHASE=PROJECT/'phase3'
RESULTS=PHASE/'results'
HISTORICAL_COMMIT='8c452ac89e38ebc5e4d04ead60ac93a18ab71baf'
atomic_json=legacy.atomic_json
read_json=legacy.read_json
digest=legacy.digest
file_hash=legacy.file_hash

def compact_json(path,value):
    import uuid
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with open(temporary,'w') as stream:
        json.dump(value,stream,separators=(',',':'),sort_keys=True,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)

def root():
    configured=os.environ.get('SEM_UPDATE_ARTIFACT_ROOT')
    path=Path(configured).resolve() if configured else PROJECT/'.artifacts/phase3'
    if path==PROJECT/'.artifacts':
        path=path/'phase3'
    os.environ['SEM_UPDATE_ARTIFACT_ROOT']=str(path)
    path.mkdir(parents=True,exist_ok=True)
    for name in ('runs','logs','checkpoints','data/processed','data/raw','generated_samples',
                 'archives','model_cache','figures_preview','costs'):
        (path/name).mkdir(parents=True,exist_ok=True)
    RESULTS.mkdir(parents=True,exist_ok=True)
    return path

def setup():
    path=root()
    base=PROJECT/'.artifacts'
    os.environ.setdefault('HF_HOME',str(base/'model_cache/huggingface'))
    os.environ.setdefault('HF_HUB_DISABLE_IMPLICIT_TOKEN','1')
    os.environ.setdefault('HF_HUB_ENABLE_HF_TRANSFER','0')
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    os.environ.setdefault('MPLCONFIGDIR',str(path/'model_cache/matplotlib'))
    os.environ.setdefault('PIP_CACHE_DIR',str(path/'model_cache/pip'))
    (path/'third_party').mkdir(exist_ok=True)
    source=base/'third_party/dcdi'
    link=path/'third_party/dcdi'
    if source.exists() and not link.exists():
        link.symlink_to(source,target_is_directory=True)
    return path

def initialize_ledger():
    path=setup()
    boundary=path/'phase_boundary.json'
    if not boundary.exists():
        old=PROJECT/'.artifacts/phase2/ledger.sqlite'
        if not old.exists():
            old=PROJECT/'.artifacts/phase2/ledger_snapshot.sqlite'
        if not old.exists():
            raise RuntimeError('Verified historical ledger is required; do not reset cumulative use')
        source=sqlite3.connect(old.as_uri()+'?mode=ro',uri=True)
        if source.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]:
            raise RuntimeError('Historical ledger still has running jobs')
        target=sqlite3.connect(path/'ledger.sqlite')
        source.backup(target)
        target.close();source.close()
        ledger=legacy.Ledger(path)
        used=ledger.used_seconds();ledger.db.close()
        atomic_json(boundary,{'historical_gpu_seconds':used,'additional_cap_seconds':24*3600,
            'cumulative_cap_seconds':min(64*3600,used+24*3600),
            'historical_commit':HISTORICAL_COMMIT,'historical_ledger_sha256':file_hash(old),
            'initialized_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'policy':'Historical records copied intact; all new job IDs start phase3-; old ledger unchanged'})
        atomic_json(RESULTS/'phase_boundary.json',read_json(boundary))
    return read_json(boundary)

def ledger():
    boundary=initialize_ledger()
    return legacy.Ledger(root(),cap_hours=boundary['cumulative_cap_seconds']/3600)

def snapshot():
    book=ledger();value=book.snapshot();book.db.close()
    boundary=read_json(root()/'phase_boundary.json')
    return {'historical_gpu_seconds':boundary['historical_gpu_seconds'],
            'phase3_gpu_seconds':value['used_seconds']-boundary['historical_gpu_seconds'],
            'additional_cap_seconds':boundary['additional_cap_seconds'],
            'cumulative_gpu_seconds':value['used_seconds'],
            'cumulative_cap_seconds':value['cap_seconds'],
            'jobs':[r for r in value['jobs'] if r['id'].startswith('phase3-')]}

def prior_attempt_seconds(name):
    with sqlite3.connect(root()/'ledger.sqlite') as book:
        return float(book.execute('SELECT COALESCE(SUM(end-start),0) FROM intervals WHERE job=? AND end IS NOT NULL',
                                  ('phase3-'+name,)).fetchone()[0])

@contextlib.contextmanager
def job(name,identity,estimate=0):
    book=ledger();name='phase3-'+name
    if not book.claim(name,identity,expected_seconds=estimate):
        book.db.close();yield False;return
    try:
        with book.device_interval(name):
            yield True
        book.finish(name)
    except BaseException:
        failure=traceback.format_exc()
        atomic_json(root()/'logs'/('failure-'+digest(name)[:16]+'-'+str(time.time_ns())+'.json'),
                    {'job':name,'identity':identity,'traceback':failure,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        book.finish(name,failure)
        raise
    finally:
        book.db.close()
        atomic_json(root()/'runtime_snapshot.json',snapshot())

def scientific_hash():
    files={p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))
           if p.name not in ('reporting.py','illustrations.py')}
    from sem_update.phase2.runtime import scientific_hash as previous
    files['historical_core_and_phase2']=previous()
    return digest(files)

def require_cuda():
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Real CUDA execution is required; CPU experiment substitution forbidden')
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False

def doctor():
    setup();require_cuda()
    import torch,platform
    with job('doctor',{'purpose':'phase-three actual CUDA and gradient verification'}) as active:
        if not active:return read_json(RESULTS/'hardware.json')
        torch.cuda.reset_peak_memory_stats()
        torch.manual_seed(260207)
        x=torch.randn(256,256,device='cuda',requires_grad=True)
        loss=(x@x.T).square().mean();loss.backward();torch.cuda.synchronize()
        assert x.grad.is_cuda and torch.isfinite(x.grad).all() and x.grad.abs().sum()>0
        report={'python':platform.python_version(),'torch':torch.__version__,
            'cuda_runtime':torch.version.cuda,'device':torch.cuda.get_device_name(),
            'capability':list(torch.cuda.get_device_capability()),'compiled_arches':torch.cuda.get_arch_list(),
            'memory_total_bytes':torch.cuda.get_device_properties(0).total_memory,
            'memory_free_bytes':torch.cuda.mem_get_info()[0],'loss':loss.item(),
            'gradient_norm':x.grad.norm().item(),'gradient_device':str(x.grad.device),
            'nvidia_smi':legacy.command('nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.free','--format=csv,noheader'),
            'mount':legacy.command('findmnt','-T',str(PROJECT),'-n','-o','TARGET,SOURCE,FSTYPE'),
            'storage':legacy.command('df','-B1',str(PROJECT)),
            'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        atomic_json(RESULTS/'hardware.json',report)
        return report

def freeze_guard():
    protocol=read_json(RESULTS/'protocol.json')
    if protocol['scientific_hash']!=scientific_hash():
        raise RuntimeError('Phase-three scientific source changed after protocol freeze')
    return protocol
