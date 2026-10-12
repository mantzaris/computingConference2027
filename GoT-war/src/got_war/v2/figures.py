"""Vector publication figures from frozen numerical records; no generated artwork."""
import collections
import html
import json
from pathlib import Path
import subprocess
import textwrap
import numpy as np
from ..budget import atomic_json
from ..structural_programs import SCM,equation
from .runtime import paths


def settings():
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42,'savefig.bbox':'tight'})


def save(fig,folder,name):
    fig.savefig(folder/(name+'.svg'))
    fig.savefig(folder/(name+'.pdf'),metadata={'Creator':'GoT-war reproducible v2 analysis','Author':''})
    fig.savefig(folder/(name+'.png'),dpi=150)


def network(app,folder):
    record=app['records'][0];model=record['model'];scm=SCM(model)
    trace=app['trace'];changed=set(trace['changed_nodes'])
    participation=collections.Counter(n for p in record['selection']['paths'] for n in p)
    source=set(record['selection']['source_boundary']);edges=record['edge_evidence']
    lines=['digraph G {','graph [rankdir=TB, bgcolor="white", pad="0.18", nodesep="0.25", ranksep="0.38", splines=polyline, outputorder=edgesfirst];',
           'node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=13, color="#38515d", margin="0.12,0.09"];',
           'edge [fontname="DejaVu Sans", fontsize=10, arrowsize=.65, penwidth=1.2];']
    index=[]
    for i,ident in enumerate(scm.order):
        n=scm.nodes[ident];title='<BR/>'.join(html.escape(x) for x in textwrap.wrap(n['label'],24))
        rule='<BR/>'.join(html.escape(x) for x in textwrap.wrap(n.get('short_mechanism','Fixed boundary input'),29))
        factual=trace['factual_states'][ident];counter=trace['counterfactual_states'][ident]
        state=str(factual)+' → '+str(counter) if ident in changed else str(factual)+' → '+str(counter)+' (same)'
        bg='#e9f4f2' if n['parents'] else '#fff4db';color='#9b3150' if n.get('event_status')=='unsupported' else '#315467'
        if ident in changed:color='#6f42a8'
        if ident==model['outcome']:bg='#d4e8f0'
        label='<'+title+'<BR/><FONT POINT-SIZE="11">'+rule+'</FONT><BR/><FONT POINT-SIZE="10">'+html.escape('E%d · %s · %s'%(i+1,n.get('event_time','time unresolved'),state))+'</FONT>>'
        lines.append('"%s" [label=%s, fillcolor="%s", color="%s", penwidth=%s, peripheries=%d];'%(ident,label,bg,color,2 if ident in changed else 1.2,2 if participation[ident]>1 else 1))
        index.append({'equation_id':'E%d'%(i+1),'node':ident,'label':n['label'],'definition':n['definition'],
            'equation':equation(n['expr']),'factual':factual,'counterfactual':counter,'event_status':n.get('event_status'),'sources':n['segments']})
    for a,b in scm.graph.edges:
        e=edges[a+'>'+b];score=e['score'];style='solid' if score==1 else 'dashed' if score>0 else 'dotted'
        color='#286b69' if score>0 else '#9a7272'
        behavior=scm.nodes[b].get('behavior',{});polarity=next((x['polarity'] for x in behavior.get('parent_changes',[]) if x['parent']==a),'unresolved')
        arrow='tee' if polarity=='inhibitory' else 'normal'
        label='−' if polarity=='inhibitory' else '±' if polarity=='mixed' else ''
        lines.append('"%s" -> "%s" [style=%s,color="%s",arrowhead=%s,label="%s"];'%(a,b,style,color,arrow,label))
    lines.append('}')
    dot=folder/'five_kings_network.dot';dot.write_text('\n'.join(lines)+'\n')
    for fmt in ('svg','pdf','png'):
        subprocess.run(['dot','-T'+fmt,str(dot),'-o',str(folder/('five_kings_network.'+fmt))],check=True)
    atomic_json(folder/'network_index.json',{'model':model['id'],'query':trace['query'],'nodes':index,
        'legend':'State annotations are factual → selected intervention. Violet borders change; double borders mark nodes shared by selected paths. Solid/dashed/dotted edges mean explicit/contextual/unsupported directional evidence. Tee arrows inhibit; ± has context-dependent sign. These are reviewed hypotheses, not established story laws.'})


