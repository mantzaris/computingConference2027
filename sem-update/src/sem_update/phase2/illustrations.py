"""Frozen-model GPU response curves and conditional real block uncertainty."""
import math
import numpy as np
import pandas as pd
import torch
import networkx as nx
from sem_update.graphs import DAG
from sem_update.data import SyntheticSCM
from sem_update.metrics import projections
from sem_update.real_uncertainty import resample_blocks,projected_bootstrap
from .runtime import root,RESULTS,job,atomic_json,read_json,digest,file_hash,freeze_guard
from .data import load,final_environments
from .evaluation import model_from_spec
from .models import sample

@torch.no_grad()
def responses():
    protocol=freeze_guard();cfg=protocol['config']
    if not (RESULTS/'final_test_access.json').exists():raise RuntimeError('Final evaluation has not been authorized by the freeze')
    choices=read_json(RESULTS/'illustration_choices.json')
    tasks={t['task_id']:t for t in read_json(RESULTS/'selected_models.json')['tasks']}
    path=RESULTS/'response_curves.csv';key=digest(choices)
    with job('response-curves-'+key[:20],{'protocol':protocol['protocol_hash'],'choices':choices,'points':17,'n':2048}) as active:
        if active:
            rows=[]
            for case in ('representative','adverse'):
                if not choices[case]:continue
                task=tasks[choices[case]];folder=root()/'data/processed'/task['data_id'];data=load(folder,allowed=('fit','early'))
                scm=SyntheticSCM(data.d,task['family'],task['seed'])
                if digest(scm.json())!=digest(read_json(folder/'truth.json')):raise ValueError('Illustration truth changed')
                target=min(data.manifest['seen_targets']);desc=sorted(nx.descendants(scm.graph.networkx(),target))
                outcome=desc[0] if desc else min(j for j in range(data.d) if j!=target)
                mu=torch.tensor(data.manifest['standardization']['mean'],device='cuda')
                sd=torch.tensor(data.manifest['standardization']['std'],device='cuda');arrays={}
                for method in ['truth','fixed','M0','M1','M2','M3','M4','M5']:
                    model=None if method=='truth' else model_from_spec(task['methods'][method]['selected'],data,cfg)
                    for i,value in enumerate(np.linspace(-2,2,17)):
                        seed=task['seed']+831019
                        if method=='truth':
                            law={target:{'kind':'fixed','value':float(mu[target]+sd[target]*value)}}
                            y=(scm.sample(2048,seed,law,device='cuda')-mu)/sd
                        else:y=sample(model,{target:{'kind':'fixed','value':float(value)}},2048,seed,'cuda')
                        q=torch.quantile(y[:,outcome],torch.tensor([.05,.5,.95],device='cuda'))
                        rows.append({'case':case,'task_id':task['task_id'],'method':method,'target':target,'outcome':outcome,
                            'assignment_standardized':float(value),'mean':y[:,outcome].mean().item(),'q05':q[0].item(),
                            'median':q[1].item(),'q95':q[2].item(),'samples':2048,'seed':seed,
                            'model_hash':'reference-SCM' if method=='truth' else digest(task['methods'][method]['selected'])})
                        arrays[f'{method}_{i}']=y.cpu().numpy()
                    del model
                np.savez_compressed(root()/'generated_samples'/('response-'+case+'.npz'),**arrays)
            pd.DataFrame(rows).to_csv(path,index=False,float_format='%.9g')
    return pd.read_csv(path)

