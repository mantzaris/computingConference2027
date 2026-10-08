"""Isolated final outcomes and truth-based descendant metrics; fitting disabled."""
import csv
import math
from pathlib import Path
import time
import networkx as nx
import numpy as np
import torch
from sem_update.graphs import DAG,structural_metrics
from sem_update.metrics import wasserstein,energy
from sem_update.phase2.models import EmpiricalMarginals,Ensemble,sample,joint_nll
from .runtime import root,RESULTS,job,atomic_json,read_json,digest,file_hash,scientific_hash,freeze_guard,require_cuda
from .data import load,final_environments,seed_for,graph_stats
from .flows import fit_graph
from .objectives import sample_many,distance_mean

def model_from_spec(spec,data,cfg):
    kind=spec['kind']
    if kind=='marginal':return EmpiricalMarginals(data.get('fit')[0].x)
    if kind=='ridge':
        path=root()/spec['path']
        if file_hash(path)!=spec['sha256']:raise ValueError('Frozen ridge changed')
        return torch.load(path,map_location='cuda',weights_only=False)
    if kind=='flow':return fit_graph(data,DAG.from_json(spec['graph']),cfg['train'],False)[0]
    if kind=='ensemble':return Ensemble([fit_graph(data,DAG.from_json(g),cfg['train'],False)[0] for g in spec['components']],spec['weights'])
    raise ValueError(kind)

@torch.no_grad()
def metric(actual,generated,actual_obs,generated_obs,target,truth,projections,seed):
    d=actual.shape[1];keep=[j for j in range(d) if j!=target];x=actual[:,keep].float();y=generated[:,keep].float()
    quant=(torch.arange(512,device=x.device)+.5)/512
    marg=(torch.quantile(x,quant,dim=0)-torch.quantile(y,quant,dim=0)).abs().mean(0)
    descendants=nx.descendants(truth.networkx(),target);di=[k for k,j in enumerate(keep) if j in descendants];nd=[k for k,j in enumerate(keep) if j not in descendants]
    actual_effect=(actual.mean(0)-actual_obs.mean(0))[keep];pred_effect=(generated.mean(0)-generated_obs.mean(0))[keep]
    errors=(actual_effect-pred_effect).square();levels=torch.tensor([.05,.25,.75,.95],device=x.device);q=torch.quantile(y,levels,dim=0)
    result={'sw1':float(wasserstein(x,y,projections,seed)),'marginal_w1':float(marg.mean()),
        'effect_rmse':float(errors.mean().sqrt()),'energy_distance':float(energy(x,y,seed+1))/math.sqrt(len(keep)),
        'energy_score':float(distance_mean(y,x)-.5*distance_mean(y,y))/math.sqrt(len(keep)),
        'descendant_w1':float(marg[di].mean()) if di else None,'nondescendant_w1':float(marg[nd].mean()) if nd else None,
        'descendant_effect_rmse':float(errors[di].mean().sqrt()) if di else None,
        'nondescendant_effect_rmse':float(errors[nd].mean().sqrt()) if nd else None,
        'descendants':len(di),'descendant_fraction':len(di)/len(keep),
        'true_response_rms':float(actual_effect.square().mean().sqrt()),
        'true_descendant_response_rms':float(actual_effect[di].square().mean().sqrt()) if di else None,
        'coverage90':float(((x>=q[0])&(x<=q[3])).float().mean()),'width90':float((q[3]-q[0]).mean()),
        'coverage50':float(((x>=q[1])&(x<=q[2])).float().mean()),'width50':float((q[2]-q[1]).mean())}
    # Vectors stay operational; representative plotting tables are curated later.
    return result,{'actual_mean':actual.mean(0).cpu().tolist(),'predicted_mean':generated.mean(0).cpu().tolist(),
        'actual_effect':actual_effect.cpu().tolist(),'predicted_effect':pred_effect.cpu().tolist(),'marginal_w1':marg.cpu().tolist(),
        'prediction_q05':q[0].cpu().tolist(),'prediction_q95':q[3].cpu().tolist()}

