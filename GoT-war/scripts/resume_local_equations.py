"""Resume final source review and local mechanism artifacts, retaining old failures."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
old=next(p for p in reversed(json.loads((b.run/'processes.json').read_text())) if p['label'].startswith('application_thinking'))
stat=Path('/proc/%s/stat'%old['pid'])
if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':raise RuntimeError('Prior application worker still active')
for folder in (b.run/'application').iterdir():
    archive=folder/'whole_equation_failures';archive.mkdir(exist_ok=True)
    for file in list(folder.glob('failed_alternative_*.json'))+[folder/'failure.json']:
        if file.exists():
            dest=archive/(str(old['pid'])+'_'+file.name)
            if not dest.exists():file.rename(dest)
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_final')
atomic_json(b.run/'local_equation_revision.json',{'job':r,'change':'Compact graph reconciliation and separately validated generated local expressions using mechanically bound formal inputs; prior whole-model failures retained.'})
print(r['label'],r['pid'])
