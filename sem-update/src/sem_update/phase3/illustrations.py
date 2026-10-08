"""Actual-model response curves and common-layout graph illustrations."""
from pathlib import Path
import json
import networkx as nx
import numpy as np
import pandas as pd
import torch
from sem_update.graphs import DAG
from sem_update.phase2.models import sample
from .runtime import root,RESULTS,job,atomic_json,read_json,digest,file_hash,freeze_guard,require_cuda
from .data import load,System,seed_for
from .evaluation import model_from_spec

@torch.no_grad()
def gather():
    protocol=freeze_guard();require_cuda();rows=[];graphs=[]
    tasks=[dict(next(t for t in protocol['tasks'] if t['d']==100 and t['family']=='heteroscedastic' and t['profile']=='sparse')),
           dict(next(t for t in protocol['tasks'] if t['profile']=='deep'))]
    for task in tasks:task.update(illustration_corruption=.5,illustration_kind='prespecified')
    frame=pd.read_csv(RESULTS/'metrics.csv')
    if 'endpoint' in frame:frame=frame[frame.endpoint=='T2']
    adverse=frame[(frame.sensitivity=='primary')&(frame.resource=='adjusted')&frame.method.isin(['M3','M4','M5'])&(frame.harmful==1)].copy()
    if len(adverse):
        adverse['excess']=adverse.delta_fixed-np.maximum(.001,.05*(adverse.sw1-adverse.delta_fixed))
        worst=adverse.sort_values(['excess','scm','method'],ascending=[False,True,True]).iloc[0]
        task=dict(next(t for t in protocol['tasks'] if t['seed']==worst.scm and t.get('sensitivity','primary')=='primary'))
        task.update(illustration_corruption=float(worst.corruption),illustration_kind='adverse',adverse_method=worst.method,
                    adverse_prediction_key=worst.prediction_key)
        tasks.append(task)
    with job('paper-illustrations',{'protocol':file_hash(RESULTS/'protocol.json'),'tasks':tasks,'grid':21,'source':file_hash(__file__)}) as active:
        if not active:return
        samples={};folder=root()/'illustrations';folder.mkdir(exist_ok=True)
        for ti,task in enumerate(tasks):
            name=f"{task['profile']}-{task['family']}-d{task['d']}-s{task['seed']}-B{protocol['config']['budget_per_target']}-c{task['illustration_corruption']:g}"
            if not (root()/'runs'/name/'adjusted-frozen.json').exists():continue
            record=read_json(root()/'runs'/name/'adjusted-frozen.json');data=load(root()/record['data_folder'],allowed=('fit','early'))
            system=System(task['d'],task['family'],task['profile'],task['seed']);net=system.graph.networkx()
            targets=[j for j in data.manifest['seen_targets'] if nx.descendants(net,j)]
            if not targets:raise ValueError('Prespecified illustration system has no visible target with descendants')
            target=min(targets);outcome=min(net.successors(target))
            rule='First prespecified replicate, c0.5, adjusted; lowest visible label with descendants; lowest direct-child label'
            if task['illustration_kind']=='adverse':
                value=read_json(root()/'generated_samples'/task['adverse_prediction_key']/'metrics.json')
                fixed_row=frame[(frame.scm==task['seed'])&(frame.resource=='adjusted')&(frame.corruption==task['illustration_corruption'])&(frame.method=='fixed')&(frame.sensitivity=='primary')].iloc[0]
                fixed=read_json(root()/'generated_samples'/fixed_row.prediction_key/'metrics.json')
                differences={v['environment']:v['sw1']-next(b['sw1'] for b in fixed['metrics'] if b['environment']==v['environment']) for v in value['metrics'] if v['endpoint']=='T2'}
                environment=min(differences,key=lambda k:(-differences[k],k));target=int(environment.split('-do')[-1])
                vector=value['vectors'][environment];keep=[j for j in range(task['d']) if j!=target]
                outcome=keep[int(np.argmax(np.abs(np.asarray(vector['actual_effect'])-np.asarray(vector['predicted_effect']))))]
                rule='Post-evaluation adverse example: largest harmful excess over the frozen threshold; worst T2 regime change vs G0; largest non-target effect error'
            mu=torch.tensor(data.manifest['standardization']['mean'],device='cuda');sd=torch.tensor(data.manifest['standardization']['std'],device='cuda')
            cfg=record['config'];models={k:model_from_spec(record['methods'][k]['selected'],data,cfg) for k in ('fixed','M1','M2','M3','M4','M5','oracle') if k in record['methods']}
            for level in np.linspace(-2,2,21):
                actual=system.sample(2048,seed_for(task['seed'],'curve'),{target:{'kind':'fixed','value':float(mu[target]+sd[target]*level)}})
                actual=(actual-mu)/sd
                values={'reference':actual}
                for method,model in models.items():values[method]=sample(model,{target:{'kind':'fixed','value':float(level)}},2048,seed_for(task['seed'],'model-curve'))
                for method,x in values.items():
                    vector=x[:,outcome];q=torch.quantile(vector,torch.tensor([.05,.95],device='cuda'))
                    row={'illustration':ti,'scm':task['seed'],'d':task['d'],'profile':task['profile'],'target':target,'outcome':outcome,
                        'assignment':float(level),'method':method,'mean':float(vector.mean()),'q05':float(q[0]),'q95':float(q[1]),'n':len(vector)}
                    rows.append(row);samples[f'case{ti}_{method}_{level:.2f}']=vector.cpu().numpy()
            undirected=net.to_undirected();distance=nx.single_source_shortest_path_length(undirected,target,cutoff=2)
            local=sorted(distance,key=lambda j:(distance[j],j))[:15]
            if outcome not in local:local=local[:14]+[outcome]
            positions=nx.spring_layout(net,seed=37114,iterations=150)
            local_positions=nx.spring_layout(net.subgraph(local),seed=37114,iterations=150)
            selected=record['methods']['M5']['selected']
            components=selected.get('components',[selected['graph']] if selected['kind']=='flow' else [])
            weights=selected.get('weights',[1.])
            repair=task.get('adverse_method','M3')
            if repair=='M5':repair='M3'
            panels=[{'label':'Reference','graph':system.graph.json()},{'label':'Initial G0','graph':record['prior']['graph']},
                {'label':repair+' returned','graph':record['methods'][repair]['selected']['graph']}]
            representative=int(np.argmax(weights))
            panels += [{'label':f'M5 component {i+1}; w={w:.3f}'+('; representative' if i==representative else ''),
                'graph':g,'weight':w,'highest_weight_representative':i==representative} for i,(g,w) in enumerate(zip(components,weights))]
            graphs.append({'scm':task['seed'],'d':task['d'],'profile':task['profile'],'target':target,'outcome':outcome,
                'illustration':ti,'kind':task['illustration_kind'],'corruption':task['illustration_corruption'],
                'adverse_method':task.get('adverse_method'),'local_nodes':local,
                'positions':{str(k):v.tolist() for k,v in positions.items()},
                'local_positions':{str(k):v.tolist() for k,v in local_positions.items()},'panels':panels,
                'selection_rule':rule,
                'local_rule':'two-hop undirected reference neighborhood, capped at 15 by distance then label; the plotted outcome replaces the last node if otherwise absent',
                'weights_meaning':'predictive mixture weights, not causal graph probabilities'})
        np.savez_compressed(folder/'response_outcome_samples.npz',**samples)
        pd.DataFrame(rows).to_csv(RESULTS/'responses.csv',index=False,float_format='%.8g')
        atomic_json(RESULTS/'illustration_graphs.json',graphs)
        atomic_json(RESULTS/'response_manifest.json',{'artifact':'illustrations/response_outcome_samples.npz',
            'sha256':file_hash(folder/'response_outcome_samples.npz'),'rows':len(rows),'samples_per_curve_setting':2048,
            'intervals':'5th and 95th predictive quantiles, not confidence intervals','source_sha256':file_hash(__file__)})

