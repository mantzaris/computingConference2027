"""Internal figure gallery in the official downloaded Springer conference class."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

PHASE=Path(__file__).resolve().parents[1];PROJECT=PHASE.parent
ROOT=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase4_real_application'))

def main():
    package=PROJECT/'.artifacts/data/raw/venue/SAI_Paper_Format_Latex_Conference.zip'
    if not package.exists():package=ROOT/'protocols/venue/SAI_Paper_Format_Latex_Conference.zip'
    build=ROOT/'paper_layout_check';build.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(package) as z:
        for name in ('svproc.cls','aliascnt.sty','remreset.sty'):(build/name).write_bytes(z.read('Latex/template/'+name))
    lines=[r'\documentclass{svproc}',r'\usepackage{graphicx}',r'\usepackage{booktabs}',r'\begin{document}']
    # Validate all six final scientific panels, including formats kept outside
    # Git to respect the cumulative repository budget.
    figures=sorted((ROOT/'figures').glob('[A-E]_*.pdf'))
    if len(figures)!=6:raise RuntimeError('Render the complete final figure set first')
    for i,p in enumerate(figures):
        target=build/f'figure{i}.pdf';shutil.copyfile(p,target)
        lines += [r'\begin{figure}[p]',r'\centering',r'\includegraphics[width=\textwidth]{'+target.name+'}',
                  r'\caption{Wind-tunnel application: '+p.stem.replace('_',r'\_')+r'. Internal layout check.}',r'\end{figure}',r'\clearpage']
    table=PHASE/'comparison.tex'
    if table.exists():
        shutil.copyfile(table,build/'comparison.tex');lines += [r'\begin{table}[p]',r'\centering',r'\input{comparison.tex}',r'\caption{Application comparison.}',r'\end{table}']
    lines += [r'\end{document}'];(build/'layout.tex').write_text('\n'.join(lines)+'\n')
    env=os.environ.copy()
    for key,name in [('TEXMFVAR','texmf-var'),('TEXMFCONFIG','texmf-config')]:
        p=ROOT/'model_cache'/name;p.mkdir(parents=True,exist_ok=True);env[key]=str(p)
    with open(build/'stdout.log','w') as out:
        code=subprocess.call(['pdflatex','-halt-on-error','-interaction=nonstopmode','layout.tex'],cwd=build,env=env,stdout=out,stderr=subprocess.STDOUT)
    log=(build/'stdout.log').read_text();report={'return_code':code,'template_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
        'template_source':'https://saiconference.com/Downloads/SAI_Paper_Format_Latex_Conference.zip',
        'template_provenance':'Official package downloaded 6 October 2026; fresh 9 October urllib retrieval returned HTTP 403; cached official package used.',
        'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in figures},
        'layout_warnings':[s for s in log.splitlines() if 'Overfull' in s or 'too large' in s],
        'artifact':'paper_layout_check/layout.pdf','submission':False}
    (PHASE/'results/template_check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return code

if __name__=='__main__':raise SystemExit(main())