@torch.no_grad()
def real_intervals():
    protocol=freeze_guard();cfg=protocol['config'];frame=pd.read_csv(RESULTS/'metrics.csv')
    selected=frame[(frame.study=='real')&(frame.stage=='selected')&frame.endpoint.isin(['T2','T2_exploratory'])&~frame.method.str.startswith('checkpoint_')]
    item=next(i for i in protocol['matrix'] if i['study']=='real');folder=root()/'data/processed'/item['data_id']
    path=RESULTS/'real_block_intervals.json'
    with job('real-block-intervals',{'protocol':protocol['protocol_hash'],'repeats':200,'block_rows':10}) as active:
        if active:
            groups=final_environments(folder);models=[];comparisons=[];saved={}
            for endpoint,part in selected.groupby('endpoint'):
                part=part.reset_index(drop=True);draws=[]
                for ei,e in enumerate(groups[endpoint]):
                    keep=[j for j in range(e.x.shape[1]) if j not in e.targets]
                    v=projections(len(keep),cfg['evaluation_projections'],item['seed']+170011+ei*31,'cuda')
                    q=(torch.arange(512,device='cuda')+.5)/512;predictions=[]
                    for row in part.itertuples():
                        key=row.evaluation_artifact.rsplit('/',1)[1].removesuffix('.json')
                        with np.load(root()/'generated_samples'/(key+'.npz')) as archive:
                            y=torch.tensor(archive[e.name],device='cuda')[:,keep]@v
                        predictions.append(torch.quantile(y,q,dim=0))
                    generator=torch.Generator(device='cuda').manual_seed(cfg['bootstrap_seed']+ei)
                    indices=resample_blocks(len(e.x),cfg['real_block_rows'],200,generator,'cuda')
                    draws.append(projected_bootstrap(e.x[:,keep]@v,torch.stack(predictions),indices).cpu().numpy())
                values=np.stack(draws).mean(0);saved[endpoint]=values
                for i,row in part.iterrows():
                    lo,hi=np.quantile(values[:,i],[.025,.975])
                    models.append({'task_id':row.task_id,'method':row.method,'metadata_variant':row.metadata_variant,
                        'endpoint':endpoint,'sw1':row.sw1,'conditional_low':float(lo),'conditional_high':float(hi),
                        'replicates':200,'block_rows':10,'independent_apparatuses':1})
                for variant in cfg['metadata_variants']:
                    for name in ['M3','M4','M5','llm_edit']:
                        a=part.index[(part.method==name)&(part.metadata_variant==variant)][0]
                        for ref in ['fixed','M1','M2']:
                            b=part.index[(part.method==ref)&(part.metadata_variant==variant)][0]
                            lo,hi=np.quantile(values[:,a]-values[:,b],[.025,.975])
                            comparisons.append({'metadata_variant':variant,'endpoint':endpoint,'comparison':name+' - '+ref,
                                'delta':float(part.iloc[a].sw1-part.iloc[b].sw1),'conditional_low':float(lo),'conditional_high':float(hi)})
            np.savez_compressed(root()/'generated_samples/real_block_bootstrap.npz',**saved)
            atomic_json(path,{'models':models,'comparisons':comparisons,
                'scope':'conditional ten-row observation-block uncertainty; fixed models and generated samples; one familiar apparatus'})
    value=read_json(path)
    pd.DataFrame(value['models']).to_csv(RESULTS/'real_block_intervals.csv',index=False,float_format='%.9g')
    pd.DataFrame(value['comparisons']).to_csv(RESULTS/'real_block_comparisons.csv',index=False,float_format='%.9g')
    return value

def response_figures(curated_only=False):
    from .reporting import setup_plot,save,COLORS,MARKERS,MAIN
    import matplotlib.pyplot as plt
    data=pd.read_csv(RESULTS/'response_curves.csv') if curated_only else responses()
    setup_plot();cases=list(data.case.unique())
    fig,axes=plt.subplots(1,len(cases),figsize=(4.8,2.6),squeeze=False)
    for ax,case in zip(axes.flat,cases):
        part=data[data.case==case]
        for method in ['truth',*MAIN]:
            p=part[part.method==method].sort_values('assignment_standardized')
            color='black' if method=='truth' else COLORS[method]
            ax.plot(p.assignment_standardized,p['mean'],color=color,label=method,
                    linestyle='--' if method=='truth' else '-',marker=None if method=='truth' else MARKERS[method],markevery=4,ms=2.5)
            if method in ('truth','M5'):ax.fill_between(p.assignment_standardized,p.q05,p.q95,color=color,alpha=.08)
        target=int(part.iloc[0].target);outcome=int(part.iloc[0].outcome)
        ax.set(xlabel=f'do(V{target}) [training SD]',ylabel=f'V{outcome} [training SD]',title=case.capitalize());ax.grid(alpha=.15)
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=4,loc='lower center',bbox_to_anchor=(.5,0),frameon=False)
    fig.suptitle('Mean response; shading = 90% predictive bands (truth, M5)',fontsize=8)
    fig.tight_layout(rect=(0,.22,1,.94));save(fig,'F6_response_curves')
    return data
