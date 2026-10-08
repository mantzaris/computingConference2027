"""Bound the existing study process group, including long prediction calls.

This CPU watchdog does not alter scientific configuration or launch GPU work.
It leaves two minutes inside the authorized ceiling for graceful interruption.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import time

PROJECT=Path(__file__).resolve().parents[2]

def remaining(root):
    boundary=json.loads((root/'phase_boundary.json').read_text())
    with sqlite3.connect((root/'ledger.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        intervals=sorted((a,b or time.time()) for a,b in db.execute('SELECT start,end FROM intervals'))
    total=end=0.
    for a,b in intervals:total+=max(0.,b-max(a,end));end=max(end,b)
    return boundary['cumulative_cap_seconds']-total

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase3')).resolve()
    session=json.loads((root/'runs/main_session.json').read_text());pid=session['pid']
    proc=Path('/proc')/str(pid)
    assert session['status']=='running'
    assert b'phase3/tools/execute_main.py' in (proc/'cmdline').read_bytes()
    assert (proc/'cwd').resolve()==PROJECT.resolve() and os.getpgid(pid)==pid
    start=(proc/'stat').read_text().split()[21]
    record={'coordinator_pid':pid,'process_start':start,'protocol_sha256':session['protocol_sha256'],
            'reserve_seconds':120,'remaining_seconds_at_start':remaining(root),'status':'verified' if args.check_only else 'watching'}
    target=root/'runs'/('budget_guard_check.json' if args.check_only else 'budget_guard.json')
    def save():
        temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(target)
    save();print(json.dumps(record),flush=True)
    if args.check_only:return
    while True:
        try:
            os.killpg(pid,0)
            if proc.exists() and (proc/'stat').read_text().split()[21]!=start:
                raise RuntimeError('Coordinator PID reused; refuse to signal unrelated processes')
        except ProcessLookupError:
            record['status']='group_exited';save();return
        left=remaining(root)
        with sqlite3.connect((root/'ledger.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            active=db.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
        if left<=120 and active:
            record.update(status='budget_interruption',remaining_seconds_at_signal=left,signal_epoch=time.time());save()
            os.killpg(pid,signal.SIGINT)
            time.sleep(20)
            try:os.killpg(pid,signal.SIGTERM)
            except ProcessLookupError:pass
            record['status']='budget_stop_sent';save();return
        # A finished coordinator can have an unreaped zombie but no GPU workers.
        state=json.loads((root/'runs/main_session.json').read_text())
        if state['status']!='running':
            if not active:record['status']='study_quiescent';save();return
        time.sleep(5)

if __name__=='__main__':main()
