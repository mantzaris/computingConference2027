"""Collect diagnostic pointers without treating overlapping reports as trials."""
import hashlib,json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
destination=root/'results/failures.jsonl'
original=run/'observed_failure_log.jsonl'
if not original.exists() and destination.exists():original.write_bytes(destination.read_bytes())
rows=[]
def add(kind,path,error,**fields):
    rows.append({'record_format_version':2,'kind':kind,'source_artifact':str(path.relative_to(root)),
                 'error':str(error),**fields})

if original.exists():
    for index,line in enumerate(original.read_text().splitlines()):
        try:
            value=json.loads(line)
            add('observed_failure',original,value.get('error',''),line=index+1,request_key=value.get('key'),role=value.get('role'))
        except (ValueError,TypeError):add('malformed_log_entry',original,'Could not parse retained raw failure entry',line=index+1)
for index,line in enumerate((run/'requests.jsonl').read_text().splitlines()):
    record=json.loads(line)
    if record.get('error'):add('generation_api_or_json',run/'requests.jsonl',record['error'],line=index+1,request_key=record['key'],role=record['role'])
for file in sorted((run/'benchmark').glob('*.json')):
    record=json.loads(file.read_text())
    for attempt in record.get('attempts',[]):
        if not attempt.get('valid'):add('controlled_validation',file,attempt.get('error',''),case_id=record['id'],seed=record['seed'],attempt=attempt['attempt'])
for file in sorted(run.rglob('*.json')):
    if 'local_snapshots' in file.parts:continue
    is_failure=('_failed_' in file.name or file.name.startswith('failed_alternative_') or file.name in ('failure.json','coverage_review_failure.json'))
    if not is_failure:continue
    try:
        record=json.loads(file.read_text())
        if isinstance(record,dict) and record.get('error'):add('application_validation_or_stage',file,record['error'],attempt=record.get('attempt'),node=record.get('node'))
    except ValueError:add('malformed_artifact',file,'Retained JSON artifact could not be parsed')
seen=set();unique=[]
for row in rows:
    key=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
    if key not in seen:seen.add(key);unique.append(row)
destination.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in unique))
(root/'results/failure_inventory_note.json').write_text(json.dumps({'entries':len(unique),
    'interpretation':'Diagnostic pointers overlap across request, repair and stage levels. This is not a count of independent failed generations. Request failures and failure-inclusive benchmark rates are reported separately.',
    'original_failure_log':str(original.relative_to(root)),
    'partial_streams':'Retained under partial_*.jsonl or interrupted_*.jsonl; early timeouts before token-level checkpointing lack complete text, as documented in RUN_LOG.md.'},indent=2)+'\n')
print('Diagnostic pointers',len(unique))
