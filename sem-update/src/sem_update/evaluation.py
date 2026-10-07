"""Final outcomes are accessible only through a frozen-selection gate."""
import csv
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .runtime import PROJECT,artifact_root,read_json,atomic_json,file_hash,digest,Ledger
from .data import Environment,SyntheticSCM,assign_values,load_learner
from .graphs import DAG,structural_metrics
from .flows import balanced_nll
from .metrics import distribution_metrics
from .training import fit_graph

def load_final_environments(manifest,root,device='cuda'):
    """Never imported by training/search; called only after frozen manifest checks."""
    if manifest['family']=='real':
        from .chambers import DATASET,VARIABLES
        designs=read_json(root/'sealed_test_design.json')
        mean=np.array(manifest['standardization']['mean'])
        std=np.array(manifest['standardization']['std'])
        quantum=np.array(manifest['dequantization_quantum'])
        groups={}
        for r in designs:
            frame=pd.read_csv(artifact_root()/'data/raw'/DATASET/(r['name']+'.csv'))
            x=frame[VARIABLES].to_numpy(dtype=float)
            x=x+(np.random.default_rng(r['dequant_seed']).random(x.shape)-.5)*quantum
            x=((x[r['start']:r['stop']]-mean)/std).astype('float32')
            env=Environment(r['name'],torch.tensor(x,device=device),r['assignments'],
                            tuple(f'{r["name"]}:{i}' for i in range(r['start'],r['stop'])),
                            tuple(sorted({i//10 for i in range(r['start'],r['stop'])})))
            groups.setdefault(r['endpoint'],[]).append(env)
        return groups
    d,seed=manifest['d'],manifest['seed']
    scm=SyntheticSCM(d,manifest['family'],seed,manifest.get('semantic',False))
    if digest(scm.json())!=digest(read_json(root/'truth.json')):
        raise RuntimeError('generator changed since data freeze')
    mu=torch.tensor(manifest['standardization']['mean'],device=device)
    sd=torch.tensor(manifest['standardization']['std'],device=device)
    seen=manifest['seen_targets']
    groups={}
    for endpoint,targets,setting,offset in [('T1',seen,1.,50000),('T2',seen,-1.,60000),
                                           ('T3',[j for j in range(d) if j not in seen],1.,70000)]:
        groups[endpoint]=[]
        for j in targets:
            law={j:{'kind':'normal','mean':float(mu[j]+setting*sd[j]),'scale':float(.25*sd[j])}}
            x=(scm.sample(2048,seed*1000+offset+j,law,device=device)-mu)/sd
            groups[endpoint].append(Environment(f'{endpoint}-do{j}',x,
                                   {j:{'kind':'normal','mean':setting,'scale':.25}},
                                   tuple(f'{seed}:{endpoint}:{j}:{i}' for i in range(2048))))
    x=(scm.sample(1024,seed*1000+80000,device=device)-mu)/sd
    groups['observational']=[Environment('test-observational',x,{},tuple(f'{seed}:finalobs:{i}' for i in range(1024)))]
    return groups

@torch.no_grad()
def evaluate_model(model,groups,seed,n=2048,projection_count=256,sample_path=None):
    endpoints={}
    environment_rows=[]
    arrays={}
    for endpoint,environments in groups.items():
        rows=[]
        for i,env in enumerate(environments):
            g=torch.Generator(device=env.x.device).manual_seed(seed+i*31+sum(map(ord,endpoint)))
            u=torch.randn(n,model.graph.d,generator=g,device=env.x.device)
            values=assign_values(env.assignments,n,g,env.x.device)
            y=model.sample_intervention(u,values)
            keep=[j for j in range(model.graph.d) if j not in env.targets]
            metrics=distribution_metrics(env.x[:,keep],y[:,keep],projection_count,seed+i*31)
            metrics.update(environment=env.name,endpoint=endpoint,actual_rows=len(env.x),generated_rows=n,
                           blocks=len(env.blocks),nll=-model.log_probability(env.x,env.targets).mean().item(),
                           non_target_nodes=keep,outcome_means_actual=env.x[:,keep].mean(0).tolist(),
                           outcome_means_generated=y[:,keep].mean(0).tolist())
            rows.append(metrics)
            environment_rows.append(metrics)
            arrays[env.name]=y.cpu().numpy()
        if rows:
            endpoint_values={k:float(np.mean([row[k] for row in rows])) for k in rows[0] if isinstance(rows[0][k],(float,int))}
            endpoint_values['nll']=balanced_nll(model,environments).item()
            endpoint_values['environment_count']=len(rows)
            endpoints[endpoint]=endpoint_values
    observed_reference=groups['observational'][0].x.mean(0).cpu().numpy()
    generated_reference=arrays[groups['observational'][0].name].mean(0)
    for row in environment_rows:
        keep=row['non_target_nodes']
        actual_effect=np.array(row['outcome_means_actual'])-observed_reference[keep]
        predicted_effect=np.array(row['outcome_means_generated'])-generated_reference[keep]
        row['mean_effect_rmse']=float(np.sqrt(np.mean((actual_effect-predicted_effect)**2)))
    for endpoint,values in endpoints.items():
        values['mean_effect_rmse']=float(np.mean([r['mean_effect_rmse'] for r in environment_rows if r['endpoint']==endpoint]))
    if sample_path:
        np.savez_compressed(sample_path,**arrays)
    return {'endpoints':endpoints,'environments':environment_rows}

def evaluate(frozen_manifest=None):
    from .cli import require_cuda
    from .experiments import implementation_hash,timed_job
    require_cuda()
    frozen=read_json(frozen_manifest or PROJECT/'results/curated/frozen_selections.json')
    protocol=read_json(PROJECT/'results/curated/frozen_protocol.json')
    index_path=PROJECT/'results/curated/run_index.json'
    index=read_json(index_path)
    if not index['complete'] or frozen['run_index_sha256']!=file_hash(index_path):
        raise RuntimeError('all selected models must be frozen before final evaluation')
    if frozen['protocol_hash']!=protocol['protocol_hash'] or frozen['implementation_hash']!=implementation_hash():
        raise RuntimeError('protocol/source mismatch at final evaluation')
    if frozen['selected_graphs_sha256']!=file_hash(PROJECT/'results/curated/selected_graphs.json') or frozen['mechanism_manifest_sha256']!=file_hash(PROJECT/'results/curated/mechanism_manifest.csv'):
        raise RuntimeError('frozen graph/mechanism manifest changed')
    access_path=PROJECT/'results/curated/final_test_access.json'
    if access_path.exists() and read_json(access_path)['frozen_selection_hash']!=digest(frozen):
        raise RuntimeError('final outcomes already exposed under another frozen selection')
    atomic_json(access_path,{'frozen_selection_hash':digest(frozen),'purpose':'one prespecified final evaluation; no tuning afterward'})
    rows,env_rows=[],[]
    data_cache={}
    ledger=Ledger()
    cfg=protocol['config']
    for run in index['runs']:
        root=artifact_root()/'data/processed'/run['data_id']
        selection_path=artifact_root()/'runs'/run['run_id']/'selection.json'
        if file_hash(selection_path)!=run['selection_sha256']:
            raise RuntimeError('selection changed after freeze')
        selection=read_json(selection_path)
        if run['data_id'] not in data_cache:
            data=load_learner(root,'cuda')
            if data.key!=run['data_hash']:
                raise RuntimeError('dataset changed after selection')
            groups=load_final_environments(data.manifest,root)
            # Cross-check final row IDs against all selection roles.
            non_test={v for envs in data.roles.values() for e in envs for v in e.row_ids}
            if any(non_test & set(e.row_ids) for envs in groups.values() for e in envs):
                raise RuntimeError('final/non-test row overlap')
            data_cache={run['data_id']:(data,groups)}
        data,groups=data_cache[run['data_id']]
        truth=None if run['study']=='real' else DAG.from_json(read_json(root/'truth.json')['graph'])
        for stage in ('initial','before_audit','selected'):
            graph=DAG.from_json(selection['candidates'][selection[stage]]['graph'])
            key=digest({'data':data.key,'graph':graph.key,'kind':selection['identity']['kind'],
                        'protocol':protocol['protocol_hash']})
            path=artifact_root()/'runs'/('evaluation-'+key+'.json')
            samples=artifact_root()/'generated_samples'/(key+'.npz')
            def final_job():
                model,_=fit_graph(data,graph,cfg['train'],selection['identity']['kind'],allow_training=False)
                result=evaluate_model(model,groups,run['seed']+170011,cfg['evaluation_samples'],
                                      cfg['evaluation_projections'],samples)
                atomic_json(path,result)
            timed_job(ledger,'evaluation-'+key,{'protocol':protocol['protocol_hash'],'key':key},final_job,60)
            result=read_json(path)
            base={k:run[k] for k in ('run_id','study','d','family','seed','budget','method','corruption','metadata_variant')}
            base.update(stage=stage,graph_hash=graph.key,candidate_count=selection['candidate_count'],
                        wall_seconds=selection['wall_seconds'],audit_pass=selection['audit']['pass'],
                        unique_parent_sets=selection['unique_parent_sets'],new_parent_sets=selection['new_parent_sets'],
                        optimizer_updates=selection['optimizer_updates'],peak_vram_bytes=selection['peak_vram_bytes'],
                        canonical_optimizer_updates=selection['canonical_optimizer_updates'],
                        canonical_fit_seconds=selection['canonical_fit_seconds'],
                        flow_peak_vram_bytes=selection['flow_peak_vram_bytes'],
                        llm_edit_attempts=selection['llm_edit_attempts'],
                        llm_edit_invalid_attempts=selection['llm_edit_invalid_attempts'],
                        llm_edit_rejected_graphs=selection['llm_edit_rejected_graphs'],
                        realized_initial_shd=run.get('realized_initial_shd'),data_id=run['data_id'],
                        actual_non_test_intervention_rows=data.manifest['non_test_intervention_rows'],
                        evaluation_artifact='runs/'+path.name,evaluation_sha256=file_hash(path))
            base['dcdi_discovery_seconds']=run.get('dcdi_discovery',{}).get('seconds',0.)
            base['data_initializer_seconds']=run['data_initializer_seconds_once_per_dataset'] if run['method']=='data_only' or run['metadata_variant']!='none' else 0.
            if run['metadata_variant']!='none':
                proposal=read_json(artifact_root()/'runs/proposals'/f'{run["data_id"]}-{run["metadata_variant"]}.json')
                base['llm_initialization_seconds']=proposal['stage_seconds']
                base['peak_vram_bytes']=max(base['peak_vram_bytes'],max(r['stats']['peak_vram_bytes'] for r in proposal['records']))
            else:
                base['llm_initialization_seconds']=0.
            base['method_component_seconds']=sum(base[k] for k in ('wall_seconds','dcdi_discovery_seconds','data_initializer_seconds','llm_initialization_seconds'))
            if truth is not None:
                base.update(structural_metrics(graph,truth))
            for endpoint,metrics in result['endpoints'].items():
                rows.append({**base,'endpoint':endpoint,**metrics})
            for env in result['environments']:
                env_rows.append({**base,**env,'marginal_w1':json.dumps(env['marginal_w1'])})
        full=pd.DataFrame(rows)
        full.to_csv(artifact_root()/'runs/evaluation_all_metrics.csv',index=False)
        # Selected endpoints plus T2 before/after repair retain every independent
        # unit needed for primary comparisons without duplicating all raw records.
        curated=full[(full.stage=='selected')|(full.endpoint=='T2')]
        curated.to_csv(PROJECT/'results/curated/metrics.csv',index=False)
        per_env=pd.DataFrame(env_rows)
        per_env.to_csv(artifact_root()/'runs/evaluation_environment_metrics.csv',index=False)
        per_env[(per_env.study=='real')&(per_env.stage=='selected')].to_csv(PROJECT/'results/curated/real_intervention_metrics.csv',index=False)
        print(json.dumps({'evaluated':run['run_id'],'rows':len(rows)}),flush=True)
    atomic_json(PROJECT/'results/curated/evaluation_complete.json',{'frozen_selection_hash':digest(frozen),
                'metrics_sha256':file_hash(PROJECT/'results/curated/metrics.csv'),'rows':len(rows),
                'runs':len(index['runs']),'status':'complete'})

def paired_results(frame,method='diagnostic',comparator='fixed',stage='selected'):
    subset=frame[(frame.endpoint=='T2')&(frame.stage==stage)]
    keys=['study','d','family','seed','budget','corruption','metadata_variant']
    a=subset[subset.method==method]
    b=subset[subset.method==comparator]
    paired=a.merge(b,on=keys,suffixes=('_method','_comparison'),validate='one_to_one')
    paired['delta']=paired.sw1_method-paired.sw1_comparison
    threshold=np.maximum(.001,.05*paired.sw1_comparison)
    paired['outcome']=np.where(paired.delta>threshold,'harmful',np.where(paired.delta < -threshold,'beneficial','neutral'))
    return paired

def cluster_interval(frame,replicates=2000,seed=81123):
    """Equal-weight SCM means; stratify by mechanism family, retain all conditions."""
    independent=frame.groupby(['family','d','seed'],as_index=False).delta.mean()
    if independent.empty:
        return {'mean':None,'low':None,'high':None,'independent_scms':0}
    rng=np.random.default_rng(seed)
    strata=[part.delta.to_numpy() for _,part in independent.groupby(['family','d'])]
    draws=[]
    for _ in range(replicates):
        draws.append(np.concatenate([rng.choice(v,len(v),replace=True) for v in strata]).mean())
    return {'mean':float(independent.delta.mean()),'low':float(np.quantile(draws,.025)),
            'high':float(np.quantile(draws,.975)),'independent_scms':len(independent)}
