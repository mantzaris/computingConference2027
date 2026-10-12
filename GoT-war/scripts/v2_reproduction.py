"""Compact, lossless version-2 numerical reproduction without private transcripts."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile
import reproduction as common

ROOT=Path(__file__).resolve().parents[1]
common.ARCHIVE='results/v2/reproduction.tar.gz'
common.MANIFEST='results/v2/reproduction_manifest.json'
common.MAX_FILES=220
common.MAX_BYTES=32*1024*1024


def pack(root):
    campaign=json.loads((root/'configs/budget_v2.json').read_text())['campaign_id'];run=root/'runs'/campaign
    ledger=run/'usage_ledger.jsonl'
    rows=[json.loads(line) for line in (run/'requests.jsonl').read_text().splitlines()]
    ledger.write_text(''.join(json.dumps({k:v for k,v in row.items() if k!='response'},ensure_ascii=False,separators=(',',':'))+'\n' for row in rows))
    files=[run/'benchmark_cases.jsonl',run/'benchmark_design.json',ledger]
    files+=sorted((run/'benchmark').glob('*.json'))
    files+=sorted(run.glob('pilot_round[1-5]/*.json'))
    files+=sorted((run/'application').glob('*/final.json'))
    for name in ('supervision_probe.json','pilot_round1_summary.json','completion.json','inference_usage.json',
                 'environment.json','service_counters.json','gpu_samples.jsonl','processes.json','shutdown_verification.json',
                 'watchdog_final.json','COMPLETE'):
        if (run/name).exists():files.append(run/name)
    payload={p.relative_to(root).as_posix():p.read_bytes() for p in sorted(set(files))}
    if len(payload)>common.MAX_FILES or sum(map(len,payload.values()))>common.MAX_BYTES:raise ValueError('Curated v2 inputs exceed declared archive bounds')
    target=root/common.ARCHIVE
    with target.open('wb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0,compresslevel=9) as zipped:
            with tarfile.open(fileobj=zipped,mode='w',format=tarfile.USTAR_FORMAT) as archive:
                for name,data in payload.items():
                    member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644
                    archive.addfile(member,io.BytesIO(data))
    manifest={'schema':2,'campaign_id':campaign,'archive':common.ARCHIVE,'archive_sha256':common.digest(target.read_bytes()),
        'archive_bytes':target.stat().st_size,'expanded_bytes':sum(map(len,payload.values())),'file_count':len(payload),
        'scope':'Frozen controlled cases, paired records including failed synthesis, retained pilot rounds, accepted application records, and usage/supervision provenance. All expanded paths remain ignored.',
        'local_only':'Full transcripts, private prompts, earlier application candidates, response fragments, model weights and raw service logs. These remain in the original project; no full-text redistribution permission is assumed.',
        'files':{name:{'bytes':len(data),'sha256':common.digest(data)} for name,data in payload.items()}}
    (root/common.MANIFEST).write_text(json.dumps(manifest,indent=2)+'\n')
    return {k:manifest[k] for k in ('archive_bytes','expanded_bytes','file_count')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group()
    mode.add_argument('--pack',action='store_true');mode.add_argument('--check',action='store_true');a=p.parse_args()
    print(json.dumps(pack(ROOT) if a.pack else common.restore(ROOT,a.check),indent=2))
