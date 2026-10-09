"""Publication figures from compact plotting tables; no AI chart generation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
PHASE=Path(__file__).resolve().parents[1];PROJECT=PHASE.parent
ROOT=Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT',PROJECT/'.artifacts/phase4_real_application'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'model_cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D

RESULTS=PHASE/'results';FIGURES=ROOT/'figures'
METHODS=['M0','M1','M2','fixed','random','M3','M4','M5']
COLORS={'M0':'#888888','M1':'#0072B2','M2':'#CC79A7','fixed':'#009E73','random':'#999933','M3':'#D55E00','M4':'#E69F00','M5':'#332288'}
LABELS=['Inlet fan\nPWM duty','Outlet fan\nPWM duty','Hatch\nangle (°)','Inlet speed\n(rpm)','Outlet speed\n(rpm)',
        'Inlet current\n(A)','Outlet current\n(A)','Upwind ΔP\n(Pa)','Downwind ΔP\n(Pa)','Intake ΔP\n(Pa)','Ambient\npressure (Pa)']
POS={0:(0,1.25),1:(0,.3),2:(0,-.65),10:(0,-1.6),3:(1,1.25),4:(1,.3),5:(1,-.65),6:(1,-1.6),7:(2,1.05),8:(2,-.15),9:(2,-1.35)}
OUTCOMES=['current_in','current_out','pressure_upwind','pressure_downwind','pressure_intake']
SHORT=['Inlet I\n(A)','Outlet I\n(A)','Upwind ΔP\n(Pa)','Downwind ΔP\n(Pa)','Intake ΔP\n(Pa)']
VARS=['load_in','load_out','hatch','rpm_in','rpm_out','current_in','current_out','pressure_upwind','pressure_downwind','pressure_intake','pressure_ambient']

def graph_edges(spec):
    if spec['kind']=='ensemble':return spec['components'][int(np.argmax(spec['weights']))]['edges']
    return spec.get('graph',{'edges':[]})['edges']

def prepare_plotting_data():
    """Derive extra plotting summaries from already sealed/evaluated predictions."""
    graphs=json.loads((ROOT/'reports/graphs_full.json').read_text());observed=pd.read_csv(RESULTS/'observed_effects.csv')
    costs=pd.read_csv(RESULTS/'costs.csv');protocol=json.loads((RESULTS/'protocol.json').read_text())
    boot=np.load(ROOT/'generated_samples/observed_bootstraps.npz');responses=[]
    names=['validate_load_in','validate_load_out','validate_hatch_rpms']
    for name in names:
        for method in ('M1','fixed','M3','M5'):
            row=costs[costs.method==method].iloc[0];samples=np.load(ROOT/row.prediction_artifact)
            for outcome in OUTCOMES[:4]:
                j=VARS.index(outcome);obs=observed[(observed.run==name)&(observed.outcome==outcome)].iloc[0]
                for arm in (0,1):
                    y=samples[name+'_'+str(arm)][:,j];ci=np.quantile(boot[name][:,arm,j],[.025,.975]);pi=np.quantile(y,[.05,.95])
                    responses.append({'run':name,'method':method,'outcome':outcome,'arm':arm,
                        'observed_mean':obs.low_mean if arm==0 else obs.high_mean,'observed_ci_low':ci[0],'observed_ci_high':ci[1],
                        'predicted_mean':y.mean(),'predictive_low90':pi[0],'predictive_high90':pi[1]})
    pd.DataFrame(responses).to_csv(RESULTS/'plot_responses.csv',index=False,float_format='%.8g')
    frequency=[]
    keys=[k for k in graphs if k.startswith('refit') and k.endswith('_M3')]
    for a in range(11):
        for b in range(11):
            n=sum([a,b] in graph_edges(graphs[k]['selected']) for k in keys)
            if n or [a,b] in graphs['M3']['initial']['edges'] or [a,b] in graph_edges(graphs['M3']['selected']):
                frequency.append({'source':a,'target':b,'selected_count':n,'grouped_refits':len(keys),'selection_frequency':n/len(keys)})
    pd.DataFrame(frequency).to_csv(RESULTS/'edge_frequency.csv',index=False,float_format='%.6g')
    main=json.loads((ROOT/'data/processed/main/manifest.json').read_text());scales=np.array(main['standardization']['std'])
    effects=pd.read_csv(ROOT/'reports/all_effects.csv');total=[]
    for target in VARS[:3]:
        runs=[r['run'] for r in protocol['final_design'] if r['panel']=='primary' and r['target']==target]
        for outcome in OUTCOMES:
            obs=observed[(observed.run.isin(runs))&(observed.outcome==outcome)];j=VARS.index(outcome)
            base={'target':target,'outcome':outcome,'observed_effect':obs.effect.mean(),'training_sd':scales[j]}
            for method in ['M1','M3','M5','fixed','semantic_M3']:
                sub=effects[(effects.method==method)&(effects.run.isin(runs))&(effects.outcome==outcome)]
                if len(sub):base[method]=sub.pred_effect.mean()
            total.append(base)
    pd.DataFrame(total).to_csv(RESULTS/'plot_total_effects.csv',index=False,float_format='%.8g')
    trade=[]
    for r in protocol['final_design']:
        if r['panel']!='primary':continue
        name=r['run'];obs=observed[observed.run==name];bs=boot[name]
        for arm in (0,1):
            col='low_mean' if arm==0 else 'high_mean';pressure=obs[obs.outcome=='pressure_upwind'][col].iloc[0]
            current=obs[obs.outcome.isin(['current_in','current_out'])][col].sum()
            pc=np.quantile(bs[:,arm,7],[.025,.975]);ic=np.quantile(bs[:,arm,5]+bs[:,arm,6],[.025,.975])
            trade.append({'run':name,'target':r['target'],'arm':arm,'pressure':pressure,'current':current,
                'pressure_low':pc[0],'pressure_high':pc[1],'current_low':ic[0],'current_high':ic[1]})
    pd.DataFrame(trade).to_csv(RESULTS/'plot_tradeoff.csv',index=False,float_format='%.8g')

def save(fig,name,selected=True):
    FIGURES.mkdir(parents=True,exist_ok=True)
    fig.savefig(FIGURES/(name+'.pdf'),metadata={'CreationDate':None,'ModDate':None},bbox_inches='tight',pad_inches=.06)
    fig.savefig(FIGURES/(name+'.svg'),metadata={'Date':None},bbox_inches='tight',pad_inches=.06)
    fig.savefig(FIGURES/(name+'.png'),dpi=220,bbox_inches='tight',pad_inches=.06)
    if selected and name in {'A_process_graph','D_accuracy_cost'}:
        (PHASE/'figures').mkdir(exist_ok=True);shutil.copyfile(FIGURES/(name+'.pdf'),PHASE/'figures'/(name+'.pdf'))
    plt.close(fig)

def draw_graph(ax,initial,selected,frequency=None,title=''):
    old=set(map(tuple,initial));new=set(map(tuple,selected));freq={} if frequency is None else {(int(r.source),int(r.target)):r.selection_frequency for r in frequency.itertuples()}
    for a,b in sorted(old|new):
        color='#999999' if (a,b) not in new else '#D55E00' if (a,b) not in old else '#0072B2'
        style=':' if (a,b) not in new else '--' if freq and freq.get((a,b),0)<.6 else '-'
        bend=(.42 if abs(POS[a][1]-POS[b][1])>1.5 else .23) if POS[a][0]==POS[b][0] else .05*(-1 if a>b else 1)
        clearance=13 if POS[a][0]==POS[b][0] else 24
        ax.add_patch(FancyArrowPatch(POS[a],POS[b],arrowstyle='-|>',mutation_scale=8,color=color,linestyle=style,
            linewidth=.85,shrinkA=clearance,shrinkB=clearance,connectionstyle=f'arc3,rad={bend}',zorder=1))
    for j,(x,y) in POS.items():
        ax.text(x,y,LABELS[j],ha='center',va='center',fontsize=7.7,bbox={'boxstyle':'round,pad=.3','fc':'#EAF2F8' if j in (0,1,2,10) else 'white','ec':'#666666','lw':.7},zorder=2)
    if not any(a==2 for a,b in new):
        ax.text(0,-1.03,'No modeled hatch pathway',ha='center',fontsize=6.1,color='#555555',fontstyle='italic')
    ax.set(xlim=(-.4,2.4),ylim=(-1.96,1.64));ax.set_axis_off();ax.set_title(title,loc='left',fontsize=9)

def main(prepare=False):
    if prepare:prepare_plotting_data()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'svg.hashsalt':'phase4-wind-tunnel','axes.linewidth':.7,'lines.linewidth':1})
    graphs=json.loads((RESULTS/'graphs.json').read_text());freq=pd.read_csv(RESULTS/'edge_frequency.csv')
    totals=pd.read_csv(RESULTS/'plot_total_effects.csv');responses=pd.read_csv(RESULTS/'plot_responses.csv')
    summary=pd.read_csv(RESULTS/'summary.csv').set_index('method');costs=pd.read_csv(RESULTS/'costs.csv').set_index('method')
    fig=plt.figure(figsize=(4.803,5.7));gs=fig.add_gridspec(2,1,height_ratios=[2.5,1],hspace=.32)
    ax=fig.add_subplot(gs[0]);draw_graph(ax,graphs['M3']['initial']['edges'],graph_edges(graphs['M3']['selected']),freq,'a  Predictive process model (M3)')
    handles=[Line2D([0],[0],color='#0072B2',label='Retained'),Line2D([0],[0],color='#D55E00',label='Added'),Line2D([0],[0],color='#999999',ls=':',label='Removed'),Line2D([0],[0],color='#333333',ls='--',label='Selected in <3/5 refits')]
    ax.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,-.15),ncol=2,frameon=False,fontsize=7)
    ax=fig.add_subplot(gs[1]);values=np.array([[totals[(totals.target==t)&(totals.outcome==o)].observed_effect.iloc[0]/totals[(totals.target==t)&(totals.outcome==o)].training_sd.iloc[0] for o in OUTCOMES] for t in VARS[:3]])
    limit=max(abs(values).max(),1e-6);im=ax.imshow(values,cmap='RdBu_r',vmin=-limit,vmax=limit,aspect='auto')
    for i,t in enumerate(VARS[:3]):
        for j,o in enumerate(OUTCOMES):
            val=totals[(totals.target==t)&(totals.outcome==o)].observed_effect.iloc[0]
            ax.text(j,i,f'{val:.3f}' if j<2 else f'{val:.1f}',ha='center',va='center',fontsize=7,color='white' if abs(values[i,j])>.55*limit else 'black')
    ax.set_xticks(range(5),SHORT,fontsize=7);ax.set_yticks(range(3),['Inlet fan','Outlet fan','Hatch'],fontsize=7)
    ax.set_title('b  Randomized total effects; numbers in physical units',loc='left',fontsize=8)
    fig.colorbar(im,ax=ax,fraction=.035,pad=.02,label='Effect / fitting SD')
    save(fig,'A_process_graph')
    for group,outcomes in [('pressure',['pressure_upwind','pressure_downwind']),('current',['current_in','current_out'])]:
        # Fan duty and hatch angle have different physical units. Share only
        # within a column; global sharing incorrectly reused hatch tick labels.
        fig,axes=plt.subplots(2,3,figsize=(4.803,3.5),sharex='col')
        for col,name in enumerate(['validate_load_in','validate_load_out','validate_hatch_rpms']):
            for row,o in enumerate(outcomes):
                ax=axes[row,col];sub=responses[(responses.run==name)&(responses.outcome==o)];obs=sub[sub.method=='M1'].sort_values('arm')
                ax.vlines(obs.arm,obs.observed_ci_low,obs.observed_ci_high,color='black',lw=1.4)
                ax.plot(obs.arm,obs.observed_mean,'ko-',label='Measured mean / 95% CI',ms=3)
                for method in ['M1','fixed','M3','M5']:
                    s=sub[sub.method==method].sort_values('arm');ax.plot(s.arm,s.predicted_mean,'o--',color=COLORS[method],ms=2.3,label=method)
                if col==0:ax.set_ylabel(o.replace('pressure_','').replace('current_','')+(' ΔP (Pa)' if group=='pressure' else ' current (A)'))
                if row==0:ax.set_title(['Inlet command','Outlet command','Hatch command'][col],fontsize=8)
                ax.set_xticks([0,1],['0.01','1'] if col<2 else ['0°','45°']);ax.tick_params(labelsize=7);ax.grid(alpha=.15)
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=6.8,frameon=False)
        fig.subplots_adjust(left=.15,right=.99,top=.9,bottom=.23,hspace=.4,wspace=.5);save(fig,'B_'+group+'_responses')
    methods=['observed_effect','M1','M3','M5'];fig,axes=plt.subplots(4,1,figsize=(4.803,4.8),sharex=True)
    matrices=[]
    for method in methods:matrices.append(np.array([[totals[(totals.target==t)&(totals.outcome==o)][method].iloc[0]/totals[(totals.target==t)&(totals.outcome==o)].training_sd.iloc[0] for o in OUTCOMES] for t in VARS[:3]]))
    lim=max(np.max(np.abs(v)) for v in matrices)
    for ax,method,mat in zip(axes,methods,matrices):
        im=ax.imshow(mat,cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto');ax.set_yticks(range(3),['Inlet','Outlet','Hatch'],fontsize=7)
        ax.set_title('Measured randomized effects' if method=='observed_effect' else method+' predicted effects',loc='left',fontsize=8)
        for i in range(3):
            for j in range(5):ax.text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',fontsize=7,color='white' if abs(mat[i,j])>.55*lim else 'black')
    axes[-1].set_xticks(range(5),['Inlet I','Outlet I','Upwind ΔP','Downwind ΔP','Intake ΔP'],fontsize=7)
    fig.subplots_adjust(left=.13,right=.85,top=.95,bottom=.08,hspace=.65);fig.colorbar(im,cax=fig.add_axes([.88,.15,.025,.7]),label='Effect / fitting SD')
    save(fig,'C_effect_heatmap')
    fig,axes=plt.subplots(1,2,figsize=(4.803,3.3),sharey=True)
    for i,method in enumerate(METHODS):
        row=summary.loc[method];axes[0].hlines(i,row.ci_low,row.ci_high,color=COLORS[method],lw=1.6);axes[0].plot(row.effect_error,i,'o',color=COLORS[method],ms=4)
        axes[1].plot(max(costs.loc[method,'logical_seconds'],1e-5),i,'o',color=COLORS[method],ms=4)
    axes[0].set_yticks(range(8),METHODS);axes[0].invert_yaxis();axes[0].set_xlabel('Contrast error / fitting SD');axes[0].set_title('a  Accuracy; paired block CI',fontsize=8)
    axes[1].set_xscale('log');axes[1].set_xlabel('Charged training + selection (s)');axes[1].set_title('b  Standalone computation',fontsize=8)
    for ax in axes:ax.grid(axis='x',alpha=.2)
    fig.subplots_adjust(left=.13,right=.98,bottom=.2,top=.9,wspace=.25);save(fig,'D_accuracy_cost')
    trade=pd.read_csv(RESULTS/'plot_tradeoff.csv');protocol=json.loads((RESULTS/'protocol.json').read_text())
    fig,ax=plt.subplots(figsize=(4.803,3.25));palette={'load_in':'#0072B2','load_out':'#D55E00','hatch':'#009E73'}
    for name,rows in trade.groupby('run',sort=True):
        rows=rows.sort_values('arm');color=palette[rows.target.iloc[0]]
        ax.plot(rows.current,rows.pressure,':',color=color,lw=.8)
        ax.hlines(rows.pressure,rows.current_low,rows.current_high,color=color,lw=1)
        ax.vlines(rows.current,rows.pressure_low,rows.pressure_high,color=color,lw=1)
        ax.scatter(rows.current,rows.pressure,c=[color,color],marker='o',s=[20,42],edgecolor='white',linewidth=.4)
    ax.axhline(protocol['decision']['threshold_pa'],color='#333333',ls='--',lw=.8,label='Development pressure target')
    ax.set(xlabel='Measured total fan current (A)',ylabel='Measured upwind − ambient pressure (Pa)')
    handles=[Line2D([0],[0],marker='o',color=c,ls=':',label=t.replace('load_in','Inlet fan').replace('load_out','Outlet fan').replace('hatch','Hatch')) for t,c in palette.items()]
    handles.append(Line2D([0],[0],color='#333333',ls='--',label='Frozen pressure target'))
    ax.legend(handles=handles,fontsize=7,frameon=False,loc='best');ax.grid(alpha=.15);fig.tight_layout();save(fig,'E_recorded_tradeoff')
    spec=graphs['M5']['selected'];components=spec.get('components',[spec.get('graph')]);weights=spec.get('weights',[1.])
    for i,(g,w) in enumerate(zip(components,weights)):
        fig,ax=plt.subplots(figsize=(4.803,3.6));draw_graph(ax,graphs['M5']['initial']['edges'],g['edges'],title=f'M5 component {i+1}; predictive mixture weight {w:.3f}')
        fig.tight_layout();save(fig,f'S_M5_component_{i+1}',False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args();main(args.prepare)
