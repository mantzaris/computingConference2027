"""Preserve earlier diagnostic repairs and normalize generated time units."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
old=next(p for p in reversed(json.loads((b.run/'processes.json').read_text())) if p['label'].startswith('application_thinking'))
stat=Path('/proc/%s/stat'%old['pid'])
if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':
    raise RuntimeError('Prior application worker is still active')
for folder in (b.run/'application').iterdir():
    if (folder/'blueprint.json').exists():continue
    archive=folder/'prior_time_units';archive.mkdir(exist_ok=True)
    for file in list(folder.glob('mechanism*.json'))+[folder/'failure.json']:
        if file.exists() and not (archive/file.name).exists():file.rename(archive/file.name)
    # Resume the most recent diagnosed semantic artifact, never resurrect an
    # earlier rejected draft merely because its quote formatting now aligns.
    for end in folder.glob('semantic_variables_*_failed_2.json'):
        start=end.name.split('_')[2];destination=folder/('semantic_variables_'+start+'.json')
        if destination.exists() and not (archive/destination.name).exists():destination.rename(archive/destination.name)
        atomic_json(destination,json.loads(end.read_text())['response'])
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_thinking_timed')
atomic_json(b.run/'time_unit_revision.json',{'job':r,'change':'LLM identifies event episode strings or unknown; deterministic encoding supplies a common numeric unit. Earlier mixed-unit dependency proposals remain archived. The latest bounded semantic repair is preserved when resuming.'})
print(r['label'],r['pid'])
