"""SCM-cluster comparisons and publication figures from actual frozen results."""
import itertools
import json
import math
from pathlib import Path
from .runtime import setup
setup()  # Configure project-local plotting caches before importing matplotlib.
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from sem_update.evaluation import cluster_interval
from .runtime import root,PHASE,RESULTS,read_json,atomic_json,file_hash,snapshot

MAIN=['M0','M1','M2','M3','M4','M5']
REPAIRS=['M3','M4','M5','random','rho0','tau0','uniform','llm_edit']
LABELS={'M0':'M0 Marginals','M1':'M1 Ridge SEM','M2':'M2 DCDI-DSF + flows',
        'M3':'M3 Average repair','M4':'M4 Robust repair','M5':'M5 Anchored mixture',
        'fixed':'Fixed G0 flows','random':'Random repair','llm_edit':'LLM-edit adaptation',
        'rho0':'Robust rho=0','tau0':'Mixture tau=0','uniform':'Uniform mixture'}
COLORS=dict(zip(MAIN,['#666666','#0072B2','#D55E00','#009E73','#CC79A7','#E69F00']))
COLORS.update(fixed='#444444',random='#56B4E9',llm_edit='#332288',tau0='#882255',uniform='#44AA99',rho0='#009E73')
MARKERS=dict(zip(MAIN,['o','s','^','D','v','P']))
MARKERS['llm_edit']='X'

