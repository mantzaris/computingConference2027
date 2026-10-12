"""Recover parser/diagnostic defects without erasing prior model generations."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
registry=json.loads((b.run/'processes.json').read_text())
old=next(p for p in reversed(registry) if p['label'] in ('application_final','application_checked'))
stat=Path('/proc/%s/stat'%old['pid'])
if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':raise RuntimeError('Prior application worker still active')
for folder in (b.run/'application').iterdir():
    archive=folder/('diagnostics_before_%d'%old['pid']);archive.mkdir(exist_ok=True)
    files=list(folder.glob('failed_alternative_*.json'))+[folder/'failure.json']+list((folder/'local_equations').glob('*_failed_*.json'))
    for file in files:
        if file.exists() and not (archive/file.name).exists():file.rename(archive/file.name)
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_checked')
atomic_json(b.run/'concrete_diagnostics_revision.json',{'job':r,'changes':['Sparse graph corrections preserve unchanged generated parent lists; existing correction outputs are replayed.','Equation prompts include recorded event times, the concrete factual input vector and required target value; validation returns actual versus required output.'],'earlier_failed_generations':'retained','manual_war_rules':False})
print(r['label'],r['pid'])
