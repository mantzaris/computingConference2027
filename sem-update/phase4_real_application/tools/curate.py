"""Compact Git outputs while preserving original bytes in ignored evidence."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

PHASE=Path(__file__).resolve().parents[1];PROJECT=PHASE.parent
ROOT=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase4_real_application'))
SELECTED={'A_process_graph.pdf','D_accuracy_cost.pdf'}
MAIN={'M0','M1','M2','M3','M4','M5','fixed','random'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    results=PHASE/'results';backup=ROOT/'reports/curated_full_precision';backup.mkdir(parents=True,exist_ok=True)
    figures_backup=ROOT/'figure_versions/before_curation'
    if not figures_backup.exists():shutil.copytree(ROOT/'figures',figures_backup)
    for p in results.iterdir():
        if p.is_file() and not (backup/p.name).exists():shutil.copyfile(p,backup/p.name)
    frozen={p.name:sha(p) for p in [results/'protocol.json',results/'llm_prior.json',results/'frozen_selections.json']}
    graph=results/'graphs.json';graph.write_text(json.dumps(json.loads(graph.read_text()),separators=(',',':'))+'\n')
    for p in results.glob('*.csv'):
        with open(p,newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        if p.name in ('effects.csv','metrics.csv'):rows=[r for r in rows if r['method'] in MAIN]
        for row in rows:
            for key,value in row.items():
                if value and re.fullmatch(r'-?(?:\d+\.\d*|\d*\.\d+|\d+[eE][-+]?\d+)(?:[eE][-+]?\d+)?',value):
                    row[key]=format(float(value),'.10g')
        with open(p,'w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    omitted=[]
    for p in (PHASE/'figures').glob('*.pdf'):
        if p.name in SELECTED:continue
        assert sha(p)==sha(ROOT/'figures'/p.name)
        dest=ROOT/'reports/not_in_git_figures'/p.name;dest.parent.mkdir(exist_ok=True)
        shutil.move(str(p),str(dest));omitted.append(p.name)
    assert frozen=={n:sha(results/n) for n in frozen}
    report={'full_precision_artifact':'reports/curated_full_precision/',
        'original_effects_and_metrics':'reports/all_effects.csv; reports/all_metrics.csv',
        'curation':'CSV numbers up to 10 significant digits; main eight methods in effects/metrics; complete semantic/refit/checkpoint summaries retained; lossless graph JSON whitespace removal',
        'selected_git_pdfs':sorted(SELECTED),'other_final_figures':'figures/ under artifact root; PDF/SVG/PNG all preserved',
        'frozen_files_unchanged':True,
        'full_precision_files':{p.name:sha(p) for p in sorted(backup.iterdir()) if p.is_file()}}
    (results/'curation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selected_pdfs':sorted(SELECTED),'moved_to_evidence':omitted,'frozen_unchanged':True}))

if __name__=='__main__':main()
