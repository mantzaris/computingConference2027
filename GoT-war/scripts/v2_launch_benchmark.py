"""Launch the three fixed splits only after the version-2 protocol is frozen."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v2.runtime import budget
from got_war.budget import atomic_json,process_birth


def main():
    b=budget(ROOT);frozen=json.loads((ROOT/'configs/v2_frozen_protocol.json').read_text())
    changed=[p for p,h in frozen['files'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if changed:raise RuntimeError('Frozen protocol differs: '+', '.join(changed))
    if hashlib.sha256((b.run/'benchmark_cases.jsonl').read_bytes()).hexdigest()!=frozen['design']['sha256']:
        raise RuntimeError('Frozen case manifest differs')
    registry=json.loads((b.run/'processes.json').read_text());launched=[]
    for split in ('development','calibration','test'):
        label='v2_fixed_'+split
        for item in registry:
            if item['label']==label and process_birth(item['pid'])==item['birth']:
                state=Path('/proc/%d/stat'%item['pid']).read_text().rsplit(')',1)[1].split()[0]
                if state!='Z':raise RuntimeError('This split already has a live registered worker: '+split)
        launched.append(b.launch([str(ROOT/'.venv/bin/python'),'-m','got_war.v2.experiments','--split',split],label))
    atomic_json(b.run/'fixed_benchmark_launch.json',{'frozen_protocol_sha256':hashlib.sha256((ROOT/'configs/v2_frozen_protocol.json').read_bytes()).hexdigest(),
        'workers':launched,'scheduling':'Three split workers share the existing server, which admits at most two sequences. Questions and SCMs are unchanged.'})
    print(json.dumps(launched,indent=2))


if __name__=='__main__':main()
