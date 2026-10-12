"""One coverage-enrichment pass; preserve both models and every failed artifact."""
import json,shutil
from pathlib import Path
from got_war.budget import Budget,atomic_json
from got_war.application import run_application

b=Budget('.')
decisions=[]
for case in json.loads((b.root/'configs/experiment.json').read_text())['cases']:
    folder=b.run/'application'/case['id']
    archive=b.run/'application_before_coverage'/case['id']
    old=list((archive if archive.exists() else folder).glob('alternative_*.json'))
    supplement=folder/'coverage_supplement.json'
    marker=b.run/'coverage_decisions'/(case['id']+'.json')
    if marker.exists() or not old or not supplement.exists():continue
    initial=max(len(json.loads(p.read_text())['model']['nodes']) for p in old)
    if initial>=10 or not json.loads(supplement.read_text())['variables']:continue
    if not archive.exists():
        archive.parent.mkdir(parents=True,exist_ok=True)
        folder.rename(archive);folder.mkdir()
        for pattern in ('facts_*.json','fact_audit_*.json','state_schema_*.json','coverage_*.json'):
            for file in archive.glob(pattern):shutil.copy2(file,folder/file.name)
        if (archive/'ordered_graph').exists():shutil.copytree(archive/'ordered_graph',folder/'ordered_graph')
    print('COVERAGE',case['id'],'initial nodes',initial,flush=True)
    run_application('.',case_ids=[case['id']])
    proposed=list(folder.glob('alternative_*.json'))
    sizes=[len(json.loads(p.read_text())['model']['nodes']) for p in proposed]
    keep=bool(sizes) and max(sizes)>initial
    decision={'case':case['id'],'initial_nodes':initial,'coverage_nodes':sizes,'coverage_selected':keep,
              'policy':'At most one source-coverage pass. Prefer a larger formally valid outcome-ancestor model from the source-audited inventory; otherwise retain the first accepted model. Selection precedes numerical interpretation and does not certify causal truth.',
              'initial_artifacts':str(archive.relative_to(b.root)),
              'node_target_met':(max(sizes) if keep else initial)>=10}
    if not keep:
        failed=b.run/'application_coverage_attempts'/case['id'];failed.parent.mkdir(exist_ok=True)
        folder.rename(failed);shutil.copytree(archive,folder)
        decision['coverage_artifacts']=str(failed.relative_to(b.root))
    atomic_json(marker,decision);decisions.append(decision)
print(json.dumps(decisions),flush=True)
