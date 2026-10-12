"""Resume a completed application worker after serialization-only corrections."""
import json,sys
from pathlib import Path
from got_war.budget import Budget, process_birth, atomic_json

b = Budget('.')
registry = json.loads((b.run / 'processes.json').read_text())
old = next(p for p in reversed(registry) if p['label'].startswith('application_modular'))
stat = Path('/proc/%s/stat' % old['pid'])
if process_birth(old['pid']) == old['birth'] and stat.exists():
    state = stat.read_text().split(') ', 1)[1].split()[0]
    if state != 'Z':
        raise RuntimeError('Previous project application worker is still active')
for folder in (b.run / 'application').iterdir():
    failure = folder / 'failure.json'
    if failure.exists():
        saved = folder / ('failure_before_resume_%s.json'%old['pid'])
        if not saved.exists():failure.rename(saved)
label='application_modular_'+(sys.argv[1] if len(sys.argv)>1 else 'resume')
record = b.launch(['bash', '-c', 'PYTHONPATH=src .venv/bin/python scripts/modular_application.py'], label)
atomic_json(b.run / (label+'_resume.json'), {
    'job': record,
    'change': 'Modular artifact validation; source IDs are checked by the citation stage, and generated chronology corrections are recorded before graph validation.',
    'causal_edges_supplied_by_researcher': False,
})
print(record['label'], record['pid'])