def render_curated():
    from .reporting import style,save,COLORS
    plt=style();path=RESULTS/'responses.csv'
    if not path.exists():return
    data=pd.read_csv(path);graphs=read_json(RESULTS/'illustration_graphs.json')
    fig,axes=plt.subplots(len(graphs),1,figsize=(4.8,2.3*len(graphs)),layout='constrained',squeeze=False)
    colors={**COLORS,'reference':'black','fixed':'#999999','oracle':'#56B4E9'}
    for ax,case in zip(axes[:,0],graphs):
        rows=data[data.illustration==case['illustration']]
        for method in ['reference','fixed','M1','M2','M3','M4','M5','oracle']:
            part=rows[rows.method==method].sort_values('assignment')
            if not len(part):continue
            ax.plot(part.assignment,part['mean'],label=method,lw=1.2 if method=='reference' else .9,
                    ls='--' if method in ('fixed','oracle') else '-',color=colors[method])
            if method in ('reference','M5'):ax.fill_between(part.assignment,part.q05,part.q95,color=colors[method],alpha=.09)
        ax.set(xlabel=f'Assigned V{case["target"]} (training SD)',ylabel=f'V{case["outcome"]} (training SD)',
               title=f'{case["d"]} nodes, {case["profile"]}'+(' — adverse case' if case['kind']=='adverse' else ''))
    axes[0,0].legend(ncol=4,fontsize=8);save(fig,'F7_responses');plt.close(fig)

    for index,case in enumerate(graphs):
        panels=case['panels']
        # Whole-graph overview and readable local view use identical positions
        # across reference/initial/returned/component models.
        for view in ('whole','local'):
            positions={int(k):v for k,v in case['positions' if view=='whole' else 'local_positions'].items()}
            whole=view=='whole';nrows=(len(panels)+1)//2
            fig,axes=plt.subplots(nrows,2,figsize=(4.8,2.15*nrows),layout='constrained',squeeze=False)
            for ax,panel in zip(axes.flat,panels):
                graph=DAG.from_json(panel['graph']).networkx()
                nodes=list(graph) if whole else case['local_nodes'];sub=graph.subgraph(nodes)
                nx.draw_networkx_edges(sub,positions,ax=ax,width=.4 if whole else .8,alpha=.4 if whole else .8,
                    arrows=True,arrowstyle='-|>',arrowsize=4 if whole else 9,node_size=9 if whole else 100)
                nx.draw_networkx_nodes(sub,positions,ax=ax,node_size=9 if whole else 100,
                    node_color=['#D55E00' if j==case['target'] else '#0072B2' for j in sub])
                if not whole:nx.draw_networkx_labels(sub,positions,ax=ax,font_size=8,labels={j:str(j) for j in sub})
                ax.set_axis_off()
                ax.set_title(panel['label'].replace('; ','\n'),fontsize=8)
            for ax in list(axes.flat)[len(panels):]:ax.set_axis_off()
            fig.suptitle(f'{case["d"]}-node {case["profile"]}: '+('whole graph' if whole else 'declared local subgraph'),fontsize=9)
            save(fig,'F'+str(8+index)+'_graphs_'+case['profile']+'_'+view);plt.close(fig)

if __name__=='__main__':gather()