def markdown_table(frame):
    columns=list(frame.columns)
    def cell(value):return f'{value:.4f}' if isinstance(value,(float,np.floating)) else str(value)
    return '\n'.join(['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])

def interval(frame,column='sw1',cfg=None):
    cfg=cfg or {'bootstrap_replicates':2000,'bootstrap_seed':261017}
    frame=frame[frame[column].notna()]
    if frame.empty:return {'mean':None,'low':None,'high':None,'independent_scms':0}
    if frame.study.eq('real').all():
        return {'mean':float(frame[column].mean()),'low':None,'high':None,'independent_scms':0}
    return cluster_interval(frame.rename(columns={column:'delta'}),cfg['bootstrap_replicates'],cfg['bootstrap_seed'])

def paired(frame,a,b):
    aa=frame[frame.method==a];bb=frame[frame.method==b]
    columns=['task_id','endpoint','stage']
    result=aa.merge(bb[['task_id','endpoint','stage','sw1']],on=columns,suffixes=('','_reference'),validate='one_to_one')
    result['delta']=result.sw1-result.sw1_reference
    return result

def repair_table(frame,cfg):
    rows=[];pairs=[]
    fixed=frame[(frame.method=='fixed')&(frame.stage=='selected')][['task_id','endpoint','sw1']].rename(columns={'sw1':'initial_sw1'})
    for (study,variant,endpoint,stage,method),part in frame[frame.method.isin(REPAIRS)&frame.endpoint.isin(['T2','T2_exploratory'])].groupby(['study','metadata_variant','endpoint','stage','method']):
        p=part.merge(fixed,on=['task_id','endpoint'],validate='one_to_one')
        p['change']=p.sw1-p.initial_sw1;p['threshold']=np.maximum(.001,.05*p.initial_sw1)
        p['harmful']=(p.change>p.threshold).astype(float);p['beneficial']=(p.change<-p.threshold).astype(float)
        p['outcome']=np.where(p.harmful.eq(1),'harmful',np.where(p.beneficial.eq(1),'beneficial','neutral'))
        p['improvement']=-p.change;p['positive_deterioration']=p.change.clip(lower=0)
        ih=interval(p,'harmful',cfg);ii=interval(p,'improvement',cfg)
        row={'study':study,'metadata_variant':variant,'endpoint':endpoint,'stage':stage,'method':method,
            'conditions':len(p),'independent_scms':ih['independent_scms'],'harmful_count':int(p.harmful.sum()),
            'harmful_frequency':ih['mean'],'harmful_low':ih['low'],'harmful_high':ih['high'],
            'beneficial_count':int(p.beneficial.sum()),'mean_improvement':ii['mean'],'improvement_low':ii['low'],'improvement_high':ii['high'],
            'mean_positive_deterioration':float(p.positive_deterioration.mean()),
            'harmful_severity_mean':float(p.loc[p.harmful.eq(1),'change'].mean()) if p.harmful.any() else 0.,
            'maximum_deterioration':float(max(0.,p.change.max())),
            'maximum_signed_change':float(p.change.max()),'retention_rate':float(p.retained_initial.mean())}
        rows.append(row);pairs.append(p)
    table=pd.DataFrame(rows);table.to_csv(RESULTS/'repair_reliability.csv',index=False)
    full=pd.concat(pairs,ignore_index=True)
    compact=['task_id','study','d','family','seed','budget','corruption','metadata_variant','endpoint','stage','method',
             'sw1','initial_sw1','change','threshold','outcome','harmful','beneficial','improvement','positive_deterioration','retained_initial']
    full[compact].to_csv(RESULTS/'paired_repairs.csv',index=False,float_format='%.9g')
    return table,full

def primary_comparisons(frame,cfg):
    rows=[]
    for a,b in itertools.combinations(MAIN,2):
        p=paired(frame,a,b);ic=interval(p,'delta',cfg)
        unit=p.groupby(['family','d','seed']).delta.mean().to_numpy()
        # Exact paired sign randomization of independent SCM means. With 15
        # systems all 32768 signs are enumerated; conditions are never flipped.
        if len(unit)<=20:
            bits=((np.arange(2**len(unit),dtype=np.uint32)[:,None]>>np.arange(len(unit)))&1)*2.-1
            null=bits@unit/len(unit);pv=float((np.abs(null)>=abs(unit.mean())-1e-14).mean())
        else:
            rng=np.random.default_rng(cfg['bootstrap_seed']);null=rng.choice([-1,1],(100000,len(unit)))@unit/len(unit)
            pv=float((1+(np.abs(null)>=abs(unit.mean())-1e-14).sum())/(len(null)+1))
        rows.append({'comparison':a+' - '+b,'a':a,'b':b,**ic,'paired_conditions':len(p),'p_sign_randomization':pv})
    result=pd.DataFrame(rows);order=np.argsort(result.p_sign_randomization.to_numpy());adjusted=np.empty(len(result));previous=0.
    for rank,i in enumerate(order):
        previous=max(previous,min(1.,(len(result)-rank)*result.iloc[i].p_sign_randomization));adjusted[i]=previous
    result['p_holm']=adjusted;result.to_csv(RESULTS/'primary_comparisons.csv',index=False);return result

def method_table(frame,cfg):
    rows=[]
    for (study,variant,endpoint,method),part in frame[(frame.stage=='selected')&~frame.method.str.startswith('checkpoint_')].groupby(['study','metadata_variant','endpoint','method']):
        result=interval(part,'sw1',cfg)
        row={'study':study,'metadata_variant':variant,'endpoint':endpoint,'method':method,'label':LABELS[method],
            'conditions':len(part),**result,**{k:float(part[k].mean()) if part[k].notna().any() else None for k in
            ['energy','energy_score','mean_effect_rmse','worst_regime_sw1','coverage_90','width_90','nll','fitting_updates',
             'flow_fit_seconds','discovery_seconds','logical_seconds','actual_incremental_seconds','prediction_seconds',
             'metric_seconds','selection_seconds','peak_vram_bytes','coverage_50','width_50','shd','precision','recall','f1',
             'candidate_count','discovery_updates'] if k in part}}
        row['maximum_peak_vram_bytes']=int(part.peak_vram_bytes.max())
        row['graph_defined_conditions']=int(part.shd.notna().sum()) if 'shd' in part else 0
        if method in ['M5','tau0','uniform']:
            # Do not average graph recovery over only the data-dependent subset
            # that collapsed to a single graph or returned G0 after an audit.
            for metric in ['shd','precision','recall','f1']:row[metric]=None
            row['graph_metric_scope']='N/A for predictive mixture method; per-returned-DAG rows retained in metrics'
        else:row['graph_metric_scope']='returned DAG where a synthetic reference exists'
        rows.append(row)
    summary=pd.DataFrame(rows);summary.to_csv(RESULTS/'method_summary.csv',index=False)
    table=summary[(summary.study=='controlled')&(summary.endpoint=='T2')&summary.method.isin(MAIN)].set_index('method').loc[MAIN].reset_index()
    table.to_csv(PHASE/'paper/tables/six_methods.csv',index=False)
    return summary,table

def checkpoint_table(frame,cfg):
    part=frame[(frame.study=='controlled')&(frame.stage=='selected')&(frame.endpoint=='T2')&frame.method.str.startswith('checkpoint_')]
    rows=[];points=[]
    for (axis,limit),group in part.groupby(['checkpoint_axis','checkpoint_limit']):
        a=group[group.method.str.startswith('checkpoint_diagnostic')]
        b=group[group.method.str.startswith('checkpoint_random')]
        common=set(a.task_id)&set(b.task_id)
        for label,data in [('diagnostic',a),('random',b)]:
            data=data[data.task_id.isin(common)]
            if data.empty:continue
            rows.append({'axis':axis,'limit':limit,'policy':label,'conditions':len(data),**interval(data,'sw1',cfg),
                         'achieved_updates':float(data.fitting_updates.mean()),'achieved_fit_seconds':float(data.flow_fit_seconds.mean())})
            points.extend(data.to_dict('records'))
    out=pd.DataFrame(rows);out.to_csv(RESULTS/'checkpoint_summary.csv',index=False)
    compact=['task_id','family','d','seed','budget','corruption','method','checkpoint_axis','checkpoint_limit','sw1','fitting_updates','flow_fit_seconds']
    pd.DataFrame(points)[compact].to_csv(RESULTS/'checkpoint_points.csv',index=False,float_format='%.9g');return out

def sign_probability(values,seed=261017):
    """Two-sided paired randomization; one sign per independent SCM."""
    values=np.asarray(values,dtype=float)
    if not len(values):return None
    if len(values)<=20:
        signs=((np.arange(2**len(values),dtype=np.uint32)[:,None]>>np.arange(len(values)))&1)*2.-1
        return float((np.abs(signs@values/len(values))>=abs(values.mean())-1e-14).mean())
    rng=np.random.default_rng(seed)
    null=rng.choice([-1,1],(100000,len(values)))@values/len(values)
    return float((1+(np.abs(null)>=abs(values.mean())-1e-14).sum())/(len(null)+1))

def holm(values):
    values=np.asarray(values,dtype=float);order=np.argsort(values);out=np.empty(len(values));previous=0.
    for rank,i in enumerate(order):
        previous=max(previous,min(1.,(len(values)-rank)*values[i]));out[i]=previous
    return out

def analysis_tables(frame,summary,pairs,tasks,cfg):
    """Secondary descriptive analyses; never used to select or fit models."""
    selected=frame[(frame.stage=='selected')&~frame.method.str.startswith('checkpoint_')]
    # The main table exposes point estimates for every endpoint. This compact
    # long table adds paired-cluster uncertainty to the additional outcomes.
    columns=['energy_score','mean_effect_rmse','worst_regime_sw1','coverage_90','width_90','shd']
    rows=[]
    for key,part in selected[selected.method.isin(MAIN+['fixed','random','llm_edit'])].groupby(['study','metadata_variant','endpoint','method']):
        for metric in columns:
            if metric not in part or part[metric].notna().sum()==0:continue
            if metric=='shd' and key[3] in ['M5','tau0','uniform']:continue
            rows.append(dict(zip(['study','metadata_variant','endpoint','method'],key))|
                        {'metric':metric,'conditions':int(part[metric].notna().sum()),**interval(part,metric,cfg)})
    pd.DataFrame(rows).to_csv(RESULTS/'secondary_outcomes.csv',index=False,float_format='%.9g')

    # Compare every repair outcome within the same SCM/condition. These are
    # descriptive secondary intervals, not an additional uncorrected family
    # of formal superiority claims.
    rows=[]
    references=[('M4','M3'),('M5','M3'),('M5','M4'),('random','M3'),
                ('rho0','M3'),('tau0','M5'),('uniform','M5')]
    for (study,variant,endpoint,stage),part in pairs.groupby(['study','metadata_variant','endpoint','stage']):
        for a,b in references:
            aa=part[part.method==a];bb=part[part.method==b]
            if aa.empty or bb.empty:continue
            for metric in ['sw1','harmful','positive_deterioration','retained_initial']:
                p=aa.merge(bb[['task_id',metric]],on='task_id',suffixes=('','_reference'),validate='one_to_one')
                p['delta']=p[metric].astype(float)-p[metric+'_reference'].astype(float)
                rows.append({'study':study,'metadata_variant':variant,'endpoint':endpoint,'stage':stage,
                    'comparison':a+' - '+b,'metric':metric,'paired_conditions':len(p),**interval(p,'delta',cfg)})
    pd.DataFrame(rows).to_csv(RESULTS/'repair_comparisons.csv',index=False,float_format='%.9g')

    # All semantic LLM comparisons are paired by SCM, never by metadata variant.
    rows=[]
    semantic=selected[(selected.study=='semantic')&(selected.endpoint=='T2')]
    for variant,part in semantic.groupby('metadata_variant'):
        for a in ['M1','M2','M3','M4','M5','fixed','random']:
            p=paired(part,a,'llm_edit')
            if p.empty:continue
            unit=p.groupby(['family','d','seed']).delta.mean().to_numpy()
            rows.append({'metadata_variant':variant,'comparison':a+' - llm_edit',
                'paired_conditions':len(p),**interval(p,'delta',cfg),
                'p_sign_randomization':sign_probability(unit,cfg['bootstrap_seed'])})
    llm=pd.DataFrame(rows)
    if len(llm):llm['p_holm']=holm(llm.p_sign_randomization)
    llm.to_csv(RESULTS/'semantic_llm_comparisons.csv',index=False,float_format='%.9g')

    # Metadata interventions change proposals, not the underlying independent SCM.
    rows=[]
    for method,part in semantic.groupby('method'):
        for variant in ['anonymous','shuffled']:
            a=part[part.metadata_variant==variant];b=part[part.metadata_variant=='coherent']
            p=a.merge(b[['data_id','sw1']],on='data_id',suffixes=('','_coherent'),validate='one_to_one')
            if p.empty:continue
            p['delta']=p.sw1-p.sw1_coherent
            rows.append({'method':method,'comparison':variant+' - coherent','paired_scms':len(p),**interval(p,'delta',cfg)})
    pd.DataFrame(rows).to_csv(RESULTS/'metadata_comparisons.csv',index=False,float_format='%.9g')

    # A bounded DSF fit remains visible even when it fails the strict constraint.
    datasets={t['data_id']:t for t in tasks};discovery=[]
    for data_id,task in datasets.items():
        r=read_json(root()/'runs/datasets'/data_id/'discovery.json')['discovery']
        discovery.append({k:task[k] for k in ('data_id','study','family','d','seed','budget')}|
            {'converged':r['converged'],'optimization_steps':r['optimization_steps'],
             'h_normalized':r['h_normalized'],'h_raw':r['h_raw'],
             'projected_edges':len(r['projection_removed_edges']),'discovery_seconds':r['seconds'],
             'peak_vram_bytes':r['peak_vram_bytes'],'method':'DCDI-DSF + common flows'})
    dcdi=pd.DataFrame(discovery);dcdi.to_csv(RESULTS/'discovery_coverage.csv',index=False,float_format='%.9g')
    strict=set(dcdi.loc[dcdi.converged.eq(True),'data_id']);rows=[];comparisons=[]
    subset=selected[(selected.study=='controlled')&(selected.endpoint=='T2')&selected.data_id.isin(strict)]
    for method,part in subset[subset.method.isin(MAIN)].groupby('method'):
        rows.append({'method':method,'conditions':len(part),'datasets':part.data_id.nunique(),**interval(part,'sw1',cfg)})
        if method!='M2':
            p=paired(subset,'M2',method)
            comparisons.append({'comparison':'M2 - '+method,'paired_conditions':len(p),**interval(p,'delta',cfg)})
    pd.DataFrame(rows,columns=['method','conditions','datasets','mean','low','high','independent_scms']).to_csv(
        RESULTS/'dcdi_converged_sensitivity.csv',index=False,float_format='%.9g')
    pd.DataFrame(comparisons,columns=['comparison','paired_conditions','mean','low','high','independent_scms']).to_csv(
        RESULTS/'dcdi_converged_comparisons.csv',index=False,float_format='%.9g')

    # A Pareto set describes observed accuracy/time tradeoffs without inventing
    # a utility function, and does not imply statistical efficiency dominance.
    rows=[]
    for (study,variant,endpoint),part in summary[summary.endpoint.isin(['T2','T2_exploratory'])].groupby(['study','metadata_variant','endpoint']):
        for scope,methods in [('six_main',MAIN),('all_reported',list(LABELS))]:
            p=part[part.method.isin(methods)].copy();p['total_seconds']=p.logical_seconds+p.prediction_seconds
            for _,r in p.iterrows():
                dominated=((p['mean']<=r['mean'])&(p.total_seconds<=r.total_seconds)&
                           ((p['mean']<r['mean'])|(p.total_seconds<r.total_seconds))).any()
                rows.append({'study':study,'metadata_variant':variant,'endpoint':endpoint,'scope':scope,
                    'method':r.method,'sw1':r['mean'],'logical_seconds':r.logical_seconds,
                    'prediction_seconds':r.prediction_seconds,'total_seconds':r.total_seconds,
                    'observed_pareto':not dominated,'lowest_observed_error':abs(r['mean']-p['mean'].min())<1e-12})
    pd.DataFrame(rows).to_csv(RESULTS/'accuracy_cost_tradeoffs.csv',index=False,float_format='%.9g')

    # Weights are predictive combination weights, never graph probabilities.
    rows=[]
    for task in tasks:
        raw=read_json(root()/'runs'/task['task_id']/'task.json')
        for method in ['M5','tau0','uniform']:
            m=task['methods'][method];weights=np.asarray(m['weights'])
            optimizer=raw['methods'][method].get('optimizer',{})
            rows.append({k:task[k] for k in ('task_id','study','family','seed','budget','metadata_variant')}|
                {'method':method,'shortlist_components':len(weights),'positive_components':int((weights>0).sum()),
                 'initial_weight_before_audit':float(weights[0]),'largest_weight_before_audit':float(weights.max()),
                 'grid_fallback':bool(optimizer.get('grid_fallback',False)),
                 'optimizer_success':optimizer.get('success') if method!='uniform' else None,
                 'representative_component_before_audit':int(weights.argmax()),'audit_pass':m['audit_pass'],
                 'retained_initial':m['retained_initial'],'effective_components_before_audit':float(1/np.sum(weights**2))})
    pd.DataFrame(rows).to_csv(RESULTS/'mixture_weights.csv',index=False,float_format='%.9g')
    return dcdi

def save(fig,name):
    folder=PHASE/'paper/figures';folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None},bbox_inches='tight',pad_inches=.025)
    fig.savefig(folder/(name+'.svg'),metadata={'Date':None},bbox_inches='tight',pad_inches=.025)
    fig.savefig(folder/(name+'.png'),dpi=200,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)

