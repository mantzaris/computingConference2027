"""Persistent absolute deadline and process-identity-scoped supervision."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def process_birth(pid):
    try:
        # comm may contain spaces; fields after the last ')' start at field 3.
        return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


class Budget:
    def __init__(self, root, config_name='budget.json'):
        self.root = Path(root).resolve()
        self.config = json.loads((self.root / 'configs' / config_name).read_text())
        self.run = self.root / 'runs' / self.config['campaign_id']
        self.run.mkdir(parents=True, exist_ok=True)
        self.stop_marker = self.root / 'runs/STOP' if config_name == 'budget.json' else self.run / 'STOP'

    def remaining(self):
        return (datetime.fromisoformat(self.config['hard_deadline']) - utcnow()).total_seconds()

    def check(self, heavy=False, estimated_seconds=0, reserve_seconds=0):
        if heavy and (self.run / 'COMPLETE').exists():
            raise RuntimeError('Campaign complete; a new inference campaign needs a separately authorized budget')
        if self.stop_marker.exists():
            raise RuntimeError('Project stop marker present')
        if self.remaining() <= estimated_seconds + reserve_seconds:
            raise RuntimeError('Persisted deadline/reserve would be exceeded')
        if heavy and utcnow() >= datetime.fromisoformat(self.config['no_heavy_jobs_after']):
            raise RuntimeError('No heavy jobs after hour 20')

    def launch(self, command, label):
        self.check(heavy=True)
        log = open(self.run / (label + '.log'), 'ab', buffering=0)
        proc = subprocess.Popen(command, cwd=str(self.root), stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        # Never register an unidentifiable process as controllable. A short-lived
        # process or a transient /proc read failure needs an explicit outcome.
        birth = None
        limit = time.monotonic() + 1.0
        while time.monotonic() < limit and proc.poll() is None:
            birth = process_birth(proc.pid)
            try:
                pgid = os.getpgid(proc.pid)
            except ProcessLookupError:
                birth = None
                break
            if birth is not None and pgid == proc.pid:
                break
            birth = None
            time.sleep(.01)
        if birth is None:
            # This Popen instance is our direct child. Do not signal an
            # unverified process group or leave a null identity in the registry.
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=2)
            log.close()
            raise RuntimeError('Launch failed: process identity could not be verified for ' + label)
        item = {'label': label, 'pid': proc.pid, 'pgid': pgid,
                'birth': birth, 'started_at': utcnow().isoformat(), 'command': command}
        registry = self.run / 'processes.json'
        with open(self.run / 'processes.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            items = json.loads(registry.read_text()) if registry.exists() else []
            items.append(item)
            atomic_json(registry, items)
        log.close()
        return item

    def stop_owned(self, sig=signal.SIGTERM, labels=None):
        registry = self.run / 'processes.json'
        stopped = []
        for entry in json.loads(registry.read_text()) if registry.exists() else []:
            if labels is not None and entry['label'] not in labels:
                continue
            pid = entry['pid']
            # Never kill an unverified/reused pid or another session's group.
            if entry['birth'] is not None and process_birth(pid) == entry['birth']:
                try:
                    if os.getpgid(pid) == entry['pgid'] == pid and pid != os.getpid():
                        os.killpg(pid, sig)
                        stopped.append(entry['label'])
                except ProcessLookupError:
                    pass
        return stopped

    def watchdog(self):
        last_sample = 0
        softened = False
        while True:
            remaining = self.remaining()
            atomic_json(self.run / 'heartbeat.json', {
                'utc': utcnow().isoformat(), 'remaining_seconds': remaining,
                'watchdog_pid': os.getpid(), 'watchdog_birth': process_birth(os.getpid()),
                'hard_deadline': self.config['hard_deadline'], 'state': 'monitoring'})
            if (self.run / 'COMPLETE').exists():
                self.stop_owned()
                atomic_json(self.run / 'watchdog_final.json', {'state':'completed', 'at':utcnow().isoformat()})
                return
            if remaining <= 0:
                stopped = self.stop_owned(signal.SIGKILL)
                atomic_json(self.run / 'watchdog_final.json', {'state':'hard_deadline', 'stopped':stopped, 'at':utcnow().isoformat()})
                return
            if not softened and utcnow() >= datetime.fromisoformat(self.config['soft_deadline']):
                self.stop_marker.touch()
                stopped = self.stop_owned()
                atomic_json(self.run / 'soft_stop.json', {'at':utcnow().isoformat(),'stopped':stopped})
                softened = True
            if time.monotonic() - last_sample > 60:
                try:
                    result = subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,power.draw','--format=csv,noheader,nounits'], timeout=10).decode().strip()
                    with open(self.run / 'gpu_samples.jsonl', 'a') as f:
                        f.write(json.dumps({'at':utcnow().isoformat(),'sample':result})+'\n')
                except (OSError, subprocess.SubprocessError):
                    pass
                last_sample = time.monotonic()
            time.sleep(min(15, max(.1, remaining)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--config', default='budget.json')
    parser.add_argument('action', choices=['watchdog','launch','status','stop'])
    parser.add_argument('--label', default='job')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    b = Budget(args.root, args.config)
    if args.action == 'watchdog': b.watchdog()
    elif args.action == 'status': print(json.dumps({'remaining_seconds':b.remaining(), **b.config},indent=2))
    elif args.action == 'stop': print(b.stop_owned())
    else:
        cmd = args.command[1:] if args.command and args.command[0] == '--' else args.command
        print(json.dumps(b.launch(cmd,args.label)))


if __name__ == '__main__':
    main()
