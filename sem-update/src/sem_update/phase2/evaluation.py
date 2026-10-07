"""Frozen final prediction; no graph selection, mechanism training or tuning."""
import math
import time
import numpy as np
import pandas as pd
import torch
from sem_update.graphs import DAG,structural_metrics
from sem_update.flows import GenerativeSCM
from sem_update.metrics import distribution_metrics
from .runtime import root,RESULTS,atomic_json,read_json,digest,file_hash,job,freeze_guard,scientific_hash
from .data import load,final_environments
from .bank import fit_graph
from .models import EmpiricalMarginals,RidgeMechanism,Ensemble,sample,joint_nll

def model_from_spec(spec,data,cfg):
    kind=spec['kind']
    if kind=='flow':return fit_graph(data,DAG.from_json(spec['graph']),cfg['train'],False)[0]
    if kind=='ensemble':
        models=[fit_graph(data,DAG.from_json(g),cfg['train'],False)[0] for g in spec['components']]
        return Ensemble(models,spec['weights'])
    if kind=='marginal':
        state=torch.load(root()/spec['path'],map_location='cuda',weights_only=True)
        return EmpiricalMarginals(state['sorted_values'])
    if kind=='ridge':
        graph=DAG.from_json(spec['graph'])
        mechanisms=[RidgeMechanism(graph.parents(j),torch.zeros((),device='cuda'),
            torch.zeros(len(graph.parents(j)),device='cuda'),torch.ones((),device='cuda')) for j in range(graph.d)]
        model=GenerativeSCM(graph,mechanisms)
        model.load_state_dict(torch.load(root()/spec['path'],map_location='cuda',weights_only=True));return model
    raise ValueError('Unknown frozen model kind')

@torch.no_grad()
def metrics(model,groups,seed,cfg,sample_path):
    arrays={};rows=[];sample_seconds=0.;metric_seconds=0.
    for endpoint,envs in groups.items():
        for i,e in enumerate(envs):
            s=seed+i*31+sum(map(ord,endpoint));torch.cuda.synchronize();start=time.monotonic()
            y=sample(model,e.assignments,cfg['evaluation_samples'],s,str(e.x.device))
            torch.cuda.synchronize();elapsed=time.monotonic()-start;sample_seconds+=elapsed
            keep=[j for j in range(e.x.shape[1]) if j not in e.targets]
            start=time.monotonic();observed=e.x[:,keep];predicted=y[:,keep]
            m=distribution_metrics(observed,predicted,cfg['evaluation_projections'],seed+i*31)
            m['energy_score']=(torch.cdist(predicted,observed).mean()-.5*torch.cdist(predicted,predicted).mean()).item()/math.sqrt(len(keep))
            nll=joint_nll(model,[e]);m['nll']=None if nll is None else nll.item()
            torch.cuda.synchronize();metric_seconds+=time.monotonic()-start
            rows.append({**m,'environment':e.name,'endpoint':endpoint,'actual_rows':len(e.x),
                'generated_rows':len(y),'non_target_nodes':keep,'blocks':len(e.blocks),
                'outcome_means_actual':observed.mean(0).tolist(),'outcome_means_generated':predicted.mean(0).tolist(),
                'prediction_seconds':elapsed,
                'predictive_q05':torch.quantile(y,.05,dim=0).tolist(),
                'predictive_q50':torch.quantile(y,.5,dim=0).tolist(),
                'predictive_q95':torch.quantile(y,.95,dim=0).tolist(),
                'all_outcome_means_actual':e.x.mean(0).tolist(),'all_outcome_means_generated':y.mean(0).tolist()})
            arrays[e.name]=y.cpu().numpy()
    actual_ref=groups['observational'][0].x.mean(0).cpu().numpy()
    generated_ref=arrays[groups['observational'][0].name].mean(0)
    for row in rows:
        keep=row['non_target_nodes'];actual=np.array(row['outcome_means_actual'])-actual_ref[keep]
        predicted=np.array(row['outcome_means_generated'])-generated_ref[keep]
        row['mean_effect_rmse']=float(np.sqrt(np.mean((actual-predicted)**2)))
    endpoints={}
    for endpoint in groups:
        values=[r for r in rows if r['endpoint']==endpoint]
        keys=['sw1','energy','energy_score','mean_rmse','variance_rmse','coverage_50','coverage_90',
              'width_50','width_90','mean_effect_rmse','nll']
        endpoints[endpoint]={k:None if values[0][k] is None else float(np.mean([r[k] for r in values])) for k in keys}
        endpoints[endpoint].update(worst_regime_sw1=max(r['sw1'] for r in values),environment_count=len(values))
    np.savez_compressed(sample_path,**arrays)
    return {'endpoints':endpoints,'environments':rows,'prediction_seconds':sample_seconds,'metric_seconds':metric_seconds,
            'sample_sha256':file_hash(sample_path),'generated_samples_per_environment':cfg['evaluation_samples']}

