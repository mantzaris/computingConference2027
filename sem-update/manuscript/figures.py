"""CPU-only composition of existing compact results. No fitting or sampling."""
from pathlib import Path
import hashlib
import json
import os
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ART = PROJECT / '.artifacts/manuscript_draft'
os.environ.setdefault('MPLCONFIGDIR', str(ART / 'matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

OUT = ART / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
TABLES = ART / 'tables'
TABLES.mkdir(parents=True, exist_ok=True)
COLORS = {'M0':'#888888','M1':'#0072B2','M2':'#CC79A7','fixed':'#009E73',
          'random':'#999933','M3':'#D55E00','M4':'#E69F00','M5':'#332288'}
METHODS = ['M0','M1','M2','M3','M4','M5','fixed','random']
NAMES = {'M0':'Marginals','M1':'Ridge','M2':'DCDI-DSF + flows','M3':'Diagnostic',
         'M4':'Robust selection','M5':'Anchored ensemble','fixed':'Fixed flows','random':'Random repair'}
INPUTS = {}

def read(path):
    p = PROJECT / path
    INPUTS[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return pd.read_csv(p)

def save(fig, name):
    for ext in ('pdf','svg','png'):
        meta = {'CreationDate':None,'ModDate':None} if ext == 'pdf' else {'Date':None} if ext == 'svg' else None
        fig.savefig(OUT / (name+'.'+ext), dpi=190, bbox_inches='tight', pad_inches=.04, metadata=meta)
    plt.close(fig)

def overview():
    fig, ax = plt.subplots(figsize=(4.80,2.30))
    ax.set(xlim=(0,10),ylim=(0,5));ax.axis('off')
    boxes = [(0.1,3.3,2.4,1.2,'Initial graph $G_0$\nFit + early stop'),
             (3.2,3.3,3.5,1.2,'Disturbance priorities\nLegal edits + search score'),
             (7.4,3.3,2.5,1.2,'Frozen bank\nCached models'),
             (0.1,1.5,2.7,1.1,'Mean selection\nM3 calibration'),
             (3.4,1.5,2.8,1.1,'Mean / worst\nM4 calibration'),
             (6.8,1.5,3.1,1.1,'Anchored mixture\nM5 calibration'),
             (2.4,.05,5.2,.8,'Audit once against $G_0$\nAccept selection or return $G_0$')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04',fc='#F5F7FA',ec='#5B6573',lw=.7))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=7)
    def arrow(a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,lw=.8,color='#535B65'))
    arrow((2.55,3.9),(3.15,3.9));arrow((6.75,3.9),(7.35,3.9))
    ax.plot([1.5,8.6],[2.95,2.95],c='#535B65',lw=.7)
    arrow((8.6,3.25),(8.6,2.6))
    for x in (1.5,4.8):arrow((x,2.95),(x,2.62))
    for x in (1.5,4.8,8.4):arrow((x,1.45),(5,.89))
    save(fig,'overview')

def controlled(metrics, reliability):
    m=metrics[(metrics.study=='controlled')&(metrics.stage=='selected')&(metrics.endpoint=='T2')]
    fig,axes=plt.subplots(1,2,figsize=(4.8,2.55))
    ax=axes[0]
    for family,marker,color,label in [('linear','o','#222222','Linear'),('nonlinear','s','#0072B2','Additive'),('heteroscedastic','^','#D55E00','Heteroscedastic')]:
        v=m[(m.family==family)&m.method.isin(METHODS[:6])].groupby('method').sw1.mean().reindex(METHODS[:6])
        ax.plot(range(6),v,marker=marker,color=color,ms=3,lw=.8,label=label)
    ax.set_xticks(range(6));ax.set_xticklabels(METHODS[:6]);ax.set_ylabel('Mean T2 sliced Wasserstein')
    ax.set_title('a  Mechanism families',loc='left');ax.legend(fontsize=6.1,frameon=False)
    ax=axes[1]
    r=reliability[(reliability.study=='controlled')&(reliability.stage=='selected')]
    offsets={'M3':(-15,9),'M4':(-26,-16),'M5':(5,1),'random':(-30,-16),'tau0':(4,3),'uniform':(-30,8)}
    for method in ['M3','M4','M5','random','tau0','uniform']:
        row=r[r.method==method].iloc[0]
        color=COLORS.get(method,'#777777')
        ax.errorbar(row.mean_improvement,100*row.harmful_frequency,
                    xerr=[[row.mean_improvement-row.improvement_low],[row.improvement_high-row.mean_improvement]],
                    yerr=[[100*(row.harmful_frequency-row.harmful_low)],[100*(row.harmful_high-row.harmful_frequency)]],
                    color=color,fmt='o' if method in COLORS else 'x',ms=3.5,lw=.65,capsize=1.5)
        label={'random':'Random','tau0':r'$\tau=0$','uniform':'Uniform'}.get(method,method)
        ax.annotate(label,(row.mean_improvement,100*row.harmful_frequency),xytext=offsets[method],textcoords='offset points',fontsize=6.5)
    ax.set(xlabel='Mean gain over fixed flows',ylabel='Harmful conditions (%)',ylim=(-2,27))
    ax.set_title('b  Accuracy and harm',loc='left')
    for ax in axes:ax.grid(alpha=.18);ax.tick_params(labelsize=6.5)
    fig.tight_layout(w_pad=1.3);save(fig,'controlled')

def scaling(summary,metrics):
    s=summary[(summary.resource=='adjusted')&summary.stratum.isin(['A-d20','A-d50','A-d100'])]
    fig,axes=plt.subplots(2,2,figsize=(4.8,4.25))
    for method in METHODS:
        p=s[s.method==method].set_index('stratum').reindex(['A-d20','A-d50','A-d100'])
        for ax,col in [(axes[0,0],'mean'),(axes[0,1],'descendant_w1'),(axes[1,0],'logical_seconds')]:
            ax.plot([20,50,100],p[col],'-o',ms=2.5,lw=.9,color=COLORS[method],label=method if method.startswith('M') else NAMES[method])
        if method in ['M3','M5']:
            axes[0,0].fill_between([20,50,100],p.low.to_numpy(),p.high.to_numpy(),color=COLORS[method],alpha=.12,lw=0)
    m=metrics[(metrics.resource=='adjusted')&(metrics.sensitivity=='primary')&(metrics.profile=='sparse')&(metrics.method=='M3')]
    for d,p in m.groupby('d'):
        v=p.groupby('scm').sw1.mean().to_numpy()
        axes[0,0].scatter(np.linspace(d-2,d+2,len(v)),v,s=5,c=COLORS['M3'],alpha=.4,zorder=1)
    labels=['Dense','Hub','Deep'];strata=['B-dense','B-hub','B-deep']
    for method in METHODS[1:]:
        p=summary[(summary.resource=='adjusted')&(summary.method==method)].set_index('stratum')
        if not all(x in p.index for x in strata):
            strata=[next(x for x in p.index if x.lower().endswith(v.lower())) for v in labels]
        axes[1,1].plot(range(3),p.loc[strata,'mean'],'-o',ms=2.5,lw=.85,color=COLORS[method])
    axes[0,0].set_title('a  Joint T2 error',loc='left');axes[0,1].set_title('b  Descendant error',loc='left')
    axes[1,0].set_title('c  Charged computation',loc='left');axes[1,1].set_title('d  50-node profiles',loc='left')
    axes[0,0].set_ylabel('Sliced Wasserstein');axes[0,1].set_ylabel('Marginal Wasserstein')
    axes[1,0].set_ylabel('Seconds (log scale)');axes[1,0].set_yscale('log')
    axes[1,1].set_ylabel('Sliced Wasserstein');axes[1,1].set_xticks(range(3));axes[1,1].set_xticklabels(labels)
    for ax in [axes[0,0],axes[0,1],axes[1,0]]:
        ax.set_xticks([20,50,100]);ax.set_xlabel('Nodes')
    for ax in axes.flat:ax.grid(alpha=.16);ax.tick_params(labelsize=6.5)
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,ncol=4,loc='lower center',frameon=False,fontsize=6.5)
    fig.tight_layout(rect=(0,.11,1,1),h_pad=1.5,w_pad=1.0);save(fig,'scaling')

def responses(response,effects):
    fig,axes=plt.subplots(2,3,figsize=(4.8,3.1),sharex='col')
    for col,run in enumerate(['validate_load_in','validate_load_out','validate_hatch_rpms']):
        for row,outcome in enumerate(['pressure_upwind','current_in']):
            ax=axes[row,col]
            o=response[(response.run==run)&(response.outcome==outcome)&(response.method=='M1')].sort_values('arm')
            ax.errorbar([0,1],o.observed_mean,yerr=[o.observed_mean-o.observed_ci_low,o.observed_ci_high-o.observed_mean],
                        fmt='ko-',ms=3,lw=1,capsize=2,label='Measured / 95% CI')
            for method in ['M1','M2','fixed','M3','M5']:
                p=effects[(effects.run==run)&(effects.outcome==outcome)&(effects.method==method)].iloc[0]
                ax.plot([0,1],[p.pred_low,p.pred_high],':o',lw=.8,ms=2.2,c=COLORS[method],label=method if method!='fixed' else 'Fixed flows')
            if col==0:ax.set_ylabel('Upwind pressure\nrelative to ambient (Pa)' if row==0 else 'Inlet current (A)')
            if row==0:ax.set_title(['Inlet duty','Outlet duty','Hatch angle'][col])
            ax.set_xticks([0,1]);ax.set_xticklabels(['0.01','1'] if col<2 else [r'$0^\circ$',r'$45^\circ$'])
            ax.grid(alpha=.16);ax.tick_params(labelsize=6.5)
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,ncol=3,loc='lower center',frameon=False,fontsize=6.6)
    fig.subplots_adjust(left=.16,right=.99,bottom=.20,top=.91,hspace=.35,wspace=.55);save(fig,'responses')

def physical(small,wind,cost):
    light=small[(small.study=='real')&(small.metadata_variant=='coherent')&(small.endpoint=='T2')].set_index('method')
    w=wind.set_index('method').join(cost.set_index('method')[['logical_seconds']])
    fig,axes=plt.subplots(1,2,figsize=(4.8,2.65))
    for ax,df,col,title in [(axes[0],light,'mean','a  Light tunnel'),(axes[1],w,'effect_error','b  Wind tunnel')]:
        for method in METHODS:
            r=df.loc[method];ax.scatter(r.logical_seconds,r[col],s=20,color=COLORS[method],label=method if method.startswith('M') else NAMES[method])
        ax.set_xscale('log');ax.set_yscale('log');ax.set_title(title,loc='left')
        # Explicit positive limits avoid old Matplotlib scatter/log autoscaling
        # clipping the inexpensive marginal control in the light-tunnel panel.
        xv=df.loc[METHODS,'logical_seconds'].to_numpy();yv=df.loc[METHODS,col].to_numpy()
        ax.set_xlim(xv.min()/1.8,xv.max()*1.8);ax.set_ylim(yv.min()/1.3,yv.max()*1.4)
        assert all(ax.get_xlim()[0]<x<ax.get_xlim()[1] and ax.get_ylim()[0]<y<ax.get_ylim()[1] for x,y in zip(xv,yv))
        ax.set_xlabel('Charged fit / selection (s)');ax.grid(alpha=.16);ax.tick_params(labelsize=6.5)
    axes[0].set_ylabel('Polarizer joint SW error');axes[1].set_ylabel('Wind contrast error')
    for method,offset in [('M1',(5,-1)),('M2',(-18,7)),('M3',(-27,-1)),('fixed',(-19,9))]:
        r=light.loc[method];axes[0].annotate(method if method!='fixed' else 'Fixed',(r.logical_seconds,r['mean']),xytext=offset,textcoords='offset points',fontsize=6.4)
    for method,offset in [('M1',(-8,7)),('M2',(-18,8)),('M3',(-8,10)),('fixed',(-10,-14))]:
        r=w.loc[method];axes[1].annotate(method if method!='fixed' else 'Fixed',(r.logical_seconds,r.effect_error),xytext=offset,textcoords='offset points',fontsize=6.4)
    h,l=axes[0].get_legend_handles_labels();fig.legend(h,l,ncol=4,loc='lower center',frameon=False,fontsize=6.4)
    fig.tight_layout(rect=(0,.18,1,1),w_pad=1.0);save(fig,'physical_cost')

def tables(summary,reliability,wind,cost):
    s=summary[(summary.study=='controlled')&(summary.endpoint=='T2')].set_index('method')
    r=reliability[(reliability.study=='controlled')&(reliability.stage=='selected')].set_index('method')
    lines=[]
    for method in METHODS:
        v=s.loc[method];harm=str(int(r.loc[method,'harmful_count']))+'/60' if method in r.index else 'N/A'
        lines.append('%s & %s & %.3f [%.3f, %.3f] & %s & %.2f \\\\' %
                     (method if method.startswith('M') else '--',NAMES[method],v['mean'],v.low,v.high,harm,v.logical_seconds))
    (TABLES/'controlled.tex').write_text('\n'.join(lines)+'\n')
    w=wind.set_index('method').join(cost.set_index('method')[['logical_seconds']]);lines=[]
    for method in METHODS:
        v=w.loc[method]
        lines.append('%s & %.3f [%.3f, %.3f] & %.1f & %.2f \\\\' %
                     (NAMES[method],v.effect_error,v.ci_low,v.ci_high,100*v.coverage90,v.logical_seconds))
    (TABLES/'wind.tex').write_text('\n'.join(lines)+'\n')
    lines=[]
    for method in METHODS:
        a=summary[(summary.study=='controlled')&(summary.endpoint=='T1')&(summary.method==method)].iloc[0]
        b=summary[(summary.study=='controlled')&(summary.endpoint=='T3')&(summary.method==method)].iloc[0]
        lines.append('%s & %.3f [%.3f, %.3f] & %.3f [%.3f, %.3f] & %.1f \\\\' %
                     (method if method.startswith('M') else NAMES[method],a['mean'],a.low,a.high,b['mean'],b.low,b.high,100*s.loc[method,'coverage_90']))
    (TABLES/'secondary.tex').write_text('\n'.join(lines)+'\n')

def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.titlesize':8,
                         'axes.labelsize':7,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'svg.hashsalt':'manuscript-draft-evidence',
                         'axes.linewidth':.6,'lines.linewidth':.9})
    small=read('phase2/results/method_summary.csv');metrics=read('phase2/results/metrics.csv')
    reliability=read('phase2/results/repair_reliability.csv')
    large=read('phase3/results/summary.csv');large_m=read('phase3/results/metrics.csv')
    wind=read('phase4_real_application/results/summary.csv');cost=read('phase4_real_application/results/costs.csv')
    resp=read('phase4_real_application/results/plot_responses.csv');eff=read('phase4_real_application/results/effects.csv')
    overview();controlled(metrics,reliability);scaling(large,large_m);responses(resp,eff);physical(small,wind,cost)
    tables(small,reliability,wind,cost)
    for path in ['phase4_real_application/figures/A_process_graph.pdf',
                 '.artifacts/phase4_real_application/figures/S_M5_component_1.pdf',
                 '.artifacts/phase4_real_application/figures/S_M5_component_2.pdf']:
        INPUTS[path]=hashlib.sha256((PROJECT/path).read_bytes()).hexdigest()
    (ART/'figure_inputs.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
    print('Five recomposed figures and three table bodies, from existing results only.')

if __name__=='__main__':main()
