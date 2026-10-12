"""Capture local serving counters without exposing connection details."""
import json,re,time
from pathlib import Path
import requests
root=Path.cwd();config=json.loads((root/'configs/budget.json').read_text());run=root/'runs'/config['campaign_id']
r=requests.get('http://127.0.0.1:8765/metrics',timeout=15);r.raise_for_status()
lines=[line for line in r.text.splitlines() if not line.startswith('#') and any(x in line for x in ['generation_tokens_total','prompt_tokens_total','request_prefill_time_seconds_sum','request_prefill_time_seconds_count','request_decode_time_seconds_sum','request_decode_time_seconds_count','request_success_total','time_to_first_token_seconds_sum','time_to_first_token_seconds_count','num_requests_running','num_requests_waiting'])]
(run/'service_counters.prom').write_text('\n'.join(lines)+'\n')
values={}
for line in lines:
 name=line.split('{',1)[0].split(' ',1)[0]
 try:values[name]=values.get(name,0)+float(line.rsplit(' ',1)[1])
 except ValueError:pass
(run/'service_counters.json').write_text(json.dumps({'collected_epoch':time.time(),'values':values,'scope':'Only this project-created GPU service; cumulative counters include aborted requests where exported.'},indent=2)+'\n')
print(json.dumps(values,indent=2))