def evaluate_tasks(tasks,cfg,development=False):
    rows=[];environments=[];previous=None;data=None;groups=None
    for task in tasks:
        if task['data_id']!=previous:
            folder=root()/'data/processed'/task['data_id'];data=load(folder,allowed=('fit','early'))
            if data.key!=task['data_hash']:raise RuntimeError('Frozen dataset changed')
            if file_hash(folder/'manifest.json')!=task.get('manifest_sha256',file_hash(folder/'manifest.json')):
                raise RuntimeError('Frozen full split manifest changed')
            with job('final-data-'+task['data_id']+'-'+str(time.time_ns()),{'data':data.key,'development':development}) as active:
                groups=final_environments(folder)
            non_test={rid for es in data.manifest['splits'].values() for e in es for rid in e['row_ids']}
            if any(non_test&set(e.row_ids) for es in groups.values() for e in es):raise RuntimeError('Final/non-test overlap')
            truth=None if task['study']=='real' else DAG.from_json(read_json(folder/'truth.json')['graph'])
            previous=task['data_id']
        for name,method in task['methods'].items():
            for stage in ('selected','before_audit'):
                if stage=='before_audit' and (name in ('M0','M1','M2','fixed') or name.startswith('checkpoint_')):continue
                spec=method[stage]
                key=digest({'data':data.key,'spec':spec,'n':cfg['evaluation_samples'],'p':cfg['evaluation_projections'],'version':2})
                path=root()/'runs/evaluation'/(key+'.json');sp=root()/'generated_samples'/(key+'.npz')
                with job('prediction-'+key,{'key':key,'development':development}) as active:
                    if active:
                        torch.cuda.reset_peak_memory_stats();start=time.monotonic()
                        model=model_from_spec(spec,data,cfg)
                        result=metrics(model,groups,task['seed']+170011,cfg,sp)
                        result.update(peak_vram_bytes=torch.cuda.max_memory_allocated(),actual_seconds=time.monotonic()-start)
                        atomic_json(path,result);del model
                result=read_json(path)
                base={k:task[k] for k in ('task_id','study','d','family','seed','budget','data_id','corruption','metadata_variant','non_test_intervention_rows')}
                base.update(method=name,stage=stage,model_hash=digest(spec),model_kind=spec['kind'],
                    fitting_updates=method['cost']['fitting_updates'],flow_fit_seconds=method['cost']['fit_seconds'],
                    discovery_seconds=method.get('discovery_seconds',0.),discovery_updates=method.get('discovery_updates',0),
                    discovery_converged=method.get('discovery_converged'),projected_edges=len(method.get('projection_removed_edges',[])),
                    logical_seconds=method['logical_seconds'],selection_seconds=method['selection_seconds'],
                    actual_incremental_seconds=method.get('actual_incremental_seconds'),
                    prediction_seconds=result['prediction_seconds'],metric_seconds=result['metric_seconds'],
                    peak_vram_bytes=max(method['peak_vram_bytes'],result['peak_vram_bytes']),
                    audit_pass=method['audit_pass'],retained_initial=(None if method['retained_initial'] is None else digest(spec)==digest(method['initial'])),
                    candidate_count=method['candidate_count'],evaluation_artifact=str(path.relative_to(root())),
                    evaluation_sha256=file_hash(path),sample_sha256=result['sample_sha256'],
                    checkpoint_axis=method.get('checkpoint_axis'),checkpoint_limit=method.get('checkpoint_limit'))
                if truth is not None and spec['kind']!='ensemble':
                    graph=DAG(data.d) if spec['kind']=='marginal' else DAG.from_json(spec['graph'])
                    base.update(structural_metrics(graph,truth))
                for endpoint,values in result['endpoints'].items():
                    if stage=='before_audit' and endpoint not in ('T2','T2_exploratory'):continue
                    if name.startswith('checkpoint_') and endpoint!='T2':continue
                    rows.append({**base,'endpoint':endpoint,**values})
                if stage=='selected' and not name.startswith('checkpoint_'):
                    environments.extend([{**base,**v} for v in result['environments']])
        print(task['task_id']+' evaluated',flush=True)
    out=root()/'runs/development' if development else RESULTS
    out.mkdir(parents=True,exist_ok=True)
    # Full environment records remain artifacts; the compact mean/quantile
    # table is exported later only for selected response illustrations.
    if development:
        identity=digest([r['task_id'] for r in tasks])[:16]
        pd.DataFrame(rows).to_csv(out/(identity+'-metrics.csv'),index=False,float_format='%.9g')
        atomic_json(out/(identity+'-environments.json'),environments)
    else:
        pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False,float_format='%.9g')
        atomic_json(root()/'runs/final_environments.json',environments)
    return rows

def evaluate():
    protocol=freeze_guard();frozen=read_json(RESULTS/'frozen_selections.json')
    path=RESULTS/'selected_models.json'
    if file_hash(path)!=frozen['selected_models_sha256'] or frozen['scientific_hash']!=scientific_hash():
        raise RuntimeError('Frozen models or source changed')
    mp=RESULTS/'mechanism_manifest.csv';sp=RESULTS/'simple_model_manifest.json'
    if file_hash(mp)!=frozen['mechanism_manifest_sha256'] or file_hash(sp)!=frozen['simple_model_manifest_sha256']:
        raise RuntimeError('Frozen parameter manifest changed')
    for row in pd.read_csv(mp).itertuples():
        checkpoint=root()/'checkpoints'/row.cache_key[:2]/(row.cache_key+'.pt')
        if file_hash(checkpoint)!=row.checkpoint_sha256:raise RuntimeError('Frozen flow weights changed')
    for checkpoint,sha in read_json(sp).items():
        if file_hash(root()/checkpoint)!=sha:raise RuntimeError('Frozen baseline parameters changed')
    access={'frozen_selection_hash':digest(frozen),'protocol_hash':protocol['protocol_hash'],
            'purpose':'one prespecified final evaluation; no post-test tuning'}
    ap=RESULTS/'final_test_access.json'
    if ap.exists() and read_json(ap)!=access:raise RuntimeError('Final outcomes exposed under another selection')
    atomic_json(ap,access)
    return evaluate_tasks(read_json(path)['tasks'],protocol['config'])
