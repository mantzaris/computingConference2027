#!/usr/bin/env python3
"""Compile the existing vector figures in the downloaded official class.

This builds an internal layout-check artifact, not a submission manuscript.
No experiments, manuscript claims, credentials, or network requests are involved.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

PROJECT=Path(__file__).resolve().parents[2]
PHASE=PROJECT/"phase2"

def main():
    root=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase2')).resolve()
    package=PROJECT/'.artifacts/data/raw/venue/SAI_Paper_Format_Latex_Conference.zip'
    figures=sorted((PHASE/'paper/figures').glob('*.pdf'))
    tables=sorted((PHASE/'paper/tables').glob('*.tex'))
    if not figures:
        raise RuntimeError('No executed figure PDFs exist yet')
    if not package.exists():
        raise RuntimeError('Download the official package named in docs/venue.md first')
    build=root/'paper_layout_check'
    build.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        for name in ('svproc.cls','aliascnt.sty','remreset.sty'):
            (build/name).write_bytes(archive.read('Latex/template/'+name))
    lines=[r'\documentclass{svproc}',r'\usepackage{graphicx}',r'\usepackage{booktabs}',r'\begin{document}',
           r'\pagestyle{plain}']
    for i,figure in enumerate(figures):
        target=build/('figure'+str(i)+'.pdf')
        shutil.copyfile(figure,target)
        lines.extend([r'\begin{figure}[p]',r'\centering',
                      r'\includegraphics[width=\textwidth]{'+target.name+'}',
                      r'\caption{Internal layout check: '+figure.stem.replace('_',r'\_')+'. '+
                      r'Not a submission manuscript}',r'\end{figure}',r'\clearpage'])
    for i,table in enumerate(tables):
        target=build/('table'+str(i)+'.tex')
        shutil.copyfile(table,target)
        lines.extend([r'\begin{table}[p]',r'\caption{Internal layout check: '+table.stem.replace('_',r'\_')+'}',
                      r'\centering',r'\input{'+target.name+'}',r'\end{table}',r'\clearpage'])
    lines.append(r'\end{document}')
    (build/'layout.tex').write_text('\n'.join(lines)+'\n')
    env=os.environ.copy()
    for variable,name in [('TEXMFVAR','texmf-var'),('TEXMFCONFIG','texmf-config')]:
        path=root/'model_cache'/name
        path.mkdir(parents=True,exist_ok=True)
        env[variable]=str(path)
    log=build/'stdout.log'
    with open(log,'w') as output:
        status=subprocess.call(['pdflatex','-halt-on-error','-interaction=nonstopmode','layout.tex'],
                               cwd=build,env=env,stdout=output,stderr=subprocess.STDOUT)
    text=log.read_text()
    report={'return_code':status,'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in figures},
            'tables':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in tables},
            'template_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
            'latex_version':subprocess.check_output(['pdflatex','--version'],text=True).splitlines()[0],
            'layout_warnings':[line for line in text.splitlines() if 'Overfull' in line or 'too large' in line],
            'artifact_pdf':str((build/'layout.pdf').relative_to(root)),
            'manuscript_or_submission':False}
    target=PHASE/'results/figure_template_check.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return status

if __name__=='__main__':
    raise SystemExit(main())
