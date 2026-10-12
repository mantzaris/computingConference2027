"""Archive formal-only candidates and run the disclosed semantic development gate."""
import json,time
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
from got_war.application import run_application
from got_war.application_baselines import run as baselines

b=Budget('.')
registry=json.loads((b.run/'processes.json').read_text())
old=next(p for p in reversed(registry) if p['label']=='application_modular_source_stage')
while process_birth(old['pid'])==old['birth']:
    stat=Path('/proc/%s/stat'%old['pid'])
    if not stat.exists() or stat.read_text().split(') ',1)[1].split()[0]=='Z':break
    b.check(estimated_seconds=30,reserve_seconds=5*3600);time.sleep(10)
archive=b.run/'application_v3'
if not archive.exists():(b.run/'application').rename(archive)
for case in json.loads(Path('configs/experiment.json').read_text())['cases']:
    folder=b.run/'application'/case['id'];folder.mkdir(parents=True,exist_ok=True)
    source=archive/case['id']/'typed_variables.json'
    if source.exists() and not (folder/'semantic_input.json').exists():
        atomic_json(folder/'semantic_input.json',{'nodes':json.loads(source.read_text()),'provenance':'Unchanged LLM variable inventory before old graph pruning; semantic corrections and new parents are LLM-generated.'})
atomic_json(b.run/'semantic_revision.json',{
    'reason':'Formal validity did not prevent a chronological-chain model or actor/action overstatements. Review variables against source entailment and discover individual mechanisms before global reconciliation.',
    'selection':'Final source-semantic protocol; earlier formally accepted and failed candidates are retained in application_v3, not counted as independent cases.',
    'manual_literary_edges_or_equations':False,
    'max_repairs_per_artifact':2,
})
run_application('.')
baselines('.')
