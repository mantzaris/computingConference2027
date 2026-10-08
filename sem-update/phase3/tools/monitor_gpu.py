"""Read-only device telemetry; raw samples stay in the ignored evidence tree."""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stop-file',required=True,type=Path)
    parser.add_argument('--interval',type=float,default=15);args=parser.parse_args()
    project=Path(__file__).resolve().parents[2]
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',project/'.artifacts/phase3'))
    path=root/'logs/device_telemetry.csv';path.parent.mkdir(parents=True,exist_ok=True)
    existed=path.exists()
    updated=0.
    with path.open('a') as stream:
        writer=csv.writer(stream)
        if not existed:writer.writerow(['utc','epoch','uuid','used_mib','total_mib','gpu_percent','memory_percent','power_w'])
        while not args.stop_file.exists():
            result=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw',
                '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True)
            now=datetime.datetime.now(datetime.timezone.utc).isoformat()
            for row in csv.reader(result.stdout.splitlines()):writer.writerow([now,time.time(),*[v.strip() for v in row]])
            if time.time()-updated>=60:
                value=json.loads(subprocess.check_output([sys.executable,str(project/'phase3/tools/status.py')],text=True))
                text=['# Phase-three live status','',f'Updated: {now}.','',
                    f"Completed primary SCMs: {value['completed_primary_scms']}; primary settings: {value['completed_primary_settings']}; sensitivity datasets: {value['completed_sensitivity_datasets']}.",
                    f"Phase-three device use: {value['phase3_device_hours']:.4f} h; remaining authorized phase allocation: {value['additional_hours_remaining']:.4f} h.",
                    f"Historical device use remains {value['historical_device_hours']:.8f} h. Final outcomes opened: {value['final_test_opened']}.",'',
                    'Active jobs:','',*[f'- {j}' for j in value['active_jobs']],'',
                    'Status records and complete logs are in `.artifacts/phase3/runs/main_session.json` and `.artifacts/phase3/logs/main.log`.',
                    'Frozen seeds, ceilings and pilot-derived estimates are in `results/protocol.json`. Fitting stops with a reserved final-evaluation allowance; no resources are provisioned.',
                    '',f"Failed job records (retained): {len(value['failed_jobs'])}. Retried jobs: {len(value['retried_jobs'])}.",'',
                    'From the existing Pod checkout, resume only after the listed worker processes have exited:', '', '```bash',
                    'cd /workspace/computingConference2027/sem-update','export PYTHONPATH=src',
                    'export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts/phase3"',
                    '.artifacts/venv/bin/python phase3/tools/status.py',
                    '.artifacts/venv/bin/python -u phase3/tools/execute_main.py','```','',
                    'All historical results remain unchanged. Source and artifacts stay under sem-update/. No push, submission, paid provisioning or Pod termination is authorized.',
                    'Remote /workspace is overlay. Final durable preservation to the local ext4 checkout is pending.']
                target=project/'phase3/docs/status.md';temporary=target.with_suffix('.tmp');temporary.write_text('\n'.join(text)+'\n');temporary.replace(target)
                updated=time.time()
            stream.flush();time.sleep(args.interval)
        stream.flush();os.fsync(stream.fileno())

if __name__=='__main__':main()
