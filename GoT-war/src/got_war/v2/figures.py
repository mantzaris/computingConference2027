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
from .runtime import paths,application_record


def settings():
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'GoT-war-v2',
        'pdf.fonttype':42,'savefig.bbox':'tight'})


def save(fig,folder,name):
    fig.savefig(folder/(name+'.svg'))
    svg=folder/(name+'.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    fig.savefig(folder/(name+'.pdf'),metadata={'Creator':'GoT-war reproducible v2 analysis','Author':''})
    fig.savefig(folder/(name+'.png'),dpi=150)
    # This environment's older Matplotlib embeds whole TrueType fonts. Preserve
    # vectors while subsetting fonts to respect the repository release ceiling.
    import shutil
    if shutil.which('gs'):
        temporary=folder.parent.parent/'.cache/v2_pdf';temporary.mkdir(parents=True,exist_ok=True)
        compact=temporary/(name+'.pdf')
        subprocess.run(['gs','-q','-dNOPAUSE','-dBATCH','-sDEVICE=pdfwrite','-dCompatibilityLevel=1.5',
            '-dEmbedAllFonts=true','-dSubsetFonts=true','-dCompressFonts=true',
            '-sOutputFile='+str(compact),str(folder/(name+'.pdf'))],check=True)
        if compact.stat().st_size<(folder/(name+'.pdf')).stat().st_size:compact.replace(folder/(name+'.pdf'))


def network(app,folder):
    record=app['records'][0];model=record['model'];scm=SCM(model)
    trace=app['trace'];changed=set(trace['changed_nodes'])
    participation=collections.Counter(n for p in record['selection']['paths'] for n in p)
    source=set(record['selection']['source_boundary']);edges=record['edge_evidence']
    inspection_file=folder.parent.parent/'results/v2/source_inspection.json'
    inspection=json.loads(inspection_file.read_text()) if inspection_file.exists() else {'items':[]}
    variant=app.get('construction_context',{}).get('variant','fresh')
    flagged={i['node']:i for i in inspection['items'] if i.get('variant','fresh')==variant}
    lines=['digraph G {','graph [rankdir=TB, bgcolor="white", pad="0.18", nodesep="0.16", ranksep="0.38", splines=polyline, outputorder=edgesfirst];',
           'node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=16, color="#38515d", margin="0.10,0.07"];',
           'edge [fontname="DejaVu Sans", fontsize=15, arrowsize=.65, penwidth=1.2];']
    index=[]
    for i,ident in enumerate(scm.order):
        n=scm.nodes[ident]
        # Shorten the explicitly specified target for figure readability only.
        # The operational definition, graph, equations and scores are unchanged.
        display_label='Stark–Lannister conflict active' if ident==model['outcome'] and app['case']['id']=='five_kings' else n['label']
        title_lines=textwrap.wrap(display_label,16)
        if ident in flagged:title_lines[-1]+=' †'
        title='<BR/>'.join(html.escape(x) for x in title_lines)
        behavior=n.get('behavior',{})
        if not n['parents']:rule_text='Fixed input; unexplained upstream causes'
        elif len({next(iter(c)) for c in behavior.get('necessary_for_one',[])})==len(n['parents']):rule_text='Every input condition is required'
        elif any(p['polarity']=='inhibitory' for p in behavior.get('parent_changes',[])):rule_text='Context-dependent enabling and inhibition'
        elif behavior.get('substitution'):rule_text='Substitute enabling pathways'
        elif behavior.get('joint_enabling'):rule_text='Joint enabling conditions'
        else:rule_text='Assumed rule; inspect truth table'
        rule='<BR/>'.join(html.escape(x) for x in textwrap.wrap(rule_text,16))
        factual=trace['factual_states'][ident];counter=trace['counterfactual_states'][ident]
        if n['type']=='category':
            state='state c%d → c%d'%(n['values'].index(factual),n['values'].index(counter))
        else:state=str(factual)+' → '+str(counter)
        if ident not in changed:state+=' (same)'
        bg='#e9f4f2' if n['parents'] else '#fff4db';color='#9b3150' if n.get('event_status')=='unsupported' else '#315467'
        if ident in changed:color='#6f42a8'
        if ident==model['outcome']:bg='#d4e8f0'
        if ident in flagged:bg='#fbe2e5'
        label='<'+title+'<BR/><FONT POINT-SIZE="15">'+rule+'</FONT><BR/><FONT POINT-SIZE="15">'+html.escape('%s · %s'%(ident,n.get('event_time','time unresolved')))+'<BR/>'+html.escape(state)+'</FONT>>'
        lines.append('"%s" [label=%s, fillcolor="%s", color="%s", penwidth=%s, peripheries=%d];'%(ident,label,bg,color,2 if ident in changed else 1.2,2 if participation[ident]>1 else 1))
        index.append({'equation_id':'E%d'%(i+1),'node':ident,'label':n['label'],'displayed_label':display_label,'definition':n['definition'],
            'equation':equation(n['expr']),'factual':factual,'counterfactual':counter,'event_status':n.get('event_status'),'sources':n['segments'],
            'inspection_flag':flagged.get(ident),'generated_short_mechanism':n.get('short_mechanism'),'displayed_behavior_summary':rule_text,'category_codes':{'c%d'%j:value for j,value in enumerate(n.get('values',[]))}})
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
        'legend':'State annotations are factual → selected intervention; category codes are defined in the node index. Violet borders change; otherwise red borders mark an unsupported event audit. Double borders mark nodes shared by selected paths. Solid/dashed/dotted edges mean explicit/contextual/zero-weight directional evidence. Tee arrows inhibit; ± has context-dependent sign. A dagger and pink fill flag a targeted operational/source concern, pending researcher adjudication. These are automatically assessed hypotheses, not established story laws.'})


