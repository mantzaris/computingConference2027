"""Curated-only paired SCM statistics and deterministic paper outputs."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from .runtime import PHASE,RESULTS,root,atomic_json,file_hash

METHODS=['M0','M1','M2','M3','M4','M5']
LABELS={'M0':'Marginals','M1':'Ridge','M2':'DCDI-DSF + flows','M3':'Diagnostic','M4':'Robust','M5':'Ensemble','fixed':'Fixed flows','random':'Random','oracle':'Oracle flows'}
COLORS=dict(zip(METHODS,['#777777','#009E73','#CC79A7','#0072B2','#D55E00','#E69F00']))

def bootstrap(frame,column,seed=37111,replicates=2000):
    """Average conditions per SCM, then stratify resampling by family."""
    units=frame.groupby(['family','scm'],sort=True)[column].mean().dropna()
    if len(units)==0:return (None,None,None,0)
    rng=np.random.default_rng(seed);draws=np.zeros(replicates);count=0
    for _,series in units.groupby(level=0):
        a=series.to_numpy();draws+=a[rng.integers(len(a),size=(replicates,len(a)))].sum(1);count+=len(a)
    lo,hi=np.quantile(draws/count,[.025,.975])
    return float(units.mean()),float(lo),float(hi),len(units)

def sign_test(values):
    a=np.asarray(values,float);a=a[np.isfinite(a)]
    if not len(a):return None
    observed=abs(a.mean());n=len(a)
    if n>20:raise ValueError('Exact sign test intended for prespecified small strata')
    count=sum(abs(np.dot(signs,a)/n)>=observed-1e-14 for signs in itertools.product((-1,1),repeat=n))
    return count/(2**n)

def holm(p):
    order=np.argsort(p);out=np.empty(len(p));maximum=0.
    for rank,i in enumerate(order):maximum=max(maximum,(len(p)-rank)*p[i]);out[i]=min(1.,maximum)
    return out

def curate():
    path=RESULTS/'metrics.csv';raw=pd.read_csv(path)
    if 'endpoint' not in raw:return raw
    archive=root()/'analysis';archive.mkdir(exist_ok=True)
    target=archive/'metrics-full.csv'
    if target.exists() and file_hash(path)!=file_hash(target):raise RuntimeError('Preserve distinct full metric versions explicitly')
    if not target.exists():shutil.copy2(path,target)
    index=['scm','family','profile','d','budget','sensitivity','corruption','resource','method']
    main=raw[~raw.method.str.startswith('checkpoint_')].copy();t2=main[main.endpoint=='T2'].copy()
    for endpoint in ('T1','T3'):
        other=main[main.endpoint==endpoint][index+['sw1','marginal_w1','effect_rmse']].rename(columns={k:endpoint+'_'+k for k in ['sw1','marginal_w1','effect_rmse']})
        t2=t2.merge(other,on=index,validate='one_to_one')
    t2=t2.drop(columns=['endpoint','record']).sort_values(index)
    t2.to_csv(path,index=False,float_format='%.7g')
    checkpoints=raw[(raw.endpoint=='T2')&(raw.resource=='adjusted')&raw.method.str.startswith('checkpoint_')].copy()
    checkpoints['policy']=checkpoints.method.str.split('_').str[1]
    checkpoints['checkpoint']=checkpoints.method.str.replace(r'^checkpoint_(diagnostic|random)_','',regex=True)
    match_index=['scm','family','profile','d','budget','sensitivity','corruption','checkpoint']
    availability=checkpoints.pivot(index=match_index,columns='policy',values='sw1')
    availability=availability.reindex(columns=['diagnostic','random'])
    coverage=availability.notna().reset_index().groupby(['d','profile','family','budget','sensitivity','checkpoint'])[['diagnostic','random']].sum()
    common=availability.dropna().index
    matched=checkpoints.set_index(match_index).loc[common].reset_index()
    coverage['paired_conditions']=availability.dropna().reset_index().groupby(['d','profile','family','budget','sensitivity','checkpoint']).size()
    coverage.fillna(0).reset_index().to_csv(RESULTS/'checkpoint_coverage.csv',index=False)
    # One compact row per independent system and checkpoint, keeping all paired
    # corruptions together. Full condition-level predictions remain inventoried.
    cpindex=['scm','family','profile','d','budget','sensitivity','method']
    columns=['sw1','delta_fixed','harmful','retained','fitting_updates','training_seconds','search_gpu_seconds','logical_seconds','candidates']
    grouped=matched.groupby(cpindex,sort=True)[columns].mean()
    grouped['conditions']=matched.groupby(cpindex).size()
    grouped.reset_index().to_csv(RESULTS/'checkpoints.csv',index=False,float_format='%.7g')
    atomic_json(RESULTS/'metric_manifest.json',{'full_metric_artifact':'analysis/metrics-full.csv','full_sha256':file_hash(target),
        'curated_sha256':file_hash(path),'full_rows':len(raw),'curated_rows':len(t2),
        'precision':'7 significant decimal digits; full operational metrics retained',
        'trace':'prediction_key maps to generated_samples/<key>/metrics.json and samples.npz in the verified artifact archive',
        'checkpoints':'Adjusted-bank completed prefixes, paired on exact SCM/corruption/ceiling before averaging within each SCM; conditions and checkpoint_coverage.csv report coverage. Full identities remain in the full metric artifact.'})
    return pd.read_csv(path)

def strata(frame):
    for resource in ('fixed','adjusted'):
        for d in (20,50,100):yield f'A-d{d}',resource,frame[(frame.profile=='sparse')&(frame.d==d)&(frame.resource==resource)]
        for profile in ('dense','hub','deep'):yield f'B-{profile}',resource,frame[(frame.profile==profile)&(frame.resource==resource)]

def statistics(frame):
    summaries=[];reliability=[];contrasts=[]
    for stratum,resource,part in strata(frame):
        for method,rows in part.groupby('method',sort=True):
            mean,low,high,n=bootstrap(rows,'sw1')
            # The prespecified oracle subset has one SCM per family/cell.
            # A stratified bootstrap would be degenerate, not evidence of zero
            # uncertainty. Retain its point estimate and mark its CI unavailable.
            if method=='oracle':low=high=None
            record={'stratum':stratum,'resource':resource,'method':method,'scms':n,'conditions':len(rows),'mean':mean,'low':low,'high':high}
            for c in ['T1_sw1','T3_sw1','marginal_w1','effect_rmse','descendant_w1','nondescendant_w1','true_response_rms','true_descendant_response_rms',
                'descendant_fraction','worst_sw1','coverage90','width90','energy_score','energy_distance','logical_seconds','training_seconds',
                'discovery_seconds','inference_seconds','metric_seconds','throughput','fitting_updates','parent_sets','candidates','accepted','shd','initial_shd']:
                record[c]=rows[c].mean()
            record['peak_vram_bytes']=rows.peak_vram_bytes.max();record['strict_converged']=int((rows.status=='converged').sum()) if method=='M2' else None
            record['graph_metric_conditions']=int(rows.shd.notna().sum())
            record['valid_capped']=int((rows.status=='valid_capped_prediction').sum());summaries.append(record)
            if method in ('M3','M4','M5','random'):
                freq,fl,fh,_=bootstrap(rows,'harmful');improve,il,ih,_=bootstrap(rows.assign(improvement=-rows.delta_fixed),'improvement')
                harmful=rows[rows.harmful==1]
                any_harm=rows.groupby('scm').harmful.max().dropna()
                reliability.append({'stratum':stratum,'resource':resource,'method':method,'scms':n,'conditions':len(rows),
                    'harm_count':int(rows.harmful.sum()),'harm_frequency':freq,'low':fl,'high':fh,
                    'mean_improvement':improve,'improvement_low':il,'improvement_high':ih,
                    'severity':harmful.delta_fixed.mean() if len(harmful) else 0.,'maximum_deterioration':max(0.,rows.delta_fixed.max()),
                    'systems_with_harm':int(any_harm.sum()),
                    'zero_event_system_risk_upper95':1-.05**(1/len(any_harm)) if len(any_harm) and not any_harm.sum() else None,
                    'retention':rows.retained.mean(),'mean_positive_deterioration':rows.delta_fixed.clip(lower=0).mean()})
        if resource=='adjusted':
            for other in ('fixed','random','M4','M5'):
                pairs=part[part.method.isin(['M3',other])].pivot(index=['family','scm','corruption'],columns='method',values='sw1').dropna()
                if not len(pairs) or not {'M3',other}<=set(pairs.columns):continue
                diff=(pairs['M3']-pairs[other]).rename('delta').reset_index();mean,lo,hi,n=bootstrap(diff,'delta')
                contrasts.append({'stratum':stratum,'contrast':'M3-'+other,'scms':n,'mean_delta':mean,'low':lo,'high':hi,
                    'p':sign_test(diff.groupby('scm').delta.mean().to_numpy())})
    if contrasts:
        # Missing strata do not reduce the frozen family of 24 contrasts.
        adjusted=holm([r['p'] for r in contrasts]+[1.]*(24-len(contrasts)))[:len(contrasts)]
        for row,p in zip(contrasts,adjusted):row['p_holm']=p
    for name,values in [('summary',summaries),('reliability',reliability),('contrasts',contrasts)]:
        pd.DataFrame(values).to_csv(RESULTS/(name+'.csv'),index=False,float_format='%.7g')
    return pd.DataFrame(summaries),pd.DataFrame(reliability),pd.DataFrame(contrasts)

def style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':9,'axes.labelsize':9,
        'legend.fontsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'svg.fonttype':'none',
        'svg.hashsalt':'phase3-scaling','axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
    return plt

def save(fig,name):
    # Every vector and preview is preserved; Git carries a compact selection.
    folder=root()/'paper/figures';folder.mkdir(parents=True,exist_ok=True)
    fig.savefig(folder/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(folder/(name+'.svg'),bbox_inches='tight',metadata={'Date':None})
    fig.savefig(folder/(name+'.png'),bbox_inches='tight',dpi=300,pil_kwargs={'compress_level':9})
    curated=PHASE/'paper/figures';curated.mkdir(parents=True,exist_ok=True)
    formats=['pdf']
    if name in ('F1_size_accuracy','F4_complexity_descendants','F5_reliability'):formats.append('svg')
    if name=='F1_size_accuracy':formats.append('png')
    for suffix in formats:shutil.copy2(folder/(name+'.'+suffix),curated/(name+'.'+suffix))

def plots(frame,summary,reliability):
    def point(rows,column):
        m,lo,hi,n=bootstrap(rows,column)
        return (m,lo,hi,n) if n else (np.nan,np.nan,np.nan,0)
    plt=style();part=frame[(frame.profile=='sparse')&(frame.resource=='adjusted')]
    fig,axes=plt.subplots(2,1,figsize=(4.8,5.5),sharey=True,layout='constrained')
    for ax,family in zip(axes,['nonlinear','heteroscedastic']):
        for mi,method in enumerate(METHODS):
            rows=part[(part.family==family)&(part.method==method)];means=[];lows=[];highs=[]
            for di,d in enumerate((20,50,100)):
                sub=rows[rows.d==d];m,lo,hi,n=point(sub,'sw1');means.append(m);lows.append(m-lo);highs.append(hi-m)
                points=sub.groupby('scm').sw1.mean();ax.scatter(np.full(len(points),di)+(mi-2.5)*.022,points,s=7,color=COLORS[method],alpha=.25,zorder=1)
            ax.errorbar(range(3),means,yerr=[lows,highs],color=COLORS[method],marker='o',ms=3,lw=1,label=method,capsize=2)
        ax.set(xticks=range(3),xticklabels=[20,50,100],xlabel='Nodes',title=family.replace('nonlinear','Additive').capitalize());ax.grid(axis='y',alpha=.15)
    for ax in axes:ax.set_ylabel('T2 joint non-target SW₁')
    axes[0].legend(ncol=3,loc='upper right',fontsize=8)
    save(fig,'F1_size_accuracy');plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(4.8,5.2),layout='constrained')
    for method in METHODS:
        rows=summary[(summary.stratum.str.startswith('A-'))&(summary.resource=='adjusted')&(summary.method==method)].set_index('stratum')
        ordered=rows.reindex(['A-d20','A-d50','A-d100'])
        axes[0].plot([20,50,100],ordered.logical_seconds,'o-',ms=3,color=COLORS[method],label=method)
        axes[1].plot([20,50,100],ordered.peak_vram_bytes/1024**3,'o-',ms=3,color=COLORS[method],label=method)
    axes[0].set(yscale='log',ylabel='Charged training + selection (s)',xlabel='Nodes',title='Logical method time')
    axes[1].set(ylabel='Maximum allocated GPU memory (GiB)',xlabel='Nodes',title='Measured peak allocation');axes[0].legend(ncol=3)
    save(fig,'F2_time_memory');plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(4.8,6.9),layout='constrained')
    for ax,d in zip(axes,(20,50,100)):
        rows=summary[(summary.stratum==f'A-d{d}')&summary.method.isin(METHODS)]
        for method in METHODS:
            r=rows[rows.method==method].set_index('resource').reindex(['fixed','adjusted'])
            ax.plot(r.logical_seconds,r['mean'],'o-',ms=3,lw=.8,color=COLORS[method],label=method)
        ax.set(xscale='log',xlabel='Charged time (s)',title=f'{d} nodes');ax.grid(alpha=.15)
    for ax in axes:ax.set_ylabel('T2 SW₁')
    axes[0].legend(ncol=3,fontsize=8)
    save(fig,'F3_error_cost');plt.close(fig)

    fig,axes=plt.subplots(2,1,figsize=(4.8,5.4),layout='constrained')
    profiles=['sparse','dense','hub','deep'];x=np.arange(4)
    for mi,method in enumerate(METHODS):
        values=[];err=[[],[]]
        for profile in profiles:
            r=frame[(frame.d==50)&(frame.family=='heteroscedastic')&(frame.profile==profile)&(frame.resource=='adjusted')&(frame.method==method)]
            m,lo,hi,n=point(r,'sw1');values.append(m);err[0].append(m-lo);err[1].append(hi-m)
        axes[0].errorbar(x+(mi-2.5)*.06,values,yerr=err,fmt='o',ms=3,capsize=2,color=COLORS[method],label=method)
        vals=[bootstrap(frame[(frame.profile=='sparse')&(frame.d==d)&(frame.resource=='adjusted')&(frame.method==method)],'descendant_w1')[0] for d in (20,50,100)]
        axes[1].plot((20,50,100),vals,'o-',ms=3,color=COLORS[method],label=method)
    axes[0].set(xticks=x,xticklabels=['Sparse','Dense','Hub','Deep'],ylabel='T2 joint SW₁',title='50-node heteroscedastic profiles')
    axes[1].set(xlabel='Nodes',ylabel='Mean marginal W₁ on descendants',title='Responding-variable prediction');axes[1].legend(ncol=3)
    save(fig,'F4_complexity_descendants');plt.close(fig)

    fig,axes=plt.subplots(3,1,figsize=(4.8,7.0),layout='constrained')
    for method in ('M3','M4','M5','random'):
        color=COLORS.get(method,'#555555');r=reliability[(reliability.stratum.str.startswith('A-'))&(reliability.resource=='adjusted')&(reliability.method==method)].set_index('stratum').reindex(['A-d20','A-d50','A-d100'])
        axes[0].errorbar((20,50,100),r.harm_frequency,yerr=[r.harm_frequency-r.low,r.high-r.harm_frequency],fmt='o-',ms=3,capsize=2,color=color,label=method)
        axes[1].plot((20,50,100),r.maximum_deterioration,'o-',ms=3,color=color)
        axes[2].plot(r.mean_improvement,r.harm_frequency,'o-',ms=3,color=color)
    bounds=reliability[(reliability.stratum.str.startswith('A-'))&(reliability.resource=='adjusted')].high
    frequency_top=max(.1,min(1.02,float(bounds.max())+.03)) if bounds.notna().any() else 1.02
    axes[0].set(xlabel='Nodes',ylabel='Harmful-repair frequency',ylim=(-.01,frequency_top));axes[0].legend(ncol=4,fontsize=8)
    axes[1].set(xlabel='Nodes',ylabel='Maximum deterioration in T2 SW₁')
    axes[2].set(xlabel='Mean improvement over G0',ylabel='Harmful-repair frequency');axes[2].axvline(0,color='.7',lw=.6)
    save(fig,'F5_reliability');plt.close(fig)

    path=RESULTS/'checkpoints.csv'
    if path.exists():
        cp=pd.read_csv(path);cp=cp[(cp.profile=='sparse')&(cp.sensitivity=='primary')]
        if len(cp):
            fig,axes=plt.subplots(3,2,figsize=(4.8,6.9),layout='constrained')
            for row,d in enumerate((20,50,100)):
                for col,axis in enumerate(('fitting_updates','gpu_job_seconds')):
                    for policy,color in [('diagnostic',COLORS['M3']),('random','#555555')]:
                        part=cp[(cp.d==d)&cp.method.str.startswith(f'checkpoint_{policy}_{axis}_')].copy()
                        part['limit']=part.method.str.rsplit('_',n=1).str[-1].astype(float)
                        stats=part.groupby('limit').agg(error=('sw1','mean'),achieved=('fitting_updates' if col==0 else 'search_gpu_seconds','mean'),coverage=('scm','nunique'))
                        axes[row,col].plot(stats.achieved,stats.error,'o-',ms=3,color=color,label=policy)
                    axes[row,col].set(title=f'{d} nodes',xlabel='Achieved updates' if col==0 else 'Fit + search (s)')
            for ax in axes[:,0]:ax.set_ylabel('T2 SW₁')
            axes[0,-1].legend(fontsize=8)
            save(fig,'F6_matched_compute');plt.close(fig)

def tables(summary,reliability):
    folder=PHASE/'paper';rows=[r'\begin{tabular}{rlrrr}',r'\hline',r'$d$ & Method & T2 SW$_1$ [95\% CI] & Time (s) & VRAM (GiB) \\',r'\hline']
    for d in (20,50,100):
        part=summary[(summary.stratum==f'A-d{d}')&(summary.resource=='adjusted')&summary.method.isin(METHODS)]
        for method in METHODS:
            if not len(part[part.method==method]):
                rows.append(f'{d} & {method} & unavailable & -- & -- \\\\');continue
            r=part[part.method==method].iloc[0]
            rows.append(f"{d} & {method} & {r['mean']:.4f} [{r.low:.4f}, {r.high:.4f}] & {r.logical_seconds:.1f} & {r.peak_vram_bytes/1024**3:.2f} \\\\")
    rows += [r'\hline',r'\end{tabular}'];(folder/'comparison.tex').write_text('\n'.join(rows)+'\n')
    rows=[r'\begin{tabular}{rlrrrr}',r'\hline',r'$d$ & Method & Harm / settings & Mean gain & Max $\Delta$ & Retained \\',r'\hline']
    for d in (20,50,100):
        for method in ('M3','M4','M5','random'):
            available=reliability[(reliability.stratum==f'A-d{d}')&(reliability.resource=='adjusted')&(reliability.method==method)]
            if not len(available):
                rows.append(f'{d} & {method} & unavailable & -- & -- & -- \\\\');continue
            r=available.iloc[0]
            rows.append(f'{d} & {method} & {r.harm_count}/{r.conditions} & {r.mean_improvement:.4f} & {r.maximum_deterioration:.4f} & {r.retention:.2f} \\\\')
    rows += [r'\hline',r'\end{tabular}'];(folder/'reliability.tex').write_text('\n'.join(rows)+'\n')

def main():
    frame=curate();primary=frame[frame.sensitivity=='primary']
    summary,reliability,contrasts=statistics(primary);plots(primary,summary,reliability);tables(summary,reliability)
    from .illustrations import render_curated
    render_curated()
    files=sorted((PHASE/'paper').rglob('*'));files=[p for p in files if p.is_file() and p.suffix in ('.pdf','.svg','.png','.tex')]
    plotting_inputs=sorted(RESULTS.glob('*.csv'))+[RESULTS/name for name in ('illustration_graphs.json','protocol.json') if (RESULTS/name).exists()]
    atomic_json(RESULTS/'figure_manifest.json',{'inputs':{p.name:file_hash(p) for p in plotting_inputs},
        'outputs':{str(p.relative_to(PHASE)):file_hash(p) for p in files},'source_sha256':file_hash(__file__),
        'all_formats_in_artifacts':{str(p.relative_to(root())):file_hash(p) for p in sorted((root()/'paper/figures').iterdir()) if p.suffix in ('.pdf','.svg','.png')},
        'curation':'All PDFs, three SVGs and one PNG preview in Git; every PDF/SVG/PNG retained in the verified ignored artifact archive.',
        'intervals':'SCM cluster bootstrap CIs in aggregate plots; predictive intervals only in response curves'})

if __name__=='__main__':main()
