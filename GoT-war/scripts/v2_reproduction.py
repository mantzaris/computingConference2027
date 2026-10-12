"""Compact, lossless version-2 numerical reproduction without private transcripts."""
import argparse
import gzip
import io
import json
from pathlib import Path
import tarfile
import subprocess
import sys
from datetime import datetime, timezone
import reproduction as common

ROOT=Path(__file__).resolve().parents[1]
common.ARCHIVE='results/v2/reproduction.tar.gz'
common.MANIFEST='results/v2/reproduction_manifest.json'
common.MAX_FILES=220
common.MAX_BYTES=32*1024*1024


def pack(root):
    campaign=json.loads((root/'configs/budget_v2.json').read_text())['campaign_id'];run=root/'runs'/campaign
    cases=[json.loads(line) for line in (run/'benchmark_cases.jsonl').read_text().splitlines()]
    incomplete=[c['id'] for c in cases if not (run/'benchmark'/(c['id']+'.json')).exists() or
        not json.loads((run/'benchmark'/(c['id']+'.json')).read_text()).get('completed')]
    if incomplete:raise ValueError('Do not publish a partial campaign archive: '+str(len(incomplete))+' controlled records incomplete')
    ledger=run/'usage_ledger.jsonl'
    rows=[json.loads(line) for line in (run/'requests.jsonl').read_text().splitlines()]
    from v2_resources import tag_controlled_requests
    rows=tag_controlled_requests(root,rows)
    ledger.write_text(''.join(json.dumps({k:v for k,v in row.items() if k!='response'},ensure_ascii=False,separators=(',',':'))+'\n' for row in rows))
    files=[run/'benchmark_cases.jsonl',run/'benchmark_design.json',ledger]
    files+=sorted((run/'benchmark').glob('*.json'))
    files+=sorted(run.glob('pilot_round[1-5]/*.json'))
    files+=sorted((run/'application').glob('*/final.json'))
    for name in ('supervision_probe.json','pilot_round1_summary.json','completion.json','inference_usage.json','inference_finished.json',
                 'environment.json','service_counters.json','gpu_samples.jsonl','processes.json','shutdown_verification.json',
                 'fixed_benchmark_launch.json','fixed_benchmark_failed_import_launch.json','watchdog_final.json','COMPLETE'):
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


def validate_release(root):
    """Exercise a clean staged export with no original private/run access."""
    import os
    import re
    destination=root/'.cache'/('v2_release_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    destination.mkdir(parents=True)
    entries=subprocess.check_output(['git','-C',str(root),'ls-files','--stage','-z','--','.'])
    exported=0
    for row in entries.split(b'\0'):
        if not row:continue
        info,name=row.split(b'\t',1);mode,oid,stage=info.decode().split();name=name.decode()
        if mode not in ('100644','100755') or stage!='0' or not common.allowed('runs/export/'+name,'export'):
            raise ValueError('Unsafe or unresolved staged entry '+name)
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(subprocess.check_output(['git','-C',str(root),'cat-file','blob',oid]));exported+=1
    (destination/'.cache').mkdir(exist_ok=True)
    environment=dict(os.environ,PYTHONPATH='src')
    def execute(args,cwd=destination,env=environment):
        value=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True)
        if value.returncode:raise RuntimeError('Clean export failed: '+str(args)+'\n'+value.stdout+'\n'+value.stderr)
        return value.stdout
    restored=json.loads(execute([sys.executable,'scripts/v2_reproduction.py']))
    repeated=json.loads(execute([sys.executable,'scripts/v2_reproduction.py']))
    tests=execute([sys.executable,'-m','pytest','-q','--basetemp=.cache/pytest'])
    execute([sys.executable,'-m','got_war.v2.analysis','--split','test'])
    verification=json.loads(execute([sys.executable,'scripts/v2_verify.py']))
    execute([sys.executable,'-c','from got_war.v2.reporting import benchmark_reports,manuscript_tables; benchmark_reports("."); manuscript_tables(".")'])
    execute([sys.executable,'scripts/v2_error_analysis.py'])
    execute([sys.executable,'-m','got_war.v2.figures'])
    stable=['results/v2/test_summary.json','results/v2/test_scm_scores.csv','results/v2/verification.json',
        'results/v2/RESULTS.md','results/v2/SOURCE_PRIORITY.md','results/v2/EXPLANATION_REPORT.md','results/v2/ERROR_ANALYSIS.md',
        'paper/v2/measured_macros.tex','paper/v2/measured_results.tex','paper/v2/application_results.tex',
        'figures/v2/five_kings_network.dot','figures/v2/network_index.json',
        'figures/v2/five_kings_network.svg','figures/v2/benchmark_components.svg',
        'figures/v2/path_influence_evidence.svg','figures/v2/coalition_sensitivity.svg']
    campaign=json.loads((destination/'configs/budget_v2.json').read_text())['campaign_id']
    if (destination/'runs'/campaign/'completion.json').exists():
        execute([sys.executable,'scripts/v2_resources.py']);stable.append('results/v2/usage.json')
    differences=[name for name in stable if (destination/name).read_bytes()!=(root/name).read_bytes()]
    texenv=dict(os.environ,TEXINPUTS='.:../template:')
    for _ in range(2):execute(['pdflatex','-interaction=nonstopmode','-halt-on-error','manuscript.tex'],destination/'paper/v2',texenv)
    pdfinfo=execute(['pdfinfo','paper/v2/manuscript.pdf'])
    checked_at=datetime.now(timezone.utc)
    config=json.loads((root/'configs/budget_v2.json').read_text())
    within_deadline=checked_at<=datetime.fromisoformat(config['hard_deadline'])
    report={'at':checked_at.isoformat(),'scope':'Clean export of staged release; private prompts/transcripts and original run folders are absent.',
        'elapsed_hours_through_release_validation':(checked_at-datetime.fromisoformat(config['started_at'])).total_seconds()/3600,
        'within_original_campaign_deadline':within_deadline,
        'exported_files':exported,'restored_records':restored,'repeat_restore':repeated,
        'tests':tests.strip(),'verification':verification,'byte_identical_outputs':stable,'differences':differences,
        'figures_regenerated':True,'manuscript_compile_passes':2,'manuscript_pages':int(re.search(r'Pages:\s+(\d+)',pdfinfo).group(1)),
        'source_entailment_check':'Not performed: original private context is intentionally absent. This is numerical/package reproducibility only.',
        'passed':not differences and verification['passed'] and repeated['restored_records']==0}
    (root/'results/v2/release_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:raise RuntimeError('Clean release differs: '+str(differences))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group()
    mode.add_argument('--pack',action='store_true');mode.add_argument('--check',action='store_true')
    mode.add_argument('--validate-release',action='store_true');a=p.parse_args()
    print(json.dumps(pack(ROOT) if a.pack else validate_release(ROOT) if a.validate_release else common.restore(ROOT,a.check),indent=2))