def benchmark(summary,folder):
    import matplotlib.pyplot as plt
    methods=['B0','B1','B2','ALT','CARRY'];labels=['B0','B1','B2','ALT','Carry']
    colors=['#8b8e96','#7593ac','#b57952','#227d78','#bbbbbb']
    rows={r['method']:r['metrics'] for r in summary['tables'] if r['condition']=='all'}
    metrics=[('identified_correct','Identified interventions'),('changed_correct','Outcome changes'),('unchanged_correct','Outcome preserved'),('uncertainty_appropriate','Underidentified questions')]
    fig,axes=plt.subplots(2,2,figsize=(5,5),sharex=True,constrained_layout=True)
    for ax,(metric,title) in zip(axes.flat,metrics):
        for i,method in enumerate(methods):
            r=rows[method][metric];x=r['estimate']
            if x is None:continue
            ax.errorbar(x,i,xerr=[[max(0,x-r['lower'])],[max(0,r['upper']-x)]],fmt='o',color=colors[i],capsize=3,ms=6)
        ax.set(yticks=range(5),yticklabels=labels,xlim=(-.025,1.025),title=title+'\n(n = %d SCMs)'%rows['B0'][metric]['scms'],xlabel='SCM mean (95% interval)')
        ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    save(fig,folder,'benchmark_components');plt.close(fig)


def application_plots(app,folder):
    import matplotlib.pyplot as plt
    records=app['records'];principal=records[0];paths=principal['selection']['paths'];n=len(paths)
    labels=['p%d'%(i+1) for i in range(n)]
    shares=np.asarray([r['attribution']['phi'] for r in records]);support=[p['evidence_support'] for p in principal['evidence_priority']['paths']]
    fig,axes=plt.subplots(2,1,figsize=(5,4.6),constrained_layout=True)
    ax=axes[0]
    for i in range(n):
        ax.plot([i]*len(records),shares[:,i],'o',color='#387f86',alpha=.5,ms=4)
        ax.plot(i,shares[0,i],'D',color='#273f51',ms=5)
    ax.axhline(0,color='#888888',lw=.8);ax.set(xticks=range(n),xticklabels=labels,ylabel='Signed path allocation',title=('Single conditional model (n = 1)' if len(records)==1 else 'Aligned function alternatives (n = %d)'%len(records)))
    axes[1].bar(range(n),support,color=['#a56868' if v==0 else '#408c87' for v in support])
    axes[1].plot(range(n),support,'o',color='#a56868',ms=5,clip_on=False)
    if not any(support):axes[1].text(.5,.55,'All path supports are zero\nSource ranking unavailable',transform=axes[1].transAxes,ha='center',va='center',color='#855454')
    axes[1].set(xticks=range(n),xticklabels=labels,ylim=(0,1.05),ylabel='Weakest directional support',title='Evidence is separate from influence')
    save(fig,folder,'path_influence_evidence');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(5,4.8),constrained_layout=True)
    values=principal['attribution']['coalition_values'];counts=collections.Counter(values)
    axes[0].bar([str(k) for k in sorted(counts)],[counts[k] for k in sorted(counts)],color='#477e9c')
    axes[0].set(xlabel='Computed coalition outcome',ylabel='Number of coalitions',title='All selected-path coalitions')
    endpoint_label='Endpoint (=null)' if principal['reference_sensitivity']['factual_null']['references']==principal['reference_sensitivity']['domain_endpoint_stress']['references'] else 'Endpoint stress'
    refs={'Declared':principal['attribution'],'Factual null':principal['reference_sensitivity']['factual_null'],
          endpoint_label:principal['reference_sensitivity']['domain_endpoint_stress'],'Four paths':principal['path_selection_sensitivity']['four_paths']}
    for i,(label,record) in enumerate(refs.items()):
        y=np.asarray(record['phi']);offset=np.linspace(-.12,.12,len(y))
        axes[1].scatter(i+offset,y,color='#387f86',alpha=.75,s=25)
    axes[1].axhline(0,lw=.8,color='#888888');axes[1].set(xticks=range(4),xticklabels=list(refs),ylabel='Path allocations',title='Reference / path-set sensitivity')
    axes[1].tick_params(axis='x',rotation=25)
    save(fig,folder,'coalition_sensitivity');plt.close(fig)


def main(root):
    root,run,result=paths(root);folder=root/'figures/v2';folder.mkdir(exist_ok=True);settings()
    application=application_record(root,run)
    if application.exists():
        app=json.loads(application.read_text());network(app,folder);application_plots(app,folder)
    summary=result/'test_summary.json'
    if summary.exists():benchmark(json.loads(summary.read_text()),folder)


if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else '.')