@torch.no_grad()
def predict(spec,data,cfg,folder,groups,truth,projection_sensitivity=False):
    identity={'spec':spec,'data':data.key,'final_seed':data.manifest['seed'],'samples':cfg['evaluation_samples'],
        'projections':cfg['evaluation_projections'],'source':scientific_hash(),'projection_sensitivity':projection_sensitivity}
    key=digest(identity);out=root()/'generated_samples'/key;out.mkdir(parents=True,exist_ok=True)
    with job('prediction-'+key,identity) as active:
        if active:
            torch.cuda.reset_peak_memory_stats();model=model_from_spec(spec,data,cfg);start=time.monotonic()
            allenv=[e for rows in groups.values() for e in rows]
            predictions=sample_many(model,allenv,cfg['evaluation_samples'],seed_for(data.manifest['seed'],'prediction'))
            torch.cuda.synchronize();inference=time.monotonic()-start;metrics_begin=time.monotonic()
            mapping={e.name:y for e,y in zip(allenv,predictions)};obs=groups['obs'][0];generated_obs=mapping[obs.name];rows=[];vectors={}
            for endpoint,envs in groups.items():
                if endpoint=='obs':continue
                for i,e in enumerate(envs):
                    target=e.targets[0];y=mapping[e.name]
                    values,vector=metric(e.x,y,obs.x,generated_obs,target,truth,cfg['evaluation_projections'],seed_for(data.manifest['seed'],'metric',e.name))
                    nll=joint_nll(model,[e]);values['nll']=None if nll is None else float(nll)
                    if projection_sensitivity and endpoint=='T2':
                        keep=[j for j in range(data.d) if j!=target]
                        for count in (64,1024):values['sw1_'+str(count)]=float(wasserstein(e.x[:,keep],y[:,keep],count,seed_for(data.manifest['seed'],'metric',e.name)))
                    rows.append({'endpoint':endpoint,'environment':e.name,'target':target,**values});vectors[e.name]=vector
            torch.cuda.synchronize();metric_seconds=time.monotonic()-metrics_begin
            np.savez_compressed(out/'samples.npz',**{name:y.cpu().numpy() for name,y in mapping.items()})
            value={'identity':identity,'metrics':rows,'vectors':vectors,'inference_seconds':inference,'metric_seconds':metric_seconds,
                'generated_rows':sum(len(y) for y in predictions),'throughput_rows_per_second':sum(len(y) for y in predictions)/inference,
                'peak_vram_bytes':torch.cuda.max_memory_allocated(),'samples_sha256':file_hash(out/'samples.npz'),'key':key}
            atomic_json(out/'metrics.json',value)
    return read_json(out/'metrics.json')

def aggregate(rows):
    names=set().union(*(r.keys() for r in rows))-{'endpoint','environment','target'};value={}
    for k in names:
        vals=[r[k] for r in rows if r.get(k) is not None]
        value[k]=float(np.mean(vals)) if vals else None
    value['worst_sw1']=max(r['sw1'] for r in rows);value['environments']=len(rows)
    value['descendant_environments']=sum(r['descendants']>0 for r in rows)
    return value

