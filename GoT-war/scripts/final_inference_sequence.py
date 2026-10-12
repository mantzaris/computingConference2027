"""Dependency-aware final project stages, all under the original watchdog."""
import json,time
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json

b=Budget('.')
def live(entry):
    path=Path('/proc/%d/stat'%entry['pid'])
    return (process_birth(entry['pid'])==entry['birth'] and path.exists()
            and path.read_text().rsplit(')',1)[1].split()[0]!='Z')

registry=json.loads((b.run/'processes.json').read_text())
dependencies=[r for r in registry if r['label'] in ('application_source_inventory','application_coverage_pass','application_coverage_review')]
def wait(entries,stage):
    while any(live(entry) for entry in entries):
        b.check(estimated_seconds=60,reserve_seconds=5*3600)
        atomic_json(b.run/'final_sequence_progress.json',{'stage':stage,'active':[e['label'] for e in entries if live(e)],'remaining_seconds':b.remaining()})
        time.sleep(15)
wait(dependencies,'waiting for preceding application artifacts')
stages=[('final_coverage_review','PYTHONPATH=src .venv/bin/python scripts/review_source_coverage.py'),
        ('complete_outcome_packet','GOT_WAR_RESERVE_OUTPUT_TOKENS=60000 PYTHONPATH=src .venv/bin/python scripts/complete_outcome_packet.py'),
        ('final_source_review','PYTHONPATH=src .venv/bin/python scripts/audit_application_sources.py'),
        ('final_trace_refinement','PYTHONPATH=src .venv/bin/python scripts/refine_application.py')]
for label,command in stages:
    marker=b.run/(label+'_stage_finished.json')
    if marker.exists():continue
    job=b.launch(['bash','-c',command],label);wait([job],label)
    atomic_json(marker,{'job':job,'process_finished':True,'success_requires_artifact_validation':True})
atomic_json(b.run/'final_sequence_finished.json',{'stages':[x[0] for x in stages],'status':'processes finished; inspect artifacts and failure logs before claiming completion'})