def setup_plot():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.labelsize':8,'axes.titlesize':8,
        'legend.fontsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'lines.linewidth':1.,'axes.linewidth':.6,
        'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'sem-update-phase2-v1'})

def method_overview(cfg):
    from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
    setup_plot();fig,ax=plt.subplots(figsize=(4.8,2.9));ax.set(xlim=(0,5),ylim=(-.12,3.6));ax.axis('off')
    boxes=[('fit','Fit + early stop\nshared intact flow mechanisms',2.5,3.23,2.55,.47),
        ('search','Search data\n+ graph proposals',.82,2.56,1.38,.48),
        ('bank','Immutable candidate bank\nincludes initial G0',2.5,2.56,1.75,.48),
        ('cal','Calibration data\nno additional fitting',4.18,2.56,1.38,.48),
        ('M3','M3: average\nscore selection',.82,1.68,1.42,.57),
        ('M4',f'M4: robust selection\nρ = {cfg["rho"]:g}',2.5,1.68,1.42,.57),
        ('M5',f'M5: predictive mixture\nτ = {cfg["tau"]:g}',4.18,1.68,1.42,.57),
        ('audit','One audit comparison; rejection returns G0',2.5,.88,3.6,.42),
        ('test','Frozen final prediction: T1 / T2 / T3',2.5,.2,3.6,.42)]
    links=[((2.5,3.),(2.5,2.81)),((1.53,2.56),(1.60,2.56)),
        ((1.99,2.30),(1.12,1.99)),((2.5,2.30),(2.80,1.99)),((3.01,2.30),(4.48,1.99)),
        ((.82,1.36),(1.7,1.11)),((2.5,1.36),(2.5,1.11)),((4.18,1.36),(3.3,1.11)),
        ((2.5,.65),(2.5,.44))]
    for key,label,x,y,w,h in boxes:
        color=COLORS[key] if key in MAIN else '#D6E1E8'
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.025',
            facecolor=color,alpha=.18 if key in MAIN else .55,edgecolor='#34495E',linewidth=.7))
        ax.text(x,y,label,ha='center',va='center',fontsize=8)
    for start,end in links:ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=8,color='#34495E',linewidth=.7))
    ax.plot([4.18,4.18,.82],[2.29,2.13,2.13],color='#777777',ls=':',lw=.8)
    for x in [.82,2.5,4.18]:
        ax.add_patch(FancyArrowPatch((x,2.13),(x,1.99),arrowstyle='-|>',mutation_scale=8,color='#777777',linewidth=.8,linestyle=':'))
    fig.tight_layout(pad=.15);save(fig,'F0_method_overview')
    atomic_json(RESULTS/'F0_plotting.json',{'boxes':boxes,'arrows':links,'rho':cfg['rho'],'tau':cfg['tau'],
        'source':'phase2/results/protocol.json; schematic, no experimental outcome values',
        'scope':'M3/M4/M5 share one bank; M0/M1/M2 are separate main controls'})

