"""Rebuild publication vectors from curated tables; generate curves after freeze."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .runtime import PROJECT,artifact_root,read_json,atomic_json,file_hash,Ledger

COLORS={'fixed':'#0072B2','diagnostic':'#009E73','random':'#E69F00','oracle':'#333333',
        'dcdi':'#CC79A7','data_only':'#56B4E9','additive_fixed':'#D55E00','llm_edit':'#CC79A7'}
FIGURE_WIDTH=12.2/2.54  # Official svproc.cls text width; no illegible downscaling.
MARKERS={'fixed':'o','diagnostic':'^','random':'s','oracle':'D','dcdi':'P','data_only':'X','llm_edit':'v'}
DISPLAY={'fixed':'Fixed','diagnostic':'Diagnostic','random':'Random','oracle':'Oracle fit',
         'dcdi':'DCDI','data_only':'Data only','llm_edit':'LLM edit','truth':'Reference'}

def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.labelsize':8.5,
                         'axes.titlesize':9,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,
                         'svg.fonttype':'none','svg.hashsalt':'sem-update-v1','axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','savefig.facecolor':'white'})

def save(fig,name):
    folder=PROJECT/'paper/figures'
    folder.mkdir(exist_ok=True,parents=True)
    for suffix in ('pdf','svg'):
        metadata={'CreationDate':None,'ModDate':None} if suffix=='pdf' else {'Date':None}
        fig.savefig(folder/(name+'.'+suffix),metadata=metadata)
    fig.savefig(artifact_root()/'figures_preview'/(name+'.png'),dpi=300)
    import matplotlib.pyplot as plt
    plt.close(fig)

def overview():
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig,ax=plt.subplots(figsize=(FIGURE_WIDTH,4.4))
    ax.set(xlim=(0,10),ylim=(0,10)); ax.axis('off')
    boxes=[(.2,8.4,4.3,1.05,'Public metadata\nFrozen local LLM'),(5.5,8.4,4.3,1.05,'Fit / early-stop data\nIndependent disturbances'),
           (2.8,6.4,4.4,1.15,'Current valid DAG\nConditional-flow cache'),
           (.2,4.5,4.3,1.05,'Search-split disturbances\nPrioritize valid edits'),
           (5.5,4.5,4.3,1.05,'Fit candidates; score\nNLL + SW₁ + edge cost'),
           (.2,1.,4.3,1.1,'One-time audit\nSelected vs initial'),
           (5.5,1.,4.3,1.1,'Locked final tests\nT1 / T2 primary / T3')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',facecolor='#F1F5F8',edgecolor='#555555',linewidth=.7))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8)
    for start,end in [((2.35,8.3),(3.8,7.65)),((7.65,8.3),(6.2,7.65)),
                      ((3.8,6.3),(2.35,5.65)),((4.6,5.02),(5.4,5.02)),
                      ((7.65,5.65),(6.2,6.3)),((5.9,4.4),(3.1,2.2)),
                      ((4.6,1.55),(5.4,1.55))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#444444','lw':.9})
    ax.text(5.,9.85,'Disturbance-guided model repair',ha='center',weight='bold')
    ax.text(7.3,3.85,'12 DAGs maximum\n4 search rounds',ha='center',fontsize=8)
    ax.plot([.05,9.85],[2.8,2.8],color='#999999',lw=.6,ls='--')
    ax.text(5.5,2.95,'One-time audit boundary',color='#666666',fontsize=8)
    ax.text(5.,.25,'Disjoint data roles; final outcomes excluded from selection',ha='center',fontsize=8)
    fig.tight_layout(pad=.4)
    save(fig,'F1_method')

def graph_figure(run_id,name):
    import matplotlib.pyplot as plt
    import networkx as nx
    from matplotlib.lines import Line2D
    path=PROJECT/'results/curated/graphs'/(name+'.json')
    if path.exists():
        inputs=read_json(path)
        if inputs['run_id']!=run_id:
            raise ValueError('curated graph example changed')
    else:
        selection_path=artifact_root()/'runs'/run_id/'selection.json'
        selection=read_json(selection_path)
        index=read_json(PROJECT/'results/curated/run_index.json')['runs']
        info=next(r for r in index if r['run_id']==run_id)
        root=artifact_root()/'data/processed'/info['data_id']
        reference=read_json(root/'truth.json')['graph'] if info['study']!='real' else {'d':6,'edges':[[0,3],[1,3],[2,3],[4,5]]}
        moves=[{**selection['candidates'][e['after']]['edit'],'round':e['round'],'score_change':e['score_change']}
               for e in selection['edits'] if e['accepted']]
        inputs={'run_id':run_id,'d':info['d'],'study':info['study'],'selection_sha256':file_hash(selection_path),
                'reference':reference,'initial':selection['candidates'][selection['initial']]['graph'],
                'selected':selection['candidates'][selection['selected']]['graph'],
                'before_audit':selection['candidates'][selection['before_audit']]['graph'],
                'audit_pass':selection['audit']['pass'],'accepted_moves':moves,'edits':selection['edits'],
                'positions':{str(k):v.tolist() for k,v in nx.circular_layout(range(info['d'])).items()}}
        atomic_json(path,inputs)
    initial,selected,before,reference=(inputs[k] for k in ('initial','selected','before_audit','reference'))
    original=set(map(tuple,initial['edges']))
    positions={int(k):np.array(v) for k,v in inputs['positions'].items()}
    panels=[('Initial',initial,False),('Returned after audit',selected,True),
            ('Synthetic reference' if inputs['study']!='real' else 'Physical reference',reference,False)]
    if not inputs['audit_pass']:
        panels.insert(1,('Rejected before return',before,True))
    fig,axes=plt.subplots(2,2,figsize=(FIGURE_WIDTH,4.7))
    for ax in axes.flat:
        ax.axis('off')
    for ax,(title,g,difference) in zip(axes.flat,panels):
        graph=nx.DiGraph(); graph.add_nodes_from(range(inputs['d'])); graph.add_edges_from(g['edges'])
        nx.draw_networkx_nodes(graph,positions,ax=ax,node_size=240,node_color='white',edgecolors='#333333',linewidths=.7)
        nx.draw_networkx_labels(graph,positions,ax=ax,labels={j:f'V{j}' for j in range(inputs['d'])},font_size=8)
        for edge in graph.edges:
            added=difference and edge not in original
            nx.draw_networkx_edges(graph,positions,ax=ax,edgelist=[edge],edge_color='#009E73' if added else '#0072B2',
                                   style='dashdot' if added else 'solid',arrowsize=12,width=1.2,node_size=240,connectionstyle='arc3,rad=0.06')
        if difference:
            for edge in original-set(map(tuple,g['edges'])):
                nx.draw_networkx_edges(nx.DiGraph([edge]),positions,ax=ax,edgelist=[edge],edge_color='#E69F00',style='dashed',
                                       arrowsize=12,width=1.1,node_size=240,connectionstyle='arc3,rad=-0.12')
        ax.set_title(title); ax.axis('off')
    details=[]
    for move in inputs['accepted_moves']:
        details.append(f"r{move['round']+1}: {move['operation']} V{move['source']}→V{move['target']}, ΔS={move['score_change']:+.3f}")
    import textwrap
    caption=(' | '.join(details) or 'No accepted search edits')+f"; audit {'passed' if inputs['audit_pass'] else 'rejected repair'}"
    fig.text(.5,.035,'\n'.join(textwrap.wrap(caption,68)),ha='center',fontsize=8)
    fig.legend(handles=[Line2D([0],[0],color='#0072B2',label='Retained/reference'),Line2D([0],[0],color='#009E73',ls='-.',label='Added'),
                        Line2D([0],[0],color='#E69F00',ls='--',label='Removed (overlay)')],loc='upper center',ncol=2,bbox_to_anchor=(.5,.99),frameon=False)
    fig.subplots_adjust(left=.03,right=.97,top=.83,bottom=.19,hspace=.3)
    save(fig,name)

@torch.no_grad()
def make_responses(run_id):
    from .data import load_learner,SyntheticSCM
    from .graphs import DAG
    from .training import fit_graph
    path=PROJECT/'results/curated/response_curves.csv'
    if path.exists():
        table=pd.read_csv(path)
        if set(table.run_id)!={run_id}:
            raise ValueError('curated response example changed')
        return table
    index=read_json(PROJECT/'results/curated/run_index.json')['runs']
    info=next(r for r in index if r['run_id']==run_id)
    root=artifact_root()/'data/processed'/info['data_id']
    data=load_learner(root,'cuda')
    selection=read_json(artifact_root()/'runs'/run_id/'selection.json')
    true=SyntheticSCM(info['d'],info['family'],info['seed'],info['study']=='semantic')
    mu=torch.tensor(data.manifest['standardization']['mean'],device='cuda')
    sd=torch.tensor(data.manifest['standardization']['std'],device='cuda')
    edges=[e for e in true.graph.edges if e[0] in data.manifest['seen_targets']]
    pairs=edges[:2]
    if len(pairs)<2:
        for target in data.manifest['seen_targets']:
            for outcome in range(data.d):
                if target!=outcome and (target,outcome) not in pairs:
                    pairs.append((target,outcome))
        pairs=pairs[:2]
    graphs={name:DAG.from_json(selection['candidates'][selection[key]]['graph']) for name,key in [('fixed','initial'),('diagnostic','selected')]}
    graphs['oracle']=true.graph
    models={name:fit_graph(data,g,selection['identity']['train'],'flow',allow_training=False)[0] for name,g in graphs.items()}
    rows=[]
    raw_curves={}
    ledger=Ledger()
    job='response-curves-'+run_id
    ledger.claim(job,{'run':run_id,'pairs':pairs,'grid':21,'samples':2048},expected_seconds=120)
    with ledger.device_interval(job):
        for target,outcome in pairs:
            fitting_values=torch.cat([e.x[:,target] for e in data.get('fit') if target in e.targets])
            fitting_low,fitting_high=fitting_values.min().item(),fitting_values.max().item()
            for setting_index,setting in enumerate(np.linspace(-2,2,21)):
                generator=torch.Generator(device='cuda').manual_seed(info['seed']+90811+target)
                noises=torch.randn(2048,info['d'],generator=generator,device='cuda')
                outputs={name:model.sample_intervention(noises,{target:float(setting)})[:,outcome] for name,model in models.items()}
                actual=true.sample(2048,info['seed']+90811+target,
                      {target:{'kind':'fixed','value':float(mu[target]+setting*sd[target])}},device='cuda',noises=noises)
                outputs['truth']=(actual[:,outcome]-mu[outcome])/sd[outcome]
                for name,y in outputs.items():
                    raw_curves[f'target{target}_outcome{outcome}_grid{setting_index}_{name}']=y.cpu().numpy()
                    lo,hi=torch.quantile(y,torch.tensor([.05,.95],device='cuda'))
                    rows.append({'run_id':run_id,'model':name,'target':target,'outcome':outcome,'setting':float(setting),
                                 'mean':y.mean().item(),'predictive_q05':lo.item(),'predictive_q95':hi.item(),
                                 'fitting_intervention_min':fitting_low,'fitting_intervention_max':fitting_high,
                                 'monte_carlo_se':y.std().item()/np.sqrt(len(y)),'samples':len(y)})
    sample_path=artifact_root()/'generated_samples'/('response-curves-'+run_id+'.npz')
    np.savez_compressed(sample_path,**raw_curves)
    frame=pd.DataFrame(rows); frame.to_csv(path,index=False)
    atomic_json(PROJECT/'results/curated/response_generation.json',{'run_id':run_id,
                'samples_artifact':str(sample_path.relative_to(artifact_root())),
                'samples_sha256':file_hash(sample_path),'table_sha256':file_hash(path),
                'pairs':pairs,'grid':np.linspace(-2,2,21).tolist(),'samples_per_point':2048,
                'noise_seed_formula':'SCM seed + 90811 + intervention target',
                'common_noises_across_settings_and_models':True,'device':'cuda'})
    ledger.finish(job)
    return frame

def response_plot(table):
    import matplotlib.pyplot as plt
    pairs=list(table[['target','outcome']].drop_duplicates().itertuples(index=False,name=None))
    fig,axes=plt.subplots(len(pairs),1,figsize=(FIGURE_WIDTH,4.7),squeeze=False)
    for ax,(target,outcome) in zip(axes.flat,pairs):
        part=table[(table.target==target)&(table.outcome==outcome)]
        for method in ('truth','fixed','diagnostic','oracle'):
            m=part[part.model==method].sort_values('setting')
            color='#333333' if method=='truth' else COLORS[method]
            ax.plot(m.setting,m['mean'],label=DISPLAY[method],color=color,ls={'truth':'-.','fixed':'--','diagnostic':'-','oracle':':'}[method],lw=1.3)
            if method=='diagnostic':
                ax.fill_between(m.setting,m.predictive_q05,m.predictive_q95,color=color,alpha=.12,label='90% predictive interval')
        ax.set(title=f'do(V{target}) → V{outcome}',xlabel='Fixed setting (observational SD)',ylabel='Outcome (observational SD)')
        low,high=part.iloc[0][['fitting_intervention_min','fitting_intervention_max']]
        ax.axvspan(-2,low,color='#999999',alpha=.07)
        ax.axvspan(high,2,color='#999999',alpha=.07)
        ax.axvline(1,color='#AAAAAA',lw=.6,ls=':')
        ax.set_xlim(-2,2)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,0,1,.90)); save(fig,'F3_intervention_responses')

def performance(frame):
    import matplotlib.pyplot as plt
    table=frame[(frame.study=='controlled')&(frame.stage=='selected')&(frame.endpoint=='T2')]
    plotted=[]
    aggregates=[]
    for d in sorted(table.d.unique()):
        fig,axes=plt.subplots(3,2,figsize=(FIGURE_WIDTH,6.7),sharex=True,sharey='row')
        for fi,family in enumerate(('linear','nonlinear','heteroscedastic')):
            for bi,budget in enumerate((100,400)):
                ax=axes[fi,bi]
                part=table[(table.d==d)&(table.family==family)&(table.budget==budget)]
                for (corruption,seed),points in part[(part.corruption>0)&part.method.isin(['fixed','random','diagnostic'])].groupby(['corruption','seed']):
                    values=points.set_index('method').sw1.reindex(['fixed','random','diagnostic'])
                    ax.plot(corruption+np.array([-.022,0,.022]),values,color='#BBBBBB',lw=.5,zorder=0)
                for mi,method in enumerate(('fixed','random','diagnostic')):
                    m=part[(part.method==method)&(part.corruption>0)]
                    for corruption,points in m.groupby('corruption'):
                        x=float(corruption)+(mi-1)*.022
                        ax.scatter(np.full(len(points),x),points.sw1,s=10,marker=MARKERS[method],alpha=.65,color=COLORS[method])
                        plotted.extend({'run_id':r.run_id,'d':d,'family':family,'budget':budget,'corruption':corruption,
                                        'method':method,'seed':r.seed,'x':x,'sw1':r.sw1}
                                       for r in points.itertuples())
                        vals=points.sw1.to_numpy()
                        rng=np.random.default_rng(81123)
                        boot=rng.choice(vals,(2000,len(vals)),replace=True).mean(1)
                        mean=vals.mean(); low,high=np.quantile(boot,[.025,.975])
                        ax.errorbar(x,mean,yerr=[[mean-low],[high-mean]],fmt=MARKERS[method],ms=3,color=COLORS[method],capsize=2,
                                    label=DISPLAY[method] if corruption==.2 else None)
                        aggregates.append({'d':d,'family':family,'budget':budget,'corruption':corruption,'method':method,
                                           'mean':mean,'low':low,'high':high,'n_scms':len(vals),
                                           'interval_type':'descriptive SCM bootstrap, 2000 replicates'})
                for method in ('oracle','dcdi','data_only'):
                    values=part[part.method==method].sw1
                    if len(values):
                        ax.axhline(values.mean(),color=COLORS[method],ls={'oracle':':','dcdi':'--','data_only':'-.'}[method],lw=.8,label=DISPLAY[method])
                        ax.axhspan(values.min(),values.max(),color=COLORS[method],alpha=.035)
                        aggregates.append({'d':d,'family':family,'budget':budget,'corruption':-1,'method':method,
                                           'mean':values.mean(),'low':values.min(),'high':values.max(),'n_scms':len(values),
                                           'interval_type':'observed SCM range, not a confidence interval'})
                shd=part[(part.method=='fixed')&(part.corruption>0)].groupby('corruption').realized_initial_shd.mean()
                ax.set_title(f'{family}; d={d}, B={budget}\nMean SHD: '+', '.join(f'{k:g}→{v:.1f}' for k,v in shd.items()),fontsize=8)
                ax.set_xticks([.2,.5]); ax.set_ylabel('T2 SW₁ ↓')
                if fi==2: ax.set_xlabel('Nominal corruption')
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False)
        fig.tight_layout(rect=(0,0,1,.93)); save(fig,f'F4_performance_d{d}')
    pd.DataFrame(plotted).to_csv(PROJECT/'results/curated/F4_points.csv',index=False)
    pd.DataFrame(aggregates).to_csv(PROJECT/'results/curated/F4_summaries.csv',index=False)

def reliability(frame):
    import matplotlib.pyplot as plt
    from .evaluation import paired_results
    core=frame[(frame.study=='controlled')&(frame.corruption>0)]
    selected=paired_results(core)
    before=paired_results(core,stage='before_audit')
    fig,axes=plt.subplots(3,1,figsize=(FIGURE_WIDTH,6.3))
    counts,edges,_=axes[0].hist(selected.delta,bins=20,color=COLORS['diagnostic'],alpha=.7)
    pd.DataFrame({'bin_low':edges[:-1],'bin_high':edges[1:],'count':counts.astype(int)}).to_csv(
        PROJECT/'results/curated/F5_histogram.csv',index=False)
    axes[0].axvline(0,color='black',lw=.8)
    axes[0].set(xlabel='Δ T2 SW₁ (repair − initial)',ylabel='Paired conditions')
    labels=['beneficial','neutral','harmful']
    outcome_rows=[]
    for offset,p,label,color in [(-.18,before,'Before audit','#56B4E9'),(.18,selected,'After audit','#009E73')]:
        counts=p.outcome.value_counts().reindex(labels,fill_value=0)
        outcome_rows.extend({'stage':label,'outcome':key,'paired_conditions':int(value)} for key,value in counts.items())
        axes[1].bar(np.arange(3)+offset,counts,width=.35,label=label,color=color,hatch='///' if label=='Before audit' else '')
    axes[1].set_xticks(range(3),labels); axes[1].set_ylabel('Paired conditions'); axes[1].legend(frameon=False)
    for method in ('diagnostic','random'):
        part=core[(core.stage=='selected')&(core.endpoint=='T2')&(core.method==method)]
        axes[2].scatter(part.canonical_optimizer_updates/1000,part.sw1,s=10,marker=MARKERS[method],alpha=.5,label=DISPLAY[method],color=COLORS[method])
    axes[2].set(xlabel='Required fitting updates (thousands)',ylabel='T2 SW₁ ↓'); axes[2].legend(frameon=False)
    fig.tight_layout(); save(fig,'F5_harm_and_cost')
    pd.DataFrame(outcome_rows).to_csv(PROJECT/'results/curated/F5_harm_counts.csv',index=False)
    cost=core[(core.stage=='selected')&(core.endpoint=='T2')&core.method.isin(['diagnostic','random'])]
    cost[['run_id','method','d','family','seed','budget','corruption','canonical_optimizer_updates',
          'sw1','method_component_seconds','wall_seconds','peak_vram_bytes']].to_csv(
        PROJECT/'results/curated/F5_cost_points.csv',index=False)
    selected.to_csv(PROJECT/'results/curated/paired_repairs.csv',index=False)
    return selected

def export_paper(plots_only=False):
    if not (PROJECT/'results/curated/evaluation_complete.json').exists():
        raise RuntimeError('cannot draw experimental figures before final evaluation completes')
    from .evaluation import paired_results,cluster_interval
    if file_hash(PROJECT/'results/curated/metrics.csv')!=read_json(PROJECT/'results/curated/evaluation_complete.json')['metrics_sha256']:
        raise ValueError('curated metrics changed after final evaluation')
    if plots_only and not all((PROJECT/'results/curated'/name).exists() for name in ('response_curves.csv','real_block_intervals.csv')):
        raise RuntimeError('clean plot export requires the completed curated plotting inputs')
    style()
    frame=pd.read_csv(PROJECT/'results/curated/metrics.csv')
    from .analysis import supplementary_tables
    supplementary_tables(frame)
    overview(); performance(frame)
    paired=reliability(frame)
    # Declared post-evaluation representative: median paired improvement at d5,
    # B400, 50% corruption; choose by run ID to break ties.
    eligible=paired[(paired.d==5)&(paired.budget==400)&(paired.corruption==.5)].sort_values(['delta','run_id_method'])
    example=eligible.iloc[len(eligible)//2].run_id_method
    graph_figure(example,'F2_graphs')
    adverse=paired[paired.outcome=='harmful'].sort_values(['delta','run_id_method'],ascending=[False,True])
    if len(adverse):
        graph_figure(adverse.iloc[0].run_id_method,'F2_adverse')
    else:
        rejected=frame[(frame.method=='diagnostic')&(frame.stage=='selected')&(frame.endpoint=='T2')&(~frame.audit_pass)]
        if len(rejected):
            graph_figure(rejected.sort_values('run_id').iloc[0].run_id,'F2_rejected')
    response_plot(make_responses(example))
    real_response_plot()
    from .real_uncertainty import block_intervals
    block_intervals(frame)
    summaries=[]
    for comparator in ('fixed','random'):
        pairs=paired_results(frame[(frame.study=='controlled')&(frame.corruption>0)],comparator=comparator)
        summaries.append({'study':'controlled','comparison':'diagnostic - '+comparator,**cluster_interval(pairs)})
    semantic=paired_results(frame[frame.study=='semantic'],comparator='llm_edit')
    summaries.append({'study':'semantic','comparison':'diagnostic - llm_edit',**cluster_interval(semantic)})
    summary=pd.DataFrame(summaries)
    summary.to_csv(PROJECT/'results/curated/summary.csv',index=False)
    (PROJECT/'paper/tables').mkdir(exist_ok=True,parents=True)
    printable=summary.rename(columns={'study':'Study','comparison':'Comparison','mean':'Mean',
                                      'low':'CI low','high':'CI high','independent_scms':'SCMs'})
    printable['Comparison']=printable['Comparison'].str.replace('diagnostic','Diag.',regex=False).str.replace('llm_edit','LLM edit',regex=False)
    latex=printable.to_latex(index=False,float_format='%.4f',escape=True)
    (PROJECT/'paper/tables/paired_effects.tex').write_text('% Requires booktabs; generated from summary.csv.\n'+
        '\\begingroup\\setlength{\\tabcolsep}{3pt}\\small\n'+latex+'\\endgroup\n')
    real_table=pd.read_csv(PROJECT/'results/curated/real_block_intervals.csv')
    real_table=real_table[['method','metadata_variant','sw1','conditional_block_low','conditional_block_high']]
    real_table=real_table.rename(columns={'method':'Method','metadata_variant':'Metadata','sw1':'SW1',
                                        'conditional_block_low':'CI low','conditional_block_high':'CI high'})
    latex=real_table.to_latex(index=False,float_format='%.4f',escape=True)
    (PROJECT/'paper/tables/real_case.tex').write_text('% Conditional block intervals: one apparatus, fixed models and generated samples.\n'+
        '\\begingroup\\setlength{\\tabcolsep}{3pt}\\small\n'+latex+'\\endgroup\n')
    atomic_json(PROJECT/'results/curated/figure_manifest.json',{'source_metrics_sha256':file_hash(PROJECT/'results/curated/metrics.csv'),
                'response_table_sha256':file_hash(PROJECT/'results/curated/response_curves.csv'),'representative_run':example,
                'selection_rule':'median d5 B400 c0.5 T2 paired delta; adverse largest harmful delta',
                'intervals':'F3 predictive quantiles; F4 descriptive SCM bootstrap CIs; summary stratified paired cluster bootstrap',
                'F4_baseline_shading':'observed range over five SCMs, not a confidence interval',
                'native_width_cm':12.2,'font_size_pt':[8,9],
                'plotting_tables':{name:file_hash(PROJECT/'results/curated'/name) for name in
                    ('metrics.csv','response_curves.csv','real_response_points.csv','F4_points.csv','F4_summaries.csv',
                     'F5_histogram.csv','F5_harm_counts.csv','F5_cost_points.csv','paired_repairs.csv')},
                'files':{p.name:file_hash(p) for p in (PROJECT/'paper/figures').iterdir() if p.suffix in ('.pdf','.svg')}})
    from .reporting import evidence_report
    if not plots_only:
        evidence_report(frame,summary)

def real_response_plot():
    """Only measured mid/strong regimes; no interpolated real-data observations."""
    import ast
    import matplotlib.pyplot as plt
    frame=pd.read_csv(PROJECT/'results/curated/real_intervention_metrics.csv')
    rows=[]
    for record in frame[frame.endpoint.isin(['T1','T2'])].to_dict('records'):
        nodes=ast.literal_eval(record['non_target_nodes'])
        index=nodes.index(3)  # Audited source-current column, kept for RGB interventions.
        actual=ast.literal_eval(record['outcome_means_actual'])[index]
        predicted=ast.literal_eval(record['outcome_means_generated'])[index]
        color=record['environment'].split('_')[1]
        rows.append({'run_id':record['run_id'],'method':record['method'],'metadata_variant':record['metadata_variant'],
                     'target':color,'regime':record['endpoint'],'actual_current_mean':actual,
                     'predicted_current_mean':predicted,'actual_rows':record['actual_rows']})
    table=pd.DataFrame(rows)
    table.to_csv(PROJECT/'results/curated/real_response_points.csv',index=False)
    fig,axes=plt.subplots(3,1,figsize=(FIGURE_WIDTH,5.9),sharey=True)
    for ax,color in zip(axes,('red','green','blue')):
        part=table[table.target==color]
        actual=part.groupby('regime').actual_current_mean.first().reindex(['T1','T2'])
        ax.scatter([0,1],actual,marker='x',s=30,color='#222222',label='Measured',zorder=5)
        for i,method in enumerate(('fixed','diagnostic','llm_edit')):
            values=part[(part.method==method)&(part.metadata_variant=='coherent')].set_index('regime').predicted_current_mean.reindex(['T1','T2'])
            ax.scatter(np.array([0,1])+(i-1)*.045,values,s=20,marker=MARKERS[method],color=COLORS[method],label=DISPLAY[method])
        ax.set_title(color+' → source current')
        ax.set_xticks([0,1],['Mid (T1)','Strong (T2)'])
        ax.set_ylabel('Mean current (reference SD)')
    axes[-1].set_xlabel('Measured intervention regime')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=2,frameon=False)
    fig.tight_layout(rect=(0,0,1,.92)); save(fig,'F3_real_regime_points')
