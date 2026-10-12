"""Version-2 resource accounting; counters are read from the existing service."""
import argparse
import collections
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.budget import atomic_json


def capture(run):
    import requests
    response=requests.get('http://127.0.0.1:8765/metrics',timeout=15)
    response.raise_for_status()
    wanted=('generation_tokens_total','prompt_tokens_total','request_prefill_time_seconds_sum',
            'request_prefill_time_seconds_count','request_decode_time_seconds_sum',
            'request_decode_time_seconds_count','request_success_total',
            'time_to_first_token_seconds_sum','time_to_first_token_seconds_count',
            'num_requests_running','num_requests_waiting')
    lines=[line for line in response.text.splitlines() if not line.startswith('#') and any(k in line for k in wanted)]
    values=collections.defaultdict(float)
    for line in lines:
        name=line.split('{',1)[0].split(' ',1)[0]
        values[name]+=float(line.rsplit(' ',1)[1])
    record={'collected_at':datetime.now(timezone.utc).isoformat(),'values':dict(values),
            'scope':'Only the version-2 project-created server; cumulative counters include aborted generation where exported.'}
    atomic_json(run/'service_counters.json',record)
    (run/'service_counters.prom').write_text('\n'.join(lines)+'\n')
    return record


def summarize(root=ROOT):
    config=json.loads((root/'configs/budget_v2.json').read_text());run=root/'runs'/config['campaign_id']
    ledger=run/'requests.jsonl'
    if not ledger.exists():ledger=run/'usage_ledger.jsonl'
    logs=[json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    roles=collections.defaultdict(lambda:{'requests':0,'request_seconds':0.,'input_tokens':0,'output_tokens':0,'request_errors':0})
    for row in logs:
        item=roles[row['role']];item['requests']+=1
        item['request_seconds']+=row.get('elapsed_seconds',0) or 0
        for key in ('input_tokens','output_tokens'):item[key]+=row.get(key,0) or 0
        item['request_errors']+=bool(row.get('error'))
    for role,item in roles.items():
        rates=[r['decode_tokens_per_second'] for r in logs if r['role']==role and r.get('decode_tokens_per_second')]
        item['median_decode_tokens_per_second']=statistics.median(rates) if rates else None
    samples=[]
    for line in (run/'gpu_samples.jsonl').read_text().splitlines():
        row=json.loads(line)
        try:
            memory,util,power=[float(x.strip()) for x in row['sample'].split(',')]
            samples.append((datetime.fromisoformat(row['at']).timestamp(),memory,util,power))
        except (ValueError,KeyError):continue
    weighted_hours=0.;sampled_resident_hours=0.;covered_seconds=0.
    for a,b in zip(samples,samples[1:]):
        dt=max(0,min(120,b[0]-a[0]));covered_seconds+=dt
        weighted_hours+=dt*(a[2]+b[2])/200/3600
        sampled_resident_hours+=dt*((a[1]>1024)+(b[1]>1024))/2/3600
    completion=run/'completion.json'
    ended=json.loads(completion.read_text())['finished_at'] if completion.exists() else datetime.now(timezone.utc).isoformat()
    end=datetime.fromisoformat(ended);start=datetime.fromisoformat(config['started_at'])
    counters=json.loads((run/'service_counters.json').read_text()) if (run/'service_counters.json').exists() else None
    record={'campaign_id':config['campaign_id'],'started_at':config['started_at'],'measured_through':ended,
        'final':completion.exists(),'elapsed_hours':(end-start).total_seconds()/3600,
        'deadline':config['hard_deadline'],'within_deadline':end<=datetime.fromisoformat(config['hard_deadline']),
        'output_token_ceiling':config['output_token_ceiling'],'requests':len(logs),
        'input_tokens':sum(x['input_tokens'] for x in roles.values()),
        'output_tokens_from_response_usage':sum(x['output_tokens'] for x in roles.values()),
        'output_tokens_from_server':counters['values'].get('vllm:generation_tokens_total') if counters else None,
        'sum_request_hours':sum(x['request_seconds'] for x in roles.values())/3600,
        'request_errors':sum(x['request_errors'] for x in roles.values()),
        'request_time_caveat':'Concurrent request durations overlap; their sum is not elapsed GPU time. Response usage can omit interrupted streams; the dedicated server counter is preferred when present.',
        'gpu_samples':len(samples),'sampled_seconds_covered':covered_seconds,
        'sampled_resident_hours_above_1gib':sampled_resident_hours,
        'sampled_utilization_weighted_gpu_hours':weighted_hours,
        'peak_sampled_vram_mib':max((s[1] for s in samples),default=None),
        'sampling_caveat':'Approximate trapezoidal integration of minute-scale nvidia-smi samples, with gaps capped at 120 seconds. This is neither billed GPU time nor exact kernel timing.',
        'billing_cost':None,'billing_note':'No price or billing modification is inferred or performed.',
        'roles':dict(roles),'server_counters':counters}
    atomic_json(root/'results/v2/usage.json',record)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-server',action='store_true')
    args=parser.parse_args();config=json.loads((ROOT/'configs/budget_v2.json').read_text())
    if args.capture_server:capture(ROOT/'runs'/config['campaign_id'])
    result=summarize()
    print(json.dumps({k:result[k] for k in ('final','elapsed_hours','requests','output_tokens_from_response_usage',
          'output_tokens_from_server','sampled_utilization_weighted_gpu_hours','peak_sampled_vram_mib')},indent=2))
