"""Start source-first application development, retaining prior failed protocols."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
registry=json.loads((b.run/'processes.json').read_text())
for old in registry:
    if old['label'].startswith('application'):
        stat=Path('/proc/%s/stat'%old['pid'])
        if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':
            raise RuntimeError('Application worker still active: '+old['label'])
archive=b.run/'application_v5';current=b.run/'application'
if not archive.exists() and current.exists():current.rename(archive)
job=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_source_inventory')
atomic_json(b.run/'source_inventory_revision.json',{'job':job,'protocol':'v6','changes':['Discover atomic events directly from small source chunks; same-model entailment audit excludes partial/unsupported events.','Select a graph from the broader audited inventory; prune context outside outcome ancestry without fabricating links.','Use reasoning-enabled local equation generation; source boundary identities get an explicit background-only contract.'],'all_prior_protocols':'retained under application_v1...v5','controlled_benchmark_changed':False,'manual_story_graph_or_rule':False})
print(job['label'],job['pid'])