def benchmark(summary,folder):
    import matplotlib.pyplot as plt
    methods=['B0','B1','B2','ALT','CARRY'];labels=['Direct LLM','Graph + LLM','One model','Alternatives','Carry forward']
    colors=['#8b8e96','#7593ac','#b57952','#227d78','#bbbbbb']
    rows={r['method']:r['metrics'] for r in summary['tables'] if r['condition']=='all'}
    metrics=[('identified_correct','Identified interventions'),('changed_correct','Outcome changes'),('unchanged_correct','Outcome preserved'),('uncertainty_appropriate','Underidentified questions')]
    fig,axes=plt.subplots(2,2,figsize=(7,5.4),sharex=True,layout='constrained')
    for ax,(metric,title) in zip(axes.flat,metrics):
        for i,method in enumerate(methods):
            r=rows[method][metric];x=r['estimate']
            if x is None:continue
            ax.errorbar(x,i,xerr=[[max(0,x-r['lower'])],[max(0,r['upper']-x)]],fmt='o',color=colors[i],capsize=3,ms=6)
        ax.set(yticks=range(5),yticklabels=labels,xlim=(-.025,1.025),title=title,xlabel='SCM mean with 95% interval')
        ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    save(fig,folder,'benchmark_components');plt.close(fig)


def application_plots(app,folder):
    import matplotlib.pyplot as plt
    records=app['records'];principal=records[0];paths=principal['selection']['paths'];n=len(paths)
    labels=['p%d'%(i+1) for i in range(n)]
    shares=np.asarray([r['attribution']['phi'] for r in records]);support=[p['evidence_support'] for p in principal['evidence_priority']['paths']]
    fig,axes=plt.subplots(1,2,figsize=(7,3.4),layout='constrained')
    ax=axes[0]
    for i in range(n):
        ax.plot([i]*len(records),shares[:,i],'o',color='#387f86',alpha=.5,ms=4)
        ax.plot(i,shares[0,i],'D',color='#273f51',ms=5)
    ax.axhline(0,color='#888',lw=.8);ax.set(xticks=range(n),xticklabels=labels,ylabel='Signed path allocation',title='Aligned function alternatives')
    axes[1].bar(range(n),support,color=['#a56868' if v==0 else '#408c87' for v in support])
    axes[1].set(xticks=range(n),xticklabels=labels,ylim=(0,1.05),ylabel='Weakest directional support',title='Evidence is separate from influence')
    save(fig,folder,'path_influence_evidence');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,3.2),layout='constrained')
    values=principal['attribution']['coalition_values'];counts=collections.Counter(values)
    axes[0].bar([str(k) for k in sorted(counts)],[counts[k] for k in sorted(counts)],color='#477e9c')
    axes[0].set(xlabel='Computed coalition outcome',ylabel='Number of coalitions',title='All selected-path coalitions')
    refs={'Declared':principal['attribution'],'Factual null':principal['reference_sensitivity']['factual_null'],
          'Endpoint stress':principal['reference_sensitivity']['domain_endpoint_stress'],'Four paths':principal['path_selection_sensitivity']['four_paths']}
    for i,(label,record) in enumerate(refs.items()):
        y=np.asarray(record['phi']);axes[1].scatter([i]*len(y),y,color='#387f86',alpha=.65,s=25)
    axes[1].axhline(0,lw=.8,color='#888');axes[1].set(xticks=range(4),xticklabels=list(refs),ylabel='Path allocations',title='Reference / path-set sensitivity')
    axes[1].tick_params(axis='x',rotation=25)
    save(fig,folder,'coalition_sensitivity');plt.close(fig)


def main(root):
    root,run,result=paths(root);folder=root/'figures/v2';folder.mkdir(exist_ok=True);settings()
    application=run/'application/five_kings/final.json'
    if application.exists():
        app=json.loads(application.read_text());network(app,folder);application_plots(app,folder)
    summary=result/'test_summary.json'
    if summary.exists():benchmark(json.loads(summary.read_text()),folder)


if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else '.')