def figures(frame,summary,table,reliability,pairs,checkpoints,cfg,curated_only=False):
    setup_plot();core=frame[(frame.study=='controlled')&(frame.stage=='selected')&(frame.endpoint=='T2')]
    fig,axes=plt.subplots(1,3,figsize=(4.8,2.5),sharey=True);points=[]
    for ax,family in zip(axes,cfg['families']):
        for method in MAIN:
            x=[];y=[];lo=[];hi=[]
            for budget in cfg['budgets']:
                r=interval(core[(core.family==family)&(core.method==method)&(core.budget==budget)],'sw1',cfg)
                points.append({'family':family,'budget':budget,'method':method,**r})
                x.append(budget);y.append(r['mean']);lo.append(r['mean']-r['low']);hi.append(r['high']-r['mean'])
            ax.errorbar(x,y,yerr=[lo,hi],color=COLORS[method],marker=MARKERS[method],ms=3,capsize=1,label=method,alpha=.9)
        ax.set_title({'linear':'Linear','nonlinear':'Nonlinear additive','heteroscedastic':'Heteroscedastic'}[family]);ax.set_xticks(cfg['budgets']);ax.set_xlabel('Rows / target');ax.grid(alpha=.15)
    axes[0].set_ylabel('T2 joint SW₁ ↓');axes[1].legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.29),frameon=False)
    fig.tight_layout(w_pad=.6);save(fig,'F1_family_budget')
    pd.DataFrame(points).to_csv(RESULTS/'F1_plotting.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(4.8,2.45))
    for ax,axis,label in zip(axes,['fitting_updates','fit_seconds'],['Fitting-update ceiling','Canonical fitting-time\nceiling (s)']):
        for policy,color in [('diagnostic',COLORS['M3']),('random',COLORS['random'])]:
            p=checkpoints[(checkpoints.axis==axis)&(checkpoints.policy==policy)].sort_values('limit')
            ax.plot(p.limit,p['mean'],marker='o' if policy=='diagnostic' else 's',ms=3,color=color,label=policy)
            ax.fill_between(p.limit,p.low,p.high,color=color,alpha=.12)
        ax.set(xlabel=label,ylabel='T2 joint SW₁ ↓');ax.grid(alpha=.15)
    axes[0].legend(frameon=False);fig.tight_layout();save(fig,'F2_matched_compute')
    fig,axes=plt.subplots(1,2,figsize=(4.8,2.45))
    for _,r in table.iterrows():
        axes[0].errorbar(r.logical_seconds,r['mean'],yerr=[[r['mean']-r.low],[r.high-r['mean']]],
            marker=MARKERS[r.method],color=COLORS[r.method],capsize=2,ms=4)
        offset={'M2':(-27,8),'M3':(12,-7),'M4':(12,8),'M5':(-33,15)}.get(r.method,(4,2))
        axes[0].annotate(r.method,(r.logical_seconds,r['mean']),xytext=offset,textcoords='offset points',fontsize=8,
            arrowprops=dict(arrowstyle='-',lw=.5,color=COLORS[r.method]) if r.method in ['M3','M4','M5'] else None,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=.4))
    axes[0].set(xscale='log',xlabel='Logical construction\n+ selection (s)',ylabel='T2 joint SW₁ ↓')
    r=reliability[(reliability.study=='controlled')&(reliability.stage=='selected')&reliability.method.isin(['M3','M4','M5','random'])]
    for _,v in r.iterrows():
        axes[1].errorbar(v.mean_improvement,v.harmful_frequency,xerr=[[v.mean_improvement-v.improvement_low],[v.improvement_high-v.mean_improvement]],
            yerr=[[v.harmful_frequency-v.harmful_low],[v.harmful_high-v.harmful_frequency]],fmt='o',color=COLORS[v.method],ms=4,capsize=2)
        offset={'M3':(6,10),'M4':(10,-15),'M5':(-26,8),'random':(-30,-15)}[v.method]
        axes[1].annotate(v.method,(v.mean_improvement,v.harmful_frequency),xytext=offset,textcoords='offset points',fontsize=8,
            arrowprops=dict(arrowstyle='-',lw=.5,color=COLORS[v.method]),
            bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=.4))
    axes[1].set(xlabel='Mean improvement over G0 ↑',ylabel='Harmful-repair frequency ↓');axes[1].axvline(0,color='gray',lw=.6)
    for ax in axes:ax.grid(alpha=.15)
    fig.tight_layout();save(fig,'F3_reliability_cost')
    fig,axes=plt.subplots(1,2,figsize=(4.8,2.45),sharey=True);points=[]
    for ax,budget in zip(axes,cfg['budgets']):
        for method in MAIN:
            values=[]
            for corruption in cfg['corruptions']:
                part=core[(core.budget==budget)&(core.corruption==corruption)&(core.method==method)]
                value=interval(part,'sw1',cfg);values.append(value)
                points.append({'budget':budget,'corruption':corruption,'method':method,**value})
            y=np.array([v['mean'] for v in values]);lo=np.array([v['low'] for v in values]);hi=np.array([v['high'] for v in values])
            ax.errorbar(cfg['corruptions'],y,yerr=[y-lo,hi-y],color=COLORS[method],marker=MARKERS[method],ms=3,capsize=1,label=method)
        ax.set(xlabel='Prior corruption fraction',title=f'B = {budget} rows / target');ax.set_xticks(cfg['corruptions']);ax.grid(alpha=.15)
    axes[0].set_ylabel('T2 joint SW₁ ↓');axes[1].legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.28),frameon=False)
    fig.tight_layout();save(fig,'F8_corruption_budget')
    pd.DataFrame(points).to_csv(RESULTS/'F8_plotting.csv',index=False,float_format='%.9g')
    tables=read_json(RESULTS/'selected_models.json')['tasks'];lookup={r['task_id']:r for r in tables}
    pp=pairs[(pairs.study=='controlled')&(pairs.stage=='selected')&(pairs.method=='M3')&(pairs.budget==400)&(pairs.corruption==.5)].sort_values(['change','task_id'])
    example=pp.iloc[len(pp)//2].task_id
    adverse=pairs[(pairs.study=='controlled')&(pairs.stage=='selected')&pairs.method.isin(['M3','M4','M5'])&(pairs.outcome=='harmful')].sort_values(['change','task_id'],ascending=[False,True])
    choices={'representative':example,'adverse':None if adverse.empty else adverse.iloc[0].task_id,
        'adverse_method':None if adverse.empty else adverse.iloc[0].method,
        'adverse_error_change':None if adverse.empty else float(adverse.iloc[0].change),
        'adverse_harm_threshold':None if adverse.empty else float(adverse.iloc[0].threshold)}
    atomic_json(RESULTS/'illustration_choices.json',{**choices,'rule':'median M3 d5/B400/c0.5; largest harmful M3/M4/M5 change'})
    if not curated_only:
        graph_table(lookup[example],'F4_graphs')
        if choices['adverse']:graph_table(lookup[choices['adverse']],'F5_adverse_graphs')
    graph_figure('F4_graphs')
    if choices['adverse']:graph_figure('F5_adverse_graphs')
    return choices

def graph_table(task,name):
    folder=root()/'data/processed'/task['data_id'];truth=read_json(folder/'truth.json')['graph']
    bank=read_json(root()/task['diagnostic_bank_path']);mix=task['methods']['M5'];initial=task['initial_graph']
    components=[bank['candidates'][k]['graph'] for k in mix['shortlist']]
    labels=[('Initial G0',initial),('M3 returned',task['methods']['M3']['selected']['graph']),
            ('M4 returned',task['methods']['M4']['selected']['graph']),('Reference DAG',truth)]
    for i,(g,w) in enumerate(zip(components,mix['weights'])):
        weight='0' if w==0 else f'{w:.1e}' if w<.005 else f'{w:.2f}'
        if g==initial:labels[0]=(f'G0; mixture w={weight}'+('\nrepresentative' if i==int(np.argmax(mix['weights'])) else ''),initial)
        else:labels.append((f'Component {i}; w={weight}'+('\nrepresentative' if i==int(np.argmax(mix['weights'])) else ''),g))
    graph=nx.DiGraph();graph.add_nodes_from(range(task['d']));graph.add_edges_from(truth['edges'])
    pos=nx.spring_layout(graph,seed=518)
    atomic_json(RESULTS/(name+'_plotting.json'),{'task_id':task['task_id'],
        'panels':[{'title':title,'graph':g} for title,g in labels],
        'audit_pass':mix['audit_pass'],'weights_scope':'calibration mixture before audit; rejection returns G0',
        'positions':{str(k):v.tolist() for k,v in pos.items()},
        'edge_widths':'uniform topology; not effect magnitude or graph stability'})

def graph_figure(name):
    table=read_json(RESULTS/(name+'_plotting.json'));pos={int(k):np.array(v) for k,v in table['positions'].items()}
    fig,axes=plt.subplots(2,3,figsize=(4.8,3.4))
    for ax,row in zip(axes.flat,table['panels']):
        title,g=row['title'],row['graph']
        nxg=nx.DiGraph();nxg.add_nodes_from(range(g['d']));nxg.add_edges_from(g['edges'])
        nx.draw_networkx(nxg,pos,ax=ax,node_color='#E8EEF3',node_size=190,font_size=8,width=.7,arrowsize=9,
                         labels={j:f'V{j}' for j in nxg})
        ax.set_title(title);ax.axis('off')
    for ax in list(axes.flat)[len(table['panels']):]:ax.axis('off')
    fig.suptitle('Common positions; mixture weights are predictive'+(' (audit rejected)' if not table['audit_pass'] else ''),fontsize=8)
    fig.tight_layout();save(fig,name)

def latex_tables(table,reliability):
    def esc(text):return str(text).replace('_',r'\_')
    def seconds(value):return f'{value:.3f}' if value<.1 else f'{value:.1f}'
    lines=[r'\begin{tabular}{lrrrr}',r'\hline',r'Method & T2 SW$_1$ [95\% CI] & Fit (s) & Discovery (s) & Predict (s) \\',r'\hline']
    for _,r in table.iterrows():
        lines.append(f"{r.method} & {r['mean']:.4f} [{r.low:.4f}, {r.high:.4f}] & {seconds(r.flow_fit_seconds)} & {seconds(r.discovery_seconds)} & {r.prediction_seconds:.3f}" + r' \\')
    lines+= [r'\hline',r'\end{tabular}']
    (PHASE/'paper/tables/six_methods.tex').write_text('\n'.join(lines)+'\n')
    r=reliability[(reliability.study=='controlled')&(reliability.stage=='selected')]
    r.to_csv(PHASE/'paper/tables/repair_reliability.csv',index=False)
    lines=[r'\begin{tabular}{lrrrr}',r'\hline',r'Repair & Harmful / tasks & Mean gain & Worst harm & Retain G0 \\',r'\hline']
    for name in ['M3','M4','M5','random','rho0','tau0','uniform']:
        q=r[r.method==name].iloc[0]
        lines.append(f'{esc(name)} & {q.harmful_count}/{q.conditions} & {q.mean_improvement:.4f} & {q.maximum_deterioration:.4f} & {100*q.retention_rate:.1f}' + r'\% \\')
    lines+=[r'\hline',r'\end{tabular}'];(PHASE/'paper/tables/repair_reliability.tex').write_text('\n'.join(lines)+'\n')

def llm_audit(tasks):
    from sem_update.graphs import DAG
    counts={};rows=[]
    for task in tasks:
        if not task.get('llm_bank_path'):continue
        bank=read_json(root()/task['llm_bank_path']);total={}
        for move in bank['edits']:
            record=move['proposal_record']
            for key,value in record['counts'].items():total[key]=total.get(key,0)+value
            total['score_rejections']=total.get('score_rejections',0)+move['score_rejections']
            total['accepted_changes']=total.get('accepted_changes',0)+int(move['accepted'])
            generated=read_json(root()/record['path'])
            assert generated['actual_local_generation'] and generated['revision']['device']=='cuda'
            raw_folder=root()/'runs'/('llm-'+generated['identity_hash'][:24])
            for response in generated['records']:
                stem=f"{response['proposal']}-{response['attempt']}"
                assert file_hash(raw_folder/(stem+'.txt'))==response['raw_sha256']
                assert file_hash(raw_folder/(stem+'.prompt.txt'))==response['prompt_sha256']
            graph_events=[DAG.from_json(g).key for r in generated['records'] for g in r['graphs']]
            unique=set(graph_events);evaluated=set(move['evaluated'])
            assert evaluated<=unique
            extra={'raw_queries_verified':len(generated['records']),'evaluated_new_candidates':len(evaluated),
                'validated_unique_proposals_within_round':len(unique),
                'repeated_valid_proposals_across_retry':len(graph_events)-len(unique),
                'valid_unique_proposals_not_evaluated':len(unique-evaluated)}
            for key,value in extra.items():total[key]=total.get(key,0)+value
        rows.append({'task_id':task['task_id'],'study':task['study'],'seed':task['seed'],
                     'metadata_variant':task['metadata_variant'],'candidate_count':len(bank['candidates']),**total})
    frame=pd.DataFrame(rows);frame.to_csv(RESULTS/'llm_edit_audit.csv',index=False)
    return frame

def execution_coverage(frame,tasks,protocol):
    import csv
    import sqlite3
    rows=[];selected=frame[(frame.stage=='selected')&(frame.endpoint=='T2')]
    for study in ['controlled','semantic','real']:
        expected=sum((len(protocol['config']['corruptions']) if study=='controlled' else
                      len(protocol['config']['metadata_variants'])) for item in protocol['matrix'] if item['study']==study)
        for method in MAIN+['fixed','random']+(['llm_edit'] if study!='controlled' else []):
            part=selected[(selected.study==study)&(selected.method==method)]
            rows.append({'study':study,'method':method,'expected_conditions':expected,
                'completed_conditions':part.task_id.nunique(),'missing_conditions':expected-part.task_id.nunique(),
                'independent_scms':0 if study=='real' else part.seed.nunique(),
                'apparatuses':1 if study=='real' and len(part) else 0})
    coverage=pd.DataFrame(rows);coverage.to_csv(RESULTS/'run_coverage.csv',index=False)
    if coverage.missing_conditions.ne(0).any():raise RuntimeError('Incomplete main/control coverage; report missing jobs before ranking methods')
    runtime=snapshot()
    with sqlite3.connect((root()/'ledger.sqlite').as_uri()+'?mode=ro',uri=True) as book:
        jobs=book.execute("SELECT j.id,j.status,j.attempts,COUNT(i.job),SUM(i.end-i.start) FROM jobs j LEFT JOIN intervals i ON i.job=j.id WHERE j.id LIKE 'phase2-%' GROUP BY j.id,j.status,j.attempts ORDER BY j.id").fetchall()
    pd.DataFrame(jobs,columns=['job_id','status','attempts','device_intervals','summed_interval_seconds']).to_csv(
        RESULTS/'actual_job_costs.csv',index=False,float_format='%.9g')
    weights=pd.read_csv(RESULTS/'mixture_weights.csv')
    telemetry=[];telemetry_path=root()/'logs/gpu_utilization.csv'
    if telemetry_path.exists():
        with telemetry_path.open() as stream:
            for row in csv.reader(stream):
                if len(row)!=5 or not row[1].startswith('phase2-'):continue
                try:telemetry.append((float(row[0]),float(row[3])))
                except ValueError:continue
    atomic_json(RESULTS/'execution_audit.json',{
        'method_conditions_selected':sum(len(t['methods']) for t in tasks),
        'six_main_conditions':int(coverage[coverage.method.isin(MAIN)].completed_conditions.sum()),
        'datasets':len({t['data_id'] for t in tasks}),'settings':len(tasks),
        'controlled_independent_scms':selected[selected.study.eq('controlled')].seed.nunique(),
        'semantic_independent_scms':selected[selected.study.eq('semantic')].seed.nunique(),
        'failed_jobs':[j for j in runtime['jobs'] if j['status']=='failed'],
        'retried_jobs':[j for j in runtime['jobs'] if j['attempts']>1],
        'mixture_grid_fallbacks':int(weights.grid_fallback.sum()),
        'maximum_recorded_method_peak_allocated_vram_bytes':int(frame.peak_vram_bytes.max()),
        'vram_scope':'maximum allocated CUDA tensor memory per process/stage, including separate LLM stages; not a continuous device-wide reserved-memory trace',
        'sampled_device_memory':{'readings':len(telemetry),
            'maximum_used_mib':max((row[1] for row in telemetry),default=None),
            'sampling_scope':'nvidia-smi heartbeat samples approximately every ten seconds per active job; maximum observed device use, not a continuously measured peak',
            'artifact':'logs/gpu_utilization.csv',
            'sha256':file_hash(telemetry_path) if telemetry_path.exists() else None},
        'actual_job_cost_scope':'single-device union, including development and failed attempts; do not sum duplicated method-condition runtime fields',
        'cost_scope':'logical full bank per method; actual incremental attribution follows execution order and can recur where a dataset model serves several conditions',
        'phase2_device_hours':runtime['phase2_gpu_seconds']/3600,
        'historical_device_hours':runtime['historical_gpu_seconds']/3600,
        'cumulative_device_hours':runtime['cumulative_gpu_seconds']/3600})
    return coverage

def evidence(table,reliability,comparisons,summary,frame,cfg):
    order=table.sort_values('mean');best=order.iloc[0]
    best_ties=order[np.isclose(order['mean'],best['mean'],rtol=0,atol=1e-12)]
    best_names=', '.join(LABELS[m] for m in best_ties.method)
    repair=reliability[(reliability.study=='controlled')&(reliability.stage=='selected')&reliability.method.isin(['M3','M4','M5','random'])]
    reliable=repair.sort_values(['harmful_frequency','mean_positive_deterioration','method']).iloc[0]
    harm_ties=repair[np.isclose(repair.harmful_frequency,reliable.harmful_frequency,rtol=0,atol=1e-12)]
    runtime=snapshot();core=frame[(frame.study=='controlled')&(frame.stage=='selected')&(frame.endpoint=='T2')]
    main=core[core.method.isin(MAIN)];converged=main[main.method=='M2'].drop_duplicates('data_id')
    unresolved=[];separated=[]
    for other in MAIN:
        if other==best.method:continue
        row=comparisons[((comparisons.a==best.method)&(comparisons.b==other))|
                        ((comparisons.b==best.method)&(comparisons.a==other))].iloc[0]
        (unresolved if row.p_holm>=.05 else separated).append(other)
    tradeoffs=pd.read_csv(RESULTS/'accuracy_cost_tradeoffs.csv')
    frontier=tradeoffs[(tradeoffs.study=='controlled')&(tradeoffs.scope=='six_main')&tradeoffs.observed_pareto.eq(True)]
    llm=pd.read_csv(RESULTS/'llm_edit_audit.csv');counts=[k for k in ['malformed_output','invalid_nodes','cycles',
        'duplicate_graphs','valid_no_change','valid_new_edits','score_rejections','accepted_changes',
        'evaluated_new_candidates','repeated_valid_proposals_across_retry','valid_unique_proposals_not_evaluated'] if k in llm]
    extensions=pd.read_csv(RESULTS/'repair_comparisons.csv')
    extension_core=extensions[(extensions.study=='controlled')&(extensions.stage=='selected')&
        extensions.comparison.isin(['M4 - M3','M5 - M3'])]
    execution=read_json(RESULTS/'execution_audit.json')
    illustration=read_json(RESULTS/'illustration_choices.json')
    historical_llm=read_json(RESULTS/'historical_llm_audit.json')
    lost_siblings=sum(not p['legacy_batch_valid'] and p['category']=='valid_graph_not_single_edit'
                      for p in historical_llm['proposals'])
    text=['# Phase-two evidence for scientific review','',
        f"Executed {main.task_id.nunique()} controlled conditions from {main.seed.nunique()} independent SCMs. "
        f"Best observed mean T2 prediction: {best_names}, {best['mean']:.5f} "
        f"(descriptive SCM-cluster 95% interval [{best.low:.5f}, {best.high:.5f}]).",'',
        'This ranking is descriptive. Formal pairwise primary comparisons use SCM-level sign randomization and Holm correction over all 15 pairs, assuming sign exchangeability under the paired null. See results/primary_comparisons.csv; overlapping marginal intervals alone do not establish ties or differences.','',
        f"The best observed method is not separated by the corrected primary test from: {', '.join(unresolved) or 'none'}. "
        f"It has a corrected difference from: {', '.join(separated) or 'none'}. Failure to separate methods is not proof of equivalence.",'',
        f"The lowest observed repair harm frequency among M3/M4/M5/random is shared by {', '.join(LABELS[m] for m in harm_ties.method)}: "
        f"{reliable.harmful_count}/{reliable.conditions}. Mean gains, retention and harm severity must be read together; retaining G0 is not proof of better prediction.",'',
        f"Observed accuracy/computation Pareto set among the six main methods: {', '.join(frontier.method)}. "
        'Cost here is logical construction/selection plus one complete final prediction batch. There is no unique best tradeoff without a cost preference. Simple methods receive their measured small costs rather than artificial compute padding. The frontier is descriptive, not a test of efficiency dominance.','',
        f"DCDI-DSF strict convergence: {int(converged.discovery_converged.sum())}/{len(converged)} unique controlled dataset fits. "
        'All capped fits and projected edges are disclosed. A capped baseline is not evidence about the fully converged published algorithm. Discovery and common-flow refitting costs are separate.','',
        f"Phase-two device use: {runtime['phase2_gpu_seconds']/3600:.6f} h; historical {runtime['historical_gpu_seconds']/3600:.6f} h; "
        f"cumulative {runtime['cumulative_gpu_seconds']/3600:.6f} h. Runtime includes tests, development, pilots and failed attempts. Logical method costs count shared bank construction separately for each M3/M4/M5 method.",'',
        f"Coverage: {execution['six_main_conditions']} six-method conditions across {execution['settings']} settings / "
        f"{execution['datasets']} datasets. Controls and checkpoint variants bring this to {execution['method_conditions_selected']} selected method-condition records. "
        'See run_coverage.csv and execution_audit.json for actual completion, failed validation attempts and resumed jobs. A metadata variant or checkpoint is not a new independent SCM.','',
        f"Recorded peak allocated CUDA memory across method stages: {execution['maximum_recorded_method_peak_allocated_vram_bytes']/2**30:.3f} GiB; "
        f"deterministic-grid optimizer fallbacks: {execution['mixture_grid_fallbacks']}. This is allocator memory, not a continuous device-wide reserved-memory trace.",'',
        '## Main controlled results','',markdown_table(table[['method','mean','low','high','flow_fit_seconds','discovery_seconds','prediction_seconds']]),'',
        'Fit seconds include all canonical mechanisms needed by a method; M0/M1 contain their direct fitting costs. Prediction seconds cover all final environments for that model, not a single environment. Mechanism times measured with concurrent workers include device contention. Actual incremental method fields must not be summed across reused conditions; the cumulative device ledger is authoritative.','',
        '## Repair reliability','',markdown_table(repair[['method','harmful_count','conditions','mean_improvement','harmful_severity_mean','retention_rate']]),'',
        'Secondary paired extension differences (negative error/harm changes favor the extension; these intervals are descriptive, without additional formal superiority claims):','',
        markdown_table(extension_core[['comparison','metric','mean','low','high']]),'',
        'The fixed G0 reference is common within each task. Harm is N/A for nonrepair M0/M1/M2. Zero observed harm can produce a degenerate bootstrap interval and does not rule out harm on new SCMs. Matched computation curves retain only conditions available for both policies at each ceiling and report achieved updates and time. The time ceiling covers canonical mechanism fitting, not all search and diagnostic overhead; total method costs are shown separately.','',
        ('Largest observed harmful repair: '+illustration['adverse_method']+' on '+illustration['adverse']+
         f", error change +{illustration['adverse_error_change']:.5f} against a harm threshold of {illustration['adverse_harm_threshold']:.5f}. See F5/F6."
         if illustration['adverse'] else 'No harmful returned repair occurred under the prespecified threshold in this matrix; this does not establish a harmless-repair guarantee.'),'',
        '## Separate semantic and real panels','']
    panel_rows=[]
    for (study,variant,endpoint),panel in summary[summary.study.ne('controlled')&summary.endpoint.isin(['T2','T2_exploratory'])].groupby(['study','metadata_variant','endpoint']):
        best_main=panel[panel.method.isin(MAIN)].sort_values('mean').iloc[0];winner=panel.sort_values('mean').iloc[0]
        main_tied=panel[panel.method.isin(MAIN)&np.isclose(panel['mean'],best_main['mean'],rtol=0,atol=1e-12)]
        tied=panel[np.isclose(panel['mean'],winner['mean'],rtol=0,atol=1e-12)]
        panel_rows.append({'panel':study+'/'+variant+'/'+endpoint,'best_main':', '.join(main_tied.method),'main_SW1':best_main['mean'],
                           'best_including_controls':', '.join(tied.method),'all_SW1':winner['mean']})
    text.append(markdown_table(pd.DataFrame(panel_rows)))
    text+=['','The real polarizer panel uses previously unused intervention regimes, conditional on recorded assignment setpoints. It is one familiar apparatus, with temporal dependence and phase-one-informed design. Each regime has one acquisition run. Ten-row bootstrap groups are analyst-defined contiguous reporting blocks, not independent acquisitions; non-test roles use separated within-run segments. RGB results remain exploratory. Resplitting previously exposed observations does not make them confirmatory. Real block intervals quantify conditional observation uncertainty, not between-apparatus or refitting uncertainty.','',
        'Semantic LLM comparisons are paired over five independent systems and corrected as a separate family. With five systems a two-sided exact sign test has limited resolution. Real comparisons use conditional within-run reporting-block intervals and are not population-level causal confirmation. Anonymous/shuffled controls use the same underlying SCMs.','',
        '## LLM interface diagnosis','',
        f"The historical raw audit checked {historical_llm['query_attempts']} query attempts and "
        f"{historical_llm['individually_classified_proposals']} individual proposals. "
        f"{historical_llm['counts'].get('valid_graph_not_single_edit',0)} were individually valid DAGs that failed the single-edit contract; "
        f"{historical_llm['counts'].get('design_constraint_violation',0)} violated design constraints. "
        f"The old all-or-nothing batch parser also discarded {lost_siblings} otherwise valid sibling DAGs. "
        'These proposal-level counts clarify the older batch/attempt counts without changing its zero-admissible-edit conclusion. The full-graph versus isolated-edge ambiguity and inconsistent node-ID presentation motivated the new legal-edit menu.','',
        markdown_table(pd.DataFrame([{'category':k,'main_count':int(llm[k].sum())} for k in counts])),'',
        'These are actual frozen Qwen3-8B generations. The edit menu guarantees that legal IDs map to acyclic graphs; an invalid ID is counted in the invalid-node/interface category. Counts distinguish proposal validation from search-score rejection and accepted search moves. Valid-proposal events can repeat across a validation retry, and the per-round fitting cap can leave a valid proposal unevaluated; both are counted separately. An accepted move can still be rejected by calibration or the one-time audit. The historical full-DAG/edit-contract failure is preserved in historical_llm_audit.json; it is not poor-method evidence.','',
        'Historical negative findings are preserved: diagnostic repair worsened semantic and real prediction; ten of 120 controlled conditions were harmful after audit; achieved fitting budgets differed; the old LLM interface admitted no new edits. The new LLM menu comparator is evaluated separately and is an adaptation inspired by CauScientist.','',
        '## Limits and interpretation','',
        'Five systems per family give limited power, especially for family-specific claims. Calibration has only ten observations per intervention at B100. Robust selection protects observed calibration environments, not arbitrary unseen settings. Mixture weights are predictive weights, not causal probabilities; marginal prediction intervals are not confidence intervals for causal effects. M2 discovers a graph without receiving the corrupted prior supplied to repair and ridge; this information difference is part of the comparison. The strict-convergence subset is a descriptive optimization-status sensitivity analysis and is not a random subgroup. No identifiability, harmless-repair guarantee, literature-priority or acceptance claim follows from these experiments. Alex must review assumptions, protocol, evidence and final text.','',
        'Reproducibility inputs are in phase2/results; final vectors, previews and tables are in phase2/paper. Full raw data, checkpoints, generated observations, candidate traces and logs are in ignored .artifacts/phase2. The runtime, frozen source/model hashes, artifact inventory and staged-blob audit record the execution and preservation state. Historical evidence remains separate. The source-linked novelty and venue reviews are in docs/novelty.md and docs/venue.md.']
    (PHASE/'docs/evidence_report.md').write_text('\n'.join(text)+'\n')
    claims=[{'claim':'The six-method controlled matrix was executed on fresh independent SCMs','status':'supported','evidence':'results/metrics.csv; results/protocol.json'},
        {'claim':f"{', '.join(best_ties.method)} attain the lowest observed controlled mean T2 error",'status':'supported','evidence':'results/method_summary.csv','limit':'descriptive tested-matrix ranking; use corrected paired comparisons for superiority'},
        {'claim':'M4 or M5 must improve every setting or prevent harmful repairs','status':'unsupported','evidence':'results/repair_reliability.csv'},
        {'claim':'A generated or highest-weight graph establishes causality','status':'unsupported','evidence':'docs/protocol.md'},
        {'claim':'The extensions are first in the literature or have new causal guarantees','status':'untested','evidence':'docs/novelty.md'},
        {'claim':'The failed historical LLM interface shows LLM-guided refinement is ineffective','status':'unsupported','evidence':'results/historical_llm_audit.json'},
        {'claim':'Real follow-up is independent-apparatus confirmation','status':'unsupported','evidence':'docs/protocol.md'}]
    for method in ['M4','M5']:
        deltas=[]
        for (study,variant,endpoint),part in summary[summary.endpoint.isin(['T2','T2_exploratory'])].groupby(['study','metadata_variant','endpoint']):
            a=part[part.method==method].iloc[0]['mean'];b=part[part.method=='M3'].iloc[0]['mean']
            deltas.append(float(a-b))
        better=any(d<-1e-12 for d in deltas);worse=any(d>1e-12 for d in deltas)
        status='mixed' if better and worse else 'supported' if better else 'unsupported'
        claims.append({'claim':method+' improves observed mean prediction over M3 across the separate tested panels',
            'status':status,'evidence':'results/method_summary.csv; results/repair_comparisons.csv',
            'limit':'descriptive point-estimate assessment; corrected primary tests and separate panel uncertainty govern inferential claims',
            'panels_better':sum(d<-1e-12 for d in deltas),'panels_worse':sum(d>1e-12 for d in deltas),
            'panels_equal':sum(abs(d)<=1e-12 for d in deltas)})
    atomic_json(RESULTS/'claim_ledger.json',claims)

def report():
    protocol=read_json(RESULTS/'protocol.json');cfg=protocol['config'];frame=pd.read_csv(RESULTS/'metrics.csv')
    if frame.empty:raise RuntimeError('Actual final metrics are required')
    (PHASE/'paper/tables').mkdir(parents=True,exist_ok=True)
    summary,table=method_table(frame,cfg);reliability,pairs=repair_table(frame,cfg)
    core=frame[(frame.study=='controlled')&(frame.stage=='selected')&(frame.endpoint=='T2')]
    comparisons=primary_comparisons(core,cfg);checkpoints=checkpoint_table(frame,cfg)
    tasks=read_json(RESULTS/'selected_models.json')['tasks']
    analysis_tables(frame,summary,pairs,tasks,cfg)
    method_overview(cfg)
    choices=figures(frame,summary,table,reliability,pairs,checkpoints,cfg);latex_tables(table,reliability)
    from .illustrations import response_figures,real_intervals
    response_figures();real_intervals();panel_figure(summary)
    llm_audit(tasks);execution_coverage(frame,tasks,protocol)
    evidence(table,reliability,comparisons,summary,frame,cfg)
    atomic_json(RESULTS/'figure_manifest.json',{'metrics_sha256':file_hash(RESULTS/'metrics.csv'),
        'illustration_choices':choices,'intervals':'SCM-cluster confidence intervals; response bands separately labeled predictive',
        'files':{p.name:file_hash(p) for p in (PHASE/'paper/figures').iterdir() if p.suffix in ('.pdf','.svg','.png')},
        'plotting_tables':{p.name:file_hash(p) for p in RESULTS.iterdir() if p.name in
            ('metrics.csv','method_summary.csv','repair_reliability.csv','paired_repairs.csv','checkpoint_summary.csv',
             'response_curves.csv','real_block_intervals.csv','selected_models.json','protocol.json') or
             p.name.startswith('F') and '_plotting.' in p.name},
        'analysis_sources':{name:file_hash(Path(__file__).with_name(name)) for name in ('reporting.py','illustrations.py')},
        'source_at_freeze':{k:protocol[k] for k in ('reporting_source_at_freeze','illustration_source_at_freeze') if k in protocol}})
    return table

def plots_only():
    """Rebuild final vectors/tables using only compact curated inputs, on CPU."""
    protocol=read_json(RESULTS/'protocol.json');cfg=protocol['config'];frame=pd.read_csv(RESULTS/'metrics.csv')
    (PHASE/'paper/tables').mkdir(parents=True,exist_ok=True)
    summary,table=method_table(frame,cfg);reliability,pairs=repair_table(frame,cfg)
    checkpoints=checkpoint_table(frame,cfg);method_overview(cfg)
    figures(frame,summary,table,reliability,pairs,checkpoints,cfg,curated_only=True)
    latex_tables(table,reliability)
    from .illustrations import response_figures
    response_figures(curated_only=True);panel_figure(summary)

def panel_figure(summary):
    blocks=pd.read_csv(RESULTS/'real_block_intervals.csv');setup_plot()
    fig,axes=plt.subplots(1,3,figsize=(4.8,2.45));points=[]
    for ax,study,endpoint,title in zip(axes,['semantic','real','real'],['T2','T2','T2_exploratory'],
            ['Semantic (5 SCMs)','Polarizer: new regime','RGB: exploratory']):
        table=summary[(summary.study==study)&(summary.endpoint==endpoint)&(summary.metadata_variant=='coherent')]
        methods=MAIN+['llm_edit']
        for i,method in enumerate(methods):
            row=table[table.method==method].iloc[0]
            if study=='real':
                interval_row=blocks[(blocks.endpoint==endpoint)&(blocks.metadata_variant=='coherent')&(blocks.method==method)].iloc[0]
                low,high=interval_row.conditional_low,interval_row.conditional_high
            else:low,high=row.low,row.high
            ax.vlines(i,low,high,color=COLORS[method],lw=1)
            ax.plot(i,row['mean'],marker=MARKERS[method],color=COLORS[method],ms=4)
            points.append({'study':study,'endpoint':endpoint,'metadata_variant':'coherent','method':method,
                'mean':row['mean'],'low':low,'high':high,'interval_type':'conditional within-run reporting-block' if study=='real' else 'SCM-cluster'})
        if study=='real':ax.set_yscale('log')
        ax.set_xticks(range(len(methods)),MAIN+['LLM'],rotation=45);ax.set_title(title);ax.set_ylabel('T2 joint SW₁ ↓');ax.grid(axis='y',alpha=.15)
    fig.tight_layout(w_pad=.5);save(fig,'F7_separate_panels')
    pd.DataFrame(points).to_csv(RESULTS/'F7_plotting.csv',index=False,float_format='%.9g')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--plots-only',action='store_true',required=True)
    parser.parse_args();plots_only()