def evaluate_records(paths,development=False):
    require_cuda();cached={};summaries=[];total_predictions=set()
    for path in paths:
        record=read_json(path);cfg=record['config'];folder=root()/record['data_folder'];folderkey=str(folder)
        if folderkey not in cached:cached={folderkey:(load(folder,allowed=('fit','early')),final_environments(folder,cfg))}
        data,(groups,truth)=cached[folderkey];task=record['task'];topology=graph_stats(truth)
        actual_folder=root()/'generated_samples'/('actual-'+data.key)
        if not actual_folder.exists():
            actual_folder.mkdir();np.savez_compressed(actual_folder/'samples.npz',**{e.name:e.x.cpu().numpy() for rows in groups.values() for e in rows})
        predictions={}
        for method,row in record['methods'].items():
            predicted=predict(row['selected'],data,cfg,folder,groups,truth,task.get('oracle',False));predictions[method]=predicted;total_predictions.add(predicted['key'])
        baseline={endpoint:aggregate([r for r in predictions['fixed']['metrics'] if r['endpoint']==endpoint])['sw1'] for endpoint in ('T1','T2','T3')}
        for method,row in record['methods'].items():
            predicted=predictions[method];spec=row['selected'];graph=None
            if spec['kind'] in ('flow','ridge'):graph=DAG.from_json(spec['graph'])
            elif spec['kind']=='marginal':graph=DAG(data.d)
            graphmetrics=structural_metrics(graph,truth) if graph else {'shd':None,'precision':None,'recall':None,'f1':None}
            returned_change=structural_metrics(graph,DAG.from_json(record['prior']['graph']))['shd'] if graph else None
            for endpoint in ('T1','T2','T3'):
                value=aggregate([r for r in predicted['metrics'] if r['endpoint']==endpoint])
                repair=method in ('M3','M4','M5','random') or method.startswith('checkpoint_');delta=value['sw1']-baseline[endpoint]
                summaries.append({'scm':task['seed'],'family':task['family'],'profile':task['profile'],'d':task['d'],
                    'budget':data.manifest['budget_per_target'],'sensitivity':task.get('sensitivity','primary'),
                    'corruption':record['prior']['corruption_fraction'],'resource':record['resource'],'method':method,'endpoint':endpoint,
                    **value,**graphmetrics,'initial_shd':record['prior']['initial_metrics']['shd'],
                    'returned_shd_from_initial':returned_change,
                    'delta_fixed':delta,'harmful':int(delta>max(.001,.05*baseline[endpoint])) if repair and endpoint=='T2' else None,
                    'retained':int(row.get('retained_initial',False)) if repair else None,'audit_pass':row.get('audit_pass'),
                    'logical_seconds':row['logical_seconds'],'training_seconds':row.get('training_seconds',0.),
                    'discovery_seconds':row.get('discovery_seconds',0.),'fitting_updates':row.get('fitting_updates',0),
                    'discovery_updates':row.get('discovery_updates',0),'input_weighted_updates':row.get('input_weighted_updates',row.get('cost',{}).get('input_weighted_updates',0)),
                    'search_gpu_seconds':row.get('prefix_gpu_job_seconds',row['logical_seconds']-row.get('selection_seconds',0.)),
                    'selection_seconds':row.get('selection_seconds',0.),
                    'parent_sets':row.get('parent_sets',0),'candidates':row.get('candidate_count',0),
                    'accepted':row.get('accepted_changes',0),'inference_seconds':predicted['inference_seconds'],
                    'latency_per_environment_seconds':predicted['inference_seconds']/(3*len(data.manifest['seen_targets'])+1),
                    'metric_seconds':predicted['metric_seconds'],'throughput':predicted['throughput_rows_per_second'],
                    'peak_vram_bytes':max(row.get('peak_vram_bytes',0),predicted['peak_vram_bytes']),
                    'status':row.get('status','complete'),'h_per_node':row.get('h_per_node'),
                    'visible_targets':len(data.manifest['seen_targets']),'visible_fraction':data.manifest['visible_fraction'],
                    'intervention_rows':data.manifest['non_test_intervention_rows'],
                    'edges':topology['edges'],'depth':topology['depth'],'max_indegree':topology['max_indegree'],
                    'max_outdegree':topology['max_outdegree'],'prediction_key':predicted['key'],
                    'record':str(Path(path).relative_to(root()))})
        if development:
            atomic_json(root()/'runs'/(record['condition']+'-'+record['resource']+'-pilot-metrics.json'),summaries)
        else:write_csv(RESULTS/'metrics.csv',summaries)
        print(f'evaluated {record["condition"]} {record["resource"]}',flush=True)
    return {'records':len(paths),'metric_rows':len(summaries),'unique_predictions':len(total_predictions)}

def write_csv(path,rows):
    if not rows:return
    keys=list(rows[0]);tmp=Path(str(path)+'.tmp')
    with open(tmp,'w') as f:
        writer=csv.DictWriter(f,keys);writer.writeheader()
        for row in rows:writer.writerow({k:(format(v,'.9g') if isinstance(v,float) else v) for k,v in row.items()})
    tmp.replace(path)

def main():
    protocol=freeze_guard();frozen=read_json(RESULTS/'frozen_selections.json')
    if frozen['source_hash']!=scientific_hash() or frozen['protocol_sha256']!=file_hash(RESULTS/'protocol.json'):raise ValueError('Frozen protocol changed')
    for name,sha in frozen['records'].items():
        if file_hash(root()/name)!=sha:raise ValueError('Frozen selected model changed')
    manifest=root()/'frozen_mechanisms.json'
    if file_hash(manifest)!=frozen['mechanism_manifest_sha256']:raise ValueError('Frozen mechanism manifest changed')
    for name,sha in read_json(manifest).items():
        if file_hash(root()/name)!=sha:raise ValueError('Frozen mechanism changed: '+name)
    if not (RESULTS/'final_test_access.json').exists():
        import datetime
        atomic_json(RESULTS/'final_test_access.json',{'frozen_selections_sha256':file_hash(RESULTS/'frozen_selections.json'),
            'first_opened_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mechanisms_verified':len(read_json(manifest))})
    with job('final-evaluation',{'frozen':digest(frozen),'source':scientific_hash()}) as active:
        if active:
            result=evaluate_records([root()/p for p in frozen['records']]);atomic_json(RESULTS/'evaluation.json',result)
