"""Re-render using only compact inputs, with no raw data, model or GPU access."""
import hashlib
import json
from pathlib import Path
import shutil
import render_figures as render

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    original=render.ROOT/'figures';scratch=render.ROOT/'figure_reproduction'
    project=scratch/'curated_only';(project/'results').mkdir(parents=True,exist_ok=True)
    files=['graphs.json','protocol.json','edge_frequency.csv','plot_total_effects.csv','plot_responses.csv','summary.csv','costs.csv','plot_tradeoff.csv']
    inputs={}
    for name in files:
        source=render.RESULTS/name;inputs[name]=sha(source);shutil.copyfile(source,project/'results'/name)
    target=render.RESULTS/'figure_reproduction.json'
    render.PHASE=project;render.RESULTS=project/'results';render.FIGURES=scratch/'rendered'
    render.main(False)
    records=[]
    for path in sorted(original.glob('*')):
        if path.suffix not in ('.pdf','.svg','.png'):continue
        other=render.FIGURES/path.name
        records.append({'name':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'identical':other.exists() and sha(other)==sha(path)})
    report={'passed':all(r['identical'] for r in records),'formats_checked':len(records),'inputs':inputs,'files':records,
            'raw_data_or_checkpoint_access':False,'gpu_required':False}
    for group in ('pressure','current'):
        svg=(original/('B_'+group+'_responses.svg')).read_text()
        assert '<!-- 0.01 -->' in svg and '<!-- 45° -->' in svg, 'Fan duty / hatch units lost in response labels'
    report['response_axis_units_checked']=True
    target.write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:raise AssertionError('Plot reproduction differs')
    print(json.dumps({'passed':True,'formats_checked':len(records)}))

if __name__=='__main__':main()
