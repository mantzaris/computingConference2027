#!/usr/bin/env python3
"""Continue an authorized suite into guarded evaluation and paper export.

Stops on failure; never chooses replacement seeds, changes the frozen protocol,
or extends the GPU budget. Every scientific phase retains its own CLI guards.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execution-job',required=True)
    args=parser.parse_args()
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts')).resolve()
    database=root/'ledger.sqlite'
    target=PROJECT/'results/curated/continuation_status.json'
    def record(state,**extra):
        value={'state':state,'execution_job':args.execution_job,
               'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**extra}
        temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,indent=2)+'\n')
        temporary.replace(target)
        print(json.dumps(value),flush=True)
    record('waiting_for_complete_selection')
    while True:
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=10) as connection:
            row=connection.execute('SELECT status,owner,error FROM jobs WHERE id=?',
                                   (args.execution_job,)).fetchone()
        if row is None:
            record('blocked',reason='named suite job does not exist');return 2
        status,owner,error=row
        if status=='complete':
            break
        if status=='failed':
            record('blocked',reason='suite failed; inspect preserved error',error=error);return 2
        pid,start=owner.split(':')
        try:
            process=(Path('/proc')/pid/'stat').read_text().split()
            alive=process[21]==start and process[2]!='Z'
        except FileNotFoundError:
            alive=False
        if not alive:
            record('blocked',reason='suite owner exited without a completion record');return 2
        time.sleep(15)
    for phase,arguments in [('evaluate',['--frozen-manifest','results/curated/frozen_selections.json']),
                            ('export-paper',[])]:
        record('running_'+phase)
        command=[sys.executable,'-u','-m','sem_update.cli',phase,*arguments]
        log=root/'logs'/('continuation-'+phase+'.log')
        with open(log,'a') as output:
            status=subprocess.call(command,cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT)
        if status:
            record('blocked',reason=phase+' failed; exact compatible resume required',
                   exit_code=status,log=str(log.relative_to(root)));return status
    record('evaluation_and_export_complete',remaining='human review, figure inspection, durable mirror and Git size audit')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
