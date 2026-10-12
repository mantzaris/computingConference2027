"""Publication SVG/PDF networks and quantitative figures from frozen results only."""
import csv,html,json,math,os,re,subprocess,textwrap
from pathlib import Path
os.environ['MPLCONFIGDIR']=str(Path(__file__).resolve().parents[2]/'.cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch,Polygon
import numpy as np
import networkx as nx
import xml.etree.ElementTree as ET
from .structural_programs import SCM,equation
from .attribution import coalitions
from .budget import atomic_json

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','axes.titlesize':11,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9})
COLORS={'positive':'#176D89','negative':'#B45135','ink':'#243449','muted':'#708092','purple':'#62488D'}


def quoted(value):return json.dumps(str(value),ensure_ascii=False)
def lines(text,width):return '<BR/>'.join(html.escape(x) for x in textwrap.wrap(str(text),width=width,break_long_words=False))


def graph_dot(record,states=None,intervention=None,rank_capacity=None):
    scm=SCM(record['model']);states=states or scm.solve();idx={n:'E%02d'%(i+1) for i,n in enumerate(scm.order)};outcome=scm.model['outcome']
    paths=record['selection']['paths'];shares=record['attribution']['phi']
    highlighted=max(range(len(paths)),key=lambda i:(abs(shares[i]),-i)) if paths else None
    highlighted_edges=set(zip(paths[highlighted],paths[highlighted][1:])) if highlighted is not None else set()
    participation={n:sum(n in p for p in paths) for n in scm.order}
    source_reviews={r['id']:r for r in record.get('final_source_review',{}).get('audits',[])}
    alias_flags={r['node_id']:r for r in record.get('source_alias_flags',[])}
    dot=['digraph G {','graph [rankdir=TB, bgcolor="white", margin=0, pad="0.10", nodesep="0.16", ranksep="0.22", splines=polyline, outputorder=edgesfirst, fontname="DejaVu Sans"];',
         'node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=12, margin="0.07,0.05", penwidth=1.1];',
         'edge [fontname="DejaVu Sans", fontsize=12, arrowsize=0.65, penwidth=1.1, color="#708092"];']
    for ident in scm.order:
        n=scm.nodes[ident];is_target=ident==outcome
        critique=source_reviews.get(ident,{})
        flagged=bool(critique.get('event_support')=='unsupported' or critique.get('story_time')=='contradicted' or critique.get('reference_semantics')=='inconsistent' or critique.get('duplicates') or critique.get('parent_order_flags') or ident in alias_flags)
        fill='#25384E' if is_target else '#EDF5F8' if n['parents'] else '#F5F0E5';font='white' if is_target else COLORS['ink']
        if intervention and ident in intervention:fill='#F8E4D6';font=COLORS['ink']
        shape='box'
        source=n.get('verified_citations',[{}])[0].get('source_id','assumption')
        label=n.get('label',ident);actor=n.get('actor','context unspecified')
        short_source=re.sub(r's0?(\d+)e0?(\d+)',r'S\1E\2',source)
        # Labels already name the event/actor or faction; complete actor context
        # remains in the index. Repeating it here made long chains illegible.
        actor_line=''
        state=('B'+str(states[ident])) if n['type']=='bool' else 'C'+str(n['values'].index(states[ident])) if n['type']=='category' else n['type']
        node_code=idx[ident]+(' !' if flagged else '')
        metadata='<B>'+node_code+'</B> · '+html.escape(state)+' · '+html.escape(short_source)
        if is_target:
            t=n.get('time');endpoint=('S%dE%d'%(t//100,t%100)) if isinstance(t,int) else 'time unresolved'
            metadata='<B>'+node_code+'</B> · '+html.escape(state)+' · '+endpoint
        content='<B>'+lines(label,18)+'</B><BR/><FONT POINT-SIZE="12">'+metadata+'</FONT>'
        junction=participation[ident]>1 and scm.graph.in_degree(ident)>1
        tooltip=n.get('definition','')+' | Equation: '+equation(n['expr'])+' | Reference: '+n.get('reference_meaning','')+' | Final source critique: '+critique.get('reason','not independently reviewed')
        dot.append(quoted(ident)+' [label=<'+content+'>, shape='+shape+', fillcolor='+quoted(fill)+', fontcolor='+quoted(font)+', peripheries='+('2' if junction else '1')+', tooltip='+quoted(tooltip)+', color='+quoted('#B45135' if flagged or (intervention and ident in intervention) else '#8A9AAA')+'];')
    edge_index={}
    rank_capacity=rank_capacity or record.get('_layout_row_capacity',2)
    known=all(scm.nodes[n].get('time') is not None for n in scm.order)
    if known:
        generations=[]
        for t in sorted({scm.nodes[n]['time'] for n in scm.order}):
            members=[n for n in scm.order if scm.nodes[n]['time']==t]
            generations.extend(nx.topological_generations(scm.graph.subgraph(members)))
    else:generations=list(nx.topological_generations(scm.graph))
    rows=[]
    for generation in generations:
        ordered=sorted(generation)
        rows.extend(ordered[i:i+rank_capacity] for i in range(0,len(ordered),rank_capacity))
    for row in rows:dot.append('{ rank=same; '+'; '.join(quoted(n) for n in row)+'; }')
    # Invisible constraints place recorded episodes in chronological bands.
    # They are drawing instructions only, never SCM edges or attributed paths.
    for previous,following in zip(rows,rows[1:]):
        dot.append(quoted(previous[0])+' -> '+quoted(following[0])+' [style=invis,weight=100];')
    for i,(a,b) in enumerate(scm.graph.edges):
        evidence=record['edge_evidence'].get(a+'>'+b,{});status=evidence.get('status','unassessed')
        style='solid' if status=='explicit' else 'dashed' if status=='inferred' else 'dotted'
        operator=scm.nodes[b]['expr'].get('op','copy');eid='e%02d'%(i+1);edge_index[eid]={'parent':a,'child':b,'support':evidence.get('score',0),'status':status,'operator':operator}
        # Width is uniform. No summing of duplicated path shares onto shared edges.
        dot.append(quoted(a)+' -> '+quoted(b)+' [label='+quoted(operator)+', tooltip='+quoted(eid+': '+a+' -> '+b+' | '+status+' | evidence score '+str(evidence.get('score',0)))+', style='+quoted(style)+', color='+quoted(COLORS['positive'] if (a,b) in highlighted_edges else '#708092')+'];')
    dot.append('}')
    return '\n'.join(dot),{'node_ids':idx,'nodes':{idx[n]:{'id':n,'definition':scm.nodes[n].get('definition'),'actor':scm.nodes[n].get('actor'),'type':scm.nodes[n]['type'],'time':scm.nodes[n].get('time'),'observed':states[n],'reference':scm.nodes[n]['reference'],'reference_meaning':scm.nodes[n].get('reference_meaning'),'equation':equation(scm.nodes[n]['expr']),'citations':scm.nodes[n].get('verified_citations',[])} for n in scm.order},'edges':edge_index,
                           'highlighted_path':'p%d'%(highlighted+1) if highlighted is not None else None,
                           'final_source_critique':source_reviews,
                           'posthoc_literal_alias_flags':alias_flags,
                           'layout':{'row_capacity':rank_capacity,'rows':rows,'basis':'recorded episode then within-episode dependency layers' if known else 'dependency layers because event time is unresolved','invisible_constraints':'Layout only; excluded from structural graph and all attribution.'},
                           'legend':'Dark: outcome. Cream: external/background boundary. B0/B1: Boolean state; C0, C1, ...: categorical state codes in the index. ! and orange border: unresolved automated source, temporal-order, reference, duplicate, or literal-alias-coverage flag. These are review flags, not independent adjudication. Actor/faction context appears in labels; full context and state meanings are in this index. Teal edges: path with largest absolute allocated share (ID breaks ties), not edge effects. Double border: junction shared by retained paths. Edge style: solid explicit support, dashed inferred, dotted unsupported/unassessed. E numbers link nodes to equations and sources here; edge labels are generated equation operators; edge audit IDs are in SVG tooltips and this index. All widths are uniform.'}


def render_network(record,directory,stem):
    directory=Path(directory);candidates=[]
    for capacity in (2,3):
        dot,index=graph_dot(record,rank_capacity=capacity)
        svg=subprocess.check_output(['dot','-Tsvg'],input=dot.encode());xml=ET.fromstring(svg)
        width=float(xml.attrib['width'].replace('pt',''));height=float(xml.attrib['height'].replace('pt',''))
        minimum=min(float(n.attrib['font-size']) for n in xml.iter() if 'font-size' in n.attrib)
        score=minimum*min(345.8268/width,465/height)
        candidates.append((score,capacity,dot,index,svg))
    score,capacity,dot,index,svg=max(candidates,key=lambda x:(x[0],-x[1]))
    record['_layout_row_capacity']=capacity
    index['layout']['minimum_font_at_manuscript_scale_pt']=score
    source=directory/(stem+'.dot');source.write_text(dot)
    for ext in ('svg','pdf','png'):subprocess.run(['dot','-T'+ext,str(source),'-o',str(directory/(stem+'.'+ext))],check=True)
    atomic_json(directory/(stem+'_index.json'),index)
    return source


def paired_network(record,directory):
    """Compute layout once, then keep identical coordinates in both worlds."""
    directory=Path(directory);scm=SCM(record['model']);factual=scm.solve()
    queries=record['queries'];changing=[q for q in queries if q['changed_nodes']]
    query=max(changing,key=lambda q:len(q['changed_nodes'])) if changing else queries[0]
    do=query['intervention'];changed=scm.solve(interventions=do)
    dot,_=graph_dot(record);layout=json.loads(subprocess.check_output(['dot','-Tjson'],input=dot.encode()))
    positions={obj['name']:[float(v) for v in obj['pos'].split(',')] for obj in layout['objects'] if 'pos' in obj}
    # Use a common Graphviz geometry but redraw concise identical-sized nodes in matplotlib.
    fig,axes=plt.subplots(1,2,figsize=(4.8,5.8))
    node_ids={n:'E%02d'%(i+1) for i,n in enumerate(scm.order)}
    state_codes={n:{v:'C%d'%i for i,v in enumerate(scm.nodes[n]['values'])} for n in scm.order if scm.nodes[n]['type']=='category'}
    xy=np.array(list(positions.values()));extent=xy.max(0)-xy.min(0)
    for ax,state,title in zip(axes,[factual,changed],['Factual\nfixed context','Intervention\n'+', '.join(node_ids[k]+'='+str(v) for k,v in do.items())]):
        # Reuse routed edges as well as node coordinates, so a direct long edge
        # does not disappear behind the intermediate nodes of another path.
        for edge in layout['edges']:
            if edge.get('style')=='invis':continue
            for draw in edge.get('_draw_',[]):
                if draw['op'] not in ('b','B'):continue
                points=draw['points'];codes=[PlotPath.MOVETO]+[PlotPath.CURVE4]*(len(points)-1)
                ax.add_patch(PathPatch(PlotPath(points,codes),fill=False,color='#91A2B2',lw=.8,zorder=1))
            for draw in edge.get('_hdraw_',[]):
                if draw['op'] in ('P','p'):ax.add_patch(Polygon(draw['points'],color='#91A2B2',zorder=1))
        for n,(x,y) in positions.items():
            differs=state[n]!=factual[n];box='#F5DDCA' if differs else '#EAF2F7'
            displayed=state_codes.get(n,{}).get(state[n],str(state[n]))
            ax.text(x,y,node_ids[n]+'\n'+displayed,ha='center',va='center',fontsize=9,bbox={'boxstyle':'round,pad=.28','fc':box,'ec':COLORS['negative'] if n in do else '#73869C','lw':1},zorder=2)
        bb=[float(v) for v in layout['bb'].split(',')]
        ax.set(xlim=(bb[0]-10,bb[2]+10),ylim=(xy[:,1].min()-60,xy[:,1].max()+70));ax.set_title(title,pad=14,fontsize=10);ax.axis('off')
    fig.suptitle(record['case']['name']+'\nSame mechanisms, background and node positions',fontsize=10,y=.99)
    fig.text(.5,.015,'Orange fill: changed state. Border: intervention target.\nNode and category codes are defined in the figure index.',ha='center',fontsize=9)
    fig.subplots_adjust(top=.81,bottom=.08,wspace=.05)
    save(fig,directory,'paired_counterfactual');plt.close(fig)
    atomic_json(directory/'paired_counterfactual_trace.json',{'case':record['case']['id'],'intervention':do,'factual':factual,'counterfactual':changed,'positions':positions,'node_ids':node_ids,'categorical_display_codes':state_codes})


def save(fig,directory,stem):
    for ext in ('svg','pdf','png'):fig.savefig(Path(directory)/(stem+'.'+ext),dpi=180,bbox_inches='tight')


def contributions(record,directory):
    attr=record['attribution'];values=[attr['baseline']]+attr['phi']+[attr['full']];labels=['Ref.']+['P%d'%(i+1) for i in range(len(attr['phi']))]+['Full']
    fig,ax=plt.subplots(figsize=(4.8,3.5));running=attr['baseline']
    for i,value in enumerate(values):
        if i in (0,len(values)-1):bottom=0;color=COLORS['ink']
        else:bottom=running;running+=value;color=COLORS['positive'] if value>=0 else COLORS['negative']
        ax.bar(i,value,bottom=bottom,color=color,width=.65)
        top=bottom+value;ax.text(i,top+(.035 if value>=0 else -.075),format(value,'+.2f') if i not in (0,len(values)-1) else format(value,'.2f'),ha='center',fontsize=9)
        if i<len(values)-1:ax.plot([i+.325,i+1-.325],[top,top],color='#B0BDC9',lw=.7,ls=':')
        if 0<i<len(values)-1 and attr['mc_se'][i-1]>0:
            ax.errorbar(i,top,yerr=attr['mc_se'][i-1],color=COLORS['ink'],capsize=3,fmt='none',lw=.8)
    ax.axhline(0,color='#BDC6D0',lw=.8);ax.set_xticks(range(len(values)));ax.set_xticklabels(labels)
    ax.set_ylabel('Modeled outcome contrast');ax.set_title(record['case']['name']+'\nPath-coalition allocation',loc='left')
    note='Exact coalition allocation; no permutation sampling error.\nStructural assumptions remain unverified.' if attr['method']=='exact' else 'Shared edges activate once. Error bars: permutation MC SE,\nnot uncertainty about the structural model.'
    ax.margins(y=.22);fig.text(.02,.01,note,fontsize=9)
    fig.tight_layout(rect=(0,.12,1,1))
    save(fig,directory,'path_contributions');plt.close(fig)


def benchmark_figure(summary,directory):
    data=[x for x in summary['method_comparison'] if x['split']=='test' and x['condition'] in ('complete','incomplete')]
    if not data:return
    methods=['B0','B1','B2','P'];fig,axes=plt.subplots(1,2,figsize=(4.8,3.3),sharey=True)
    for ax,condition in zip(axes,['complete','incomplete']):
        rows=[next((x for x in data if x['condition']==condition and x['method']==m),None) for m in methods]
        means=[x['score'] if x else np.nan for x in rows];lo=[x['score']-x['ci_low'] if x else 0 for x in rows];hi=[x['ci_high']-x['score'] if x else 0 for x in rows]
        ax.bar(np.arange(4),means,color=['#B8C3CF','#839AB3',COLORS['positive'],COLORS['purple']],width=.65)
        ax.errorbar(np.arange(4),means,yerr=[lo,hi],fmt='none',color=COLORS['ink'],capsize=3,lw=1)
        ax.set_xticks(range(4));ax.set_xticklabels(methods);ax.set_ylim(0,1.08);ax.set_title(condition.capitalize()+' evidence')
        ax.yaxis.grid(True,alpha=.15);ax.set_axisbelow(True)
    axes[0].set_ylabel('Query score (SCM average)');fig.tight_layout();fig.text(.04,-.05,'95% intervals bootstrap independent SCMs;\nparaphrases are averaged within each SCM.',fontsize=9)
    save(fig,directory,'benchmark_performance');plt.close(fig)


def sensitivity(records,directory):
    fig,axes=plt.subplots(len(records),1,figsize=(4.8,max(3,len(records)*2.1)),squeeze=False)
    for ax,record in zip(axes[:,0],records):
        main=record['attribution']['phi'];alt=record['reference_sensitivity']['domain_endpoint_alternative']['phi'];x=np.arange(len(main))
        scm=SCM(record['model']);world=scm.solve(interventions={n:scm.nodes[n]['reference'] for n in record['selection']['source_boundary']})
        coherent=coalitions(scm,record['selection']['paths'],references={(a,b):world[a] for a,b in scm.graph.edges},exact=len(main)<=8)['phi']
        ax.bar(x-.24,main,width=.23,color=COLORS['positive'],label='Declared reference');ax.bar(x,coherent,width=.23,color=COLORS['purple'],label='Boundary-derived reference');ax.bar(x+.24,alt,width=.23,color=COLORS['negative'],label='Domain endpoint stress test')
        ax.axhline(0,lw=.7,color='#777777');ax.set_xticks(x);ax.set_xticklabels(['P%d'%(i+1) for i in x]);ax.set_title(record['case']['name'],loc='left',fontsize=10);ax.set_ylabel('Contribution')
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,frameon=False,fontsize=9,loc='lower center',ncol=1)
    fig.tight_layout(rect=(0,.10,1,1));save(fig,directory,'reference_sensitivity');plt.close(fig)


def render(root):
    root=Path(root);run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id'];directory=root/'figures';directory.mkdir(exist_ok=True)
    chosen=[]
    alias_file=root/'results/source_alias_checks.json'
    alias_findings=json.loads(alias_file.read_text())['findings'] if alias_file.exists() else []
    ordered=[run/'application'/c['id'] for c in json.loads((root/'configs/experiment.json').read_text())['cases']]
    for folder in ordered:
        files=sorted(folder.glob('alternative_*.json'))
        if files:
            record=json.loads(files[0].read_text())
            review=folder/'final_source_review.json'
            if review.exists():record['final_source_review']=json.loads(review.read_text())
            record['source_alias_flags']=[r for r in alias_findings if r['case']==record['case']['id']]
            chosen.append(record);render_network(record,directory,record['case']['id']+'_network')
    if chosen:
        contributions(chosen[0],directory);paired_network(chosen[0],directory);sensitivity(chosen,directory)
    summary=root/'results/summary.json'
    if summary.exists():benchmark_figure(json.loads(summary.read_text()),directory)
    atomic_json(directory/'figure_manifest.json',{'networks':[r['case']['id'] for r in chosen],'software':'Graphviz dot for principal layouts; matplotlib for numeric/paired figures','edge_width':'uniform, never sum of path shares','inspection_status':'pending visual inspection at manuscript scale','main_models':'first accepted alternative by predeclared index'})
    return len(chosen)

if __name__=='__main__':
    import sys
    print('Networks rendered',render(sys.argv[1] if len(sys.argv)>1 else '.'))
