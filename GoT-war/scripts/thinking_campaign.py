"""Bounded thinking-enabled source/mechanism review after the failed literal audit."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
from got_war.application import run_application
from got_war.application_baselines import run as baselines
b=Budget('.')
old=next(p for p in reversed(json.loads((b.run/'processes.json').read_text())) if p['label']=='application_semantic')
stat=Path('/proc/%s/stat'%old['pid'])
if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':
    raise RuntimeError('Prior application review is still active')
archive=b.run/'application_v4'
if not archive.exists():(b.run/'application').rename(archive)
for source in archive.glob('*/semantic_input.json'):
    destination=b.run/'application'/source.parent.name/'semantic_input.json'
    if not destination.exists():atomic_json(destination,json.loads(source.read_text()))
atomic_json(b.run/'thinking_revision.json',{
    'change':'Enable and retain reasoning tokens for source-semantic and dependency review; preserve the same frozen packets and initial variable inventory.',
    'motivation':'All v4 cases failed strict contiguous-quote validation. They are retained; no quote is silently substituted.',
    'controlled_inference_changed':False,'max_repairs_per_artifact':2,
})
run_application('.')
baselines('.')
