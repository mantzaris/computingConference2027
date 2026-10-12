"""Bounded modular application revision, preserving all earlier protocols."""
import json,os,signal,time
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
from got_war.application import run_application
from got_war.application_baselines import run as baselines
b=Budget('.')
# Archive only failed/unfinished construction; accepted blueprints/models are preserved.
for case in json.loads(Path('configs/experiment.json').read_text())['cases']:
 folder=b.run/'application'/case['id']
 if folder.exists() and not (folder/'blueprint.json').exists():
  archive=b.run/'application_v2'/case['id'];archive.parent.mkdir(exist_ok=True)
  if not archive.exists():folder.rename(archive)
run_application('.')
baselines('.')
