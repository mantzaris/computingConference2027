"""One sealed final evaluation, block uncertainty and recorded-arm decisions."""
import csv
import itertools
import time
import numpy as np
import pandas as pd
import torch
from sem_update.metrics import wasserstein
from app_runtime import *
from app_data import *
from app_methods import install, load_model, sample_joint

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader();writer.writerows(rows)

def block_means(x,arms,repeats,seed,block_size=10):
    """Resample contiguous experimental blocks, retaining assigned treatment."""
    rng=np.random.default_rng(seed);blocks=np.arange(len(x))//block_size;k=blocks.max()+1
    counts=np.array([[np.sum((blocks==b)&(arms==a)) for a in (0,1)] for b in range(k)])
    sums=np.array([[x[(blocks==b)&(arms==a)].sum(0) for a in (0,1)] for b in range(k)])
    result=[]
    for _ in range(repeats):
        for attempt in range(100):
            ix=rng.integers(k,size=k);n=counts[ix].sum(0)
            if n.min()>0:break
        else:raise ValueError('Insufficient treatment support for block uncertainty')
        result.append(sums[ix].sum(0)/n[:,None])
    return np.array(result)

def score_effect(predicted,observed,scales,indices=OUTCOMES):
    return float(np.mean(np.abs(predicted[list(indices)]-observed[list(indices)])/scales[list(indices)]))

def weighted_primary(run_scores,design):
    return float(np.mean([np.mean([run_scores[r['run']] for r in design if r['target']==target and r['panel']=='primary'])
                          for target in VARS[:3]]))

def choose_arm(means,threshold):
    pressure=means[:,7];current=means[:,5:7].sum(1);eligible=np.where(pressure>=threshold)[0]
    if len(eligible):return int(min(eligible,key=lambda k:(current[k],k)))
    return int(min(range(2),key=lambda k:(-pressure[k],current[k],k)))

def evaluate():
    setup();cuda();install();protocol=read_json(RESULTS/'protocol.json');sealed=read_json(RESULTS/'frozen_selections.json')
    if protocol['scientific_hash']!=source_hash() or sealed['protocol_sha256']!=file_hash(RESULTS/'protocol.json'):
        raise RuntimeError('Protocol/source changed before final evaluation')
    for p,h in sealed['records'].items():
        if file_hash(ROOT/p)!=h:raise RuntimeError('Selected models changed')
    if file_hash(ROOT/'sealed_checkpoints.json')!=sealed['checkpoints_manifest_sha256']:raise RuntimeError('Checkpoint manifest changed')
    for p,h in read_json(ROOT/'sealed_checkpoints.json').items():
        if file_hash(ROOT/p)!=h:raise RuntimeError('Checkpoint changed')
    cfg=protocol['config'];design=[r for r in protocol['final_design'] if r['panel']!='immediate_acoustic']
    main=read_json(ROOT/'runs/main/frozen.json');main_manifest=read_json(ROOT/main['data_folder']/'manifest.json')
    scales=np.array(main_manifest['standardization']['std']);B=cfg['bootstrap_replicates']
    with job('final-evaluation',{'protocol':file_hash(RESULTS/'protocol.json'),'selections':file_hash(RESULTS/'frozen_selections.json')}) as active:
        if not active:return
        boundary=ROOT/'final_access.json'
        if not boundary.exists():atomic_json(boundary,{'opened_unix':time.time(),'sealed_sha256':file_hash(RESULTS/'frozen_selections.json')})
        empirical={};observed_rows=[]
        for ri,r in enumerate(design):
            path=raw('wt_validate_v1',r['run'])
            if file_hash(path)!=r['sha256']:raise ValueError('Final recording changed')
            frame=pd.read_csv(path);check_configuration(frame)
            x=calibrated(frame);arms=frame.flag.to_numpy(int)
            means=np.stack([x[arms==a].mean(0) for a in (0,1)])
            boot=block_means(x,arms,B,cfg['bootstrap_seed']+ri)
            empirical[r['run']]={'x':x,'arms':arms,'means':means,'bootstrap_means':boot}
            for j in range(3,len(VARS)):
                delta=means[1,j]-means[0,j];draws=boot[:,1,j]-boot[:,0,j];ci=np.quantile(draws,[.025,.975])
                observed_rows.append({'run':r['run'],'target':r['target'],'panel':r['panel'],'outcome':VARS[j],'unit':UNITS[j],
                    'low_mean':means[0,j],'high_mean':means[1,j],'effect':delta,'ci_low':ci[0],'ci_high':ci[1],
                    'n_low':r['arm_n'][0],'n_high':r['arm_n'][1],'block_rows':10})
        np.savez_compressed(ROOT/'generated_samples/observed_bootstraps.npz',**{r:v['bootstrap_means'] for r,v in empirical.items()})
        metrics=[];effects=[];predictions={};decisions=[];graph_records={};cost_records=[]
        for record_path in sealed['records']:
            record=read_json(ROOT/record_path);folder=ROOT/record['data_folder'];data=load(folder,('fit','early'))
            m=data.manifest;mu=np.array(m['standardization']['mean']);sd=np.array(m['standardization']['std'])
            prefix=('semantic_' if record['semantic'] else f'refit{record["replicate"]}_' if record['replicate'] else '')
            for method,row in record['methods'].items():
                keep=(method in ('M0','M1','M2','M3','M4','M5','fixed','random') if not prefix else
                      method in ('M1','M3','M4','M5','fixed','random') if record['semantic'] else method in ('M1','M3','M4','M5','fixed'))
                if not keep and not (not prefix and method.startswith('checkpoint_')):continue
                label=prefix+method;spec=row['selected'];key=digest({'data':data.key,'spec':spec,'samples':cfg['evaluation_samples']})
                cache=ROOT/'generated_samples'/('prediction-'+key+'.npz');timing=cache.with_suffix('.json')
                if cache.exists():arrays=dict(np.load(cache));seconds=read_json(timing)['seconds'];peak=read_json(timing)['peak_vram_bytes']
                else:
                    torch.cuda.reset_peak_memory_stats();model=load_model(spec,data,cfg);arrays={};start=time.monotonic()
                    for ri,r in enumerate(design):
                        for arm in (0,1):
                            physical={**r['nuisance'],r['target']:r['high'] if arm else r['low']}
                            assignments={str(j):{'kind':'fixed','value':(physical[VARS[j]]-mu[j])/sd[j]} for j in ACTUATORS}
                            z=sample_joint(model,assignments,cfg['evaluation_samples'],44500+ri)
                            assert z.is_cuda and torch.isfinite(z).all()
                            for j in ACTUATORS:
                                if not torch.allclose(z[:,j],torch.full_like(z[:,j],assignments[str(j)]['value'])):raise AssertionError('Intervention replacement failed')
                            arrays[r['run']+'_'+str(arm)]=(z.cpu().numpy()*sd+mu).astype('float64')
                    torch.cuda.synchronize();seconds=time.monotonic()-start;peak=torch.cuda.max_memory_allocated()
                    np.savez_compressed(cache,**arrays);atomic_json(timing,{'seconds':seconds,'peak_vram_bytes':peak,'sha256':file_hash(cache),
                        'data':data.key,'spec':spec,'samples_per_arm':cfg['evaluation_samples']})
                    del model
                graph_records[label]={'initial':record['initial'],'selected':spec,'before_audit':row.get('before_audit'),
                    'retained_initial':row.get('retained_initial'),'audit_pass':row.get('audit_pass'),'bank_hash':row.get('bank_hash',record['bank_hashes'].get('diagnostic'))}
                training=row.get('cost',{}).get('fit_seconds',row.get('stage_seconds',row['logical_seconds']))
                cost_records.append({'method':label,'logical_seconds':row['logical_seconds'],'training_seconds':training,
                    'discovery_seconds':row.get('discovery',{}).get('seconds',0),'selection_seconds':row.get('selection_seconds',0),
                    'fitting_updates':row['fitting_updates'],'candidate_count':row.get('candidate_count',1),
                    'prediction_seconds':seconds,'samples_per_arm':cfg['evaluation_samples'],'peak_vram_bytes':max(peak,row.get('stage_peak_bytes',0),row.get('discovery',{}).get('peak_vram_bytes',0)),
                    'retained_initial':row.get('retained_initial'),'audit_pass':row.get('audit_pass'),'prediction_artifact':str(cache.relative_to(ROOT)),
                    'discovery_status':row.get('discovery',{}).get('status'),'strict_convergence':row.get('discovery',{}).get('converged')})
                predictions[label]={}
                for ri,r in enumerate(design):
                    ys=[arrays[r['run']+'_'+str(a)] for a in (0,1)];means=np.stack([z.mean(0) for z in ys]);delta=means[1]-means[0]
                    emp=empirical[r['run']];observed=emp['means'][1]-emp['means'][0]
                    predictions[label][r['run']]=delta
                    sw=[];coverage=[];width=[]
                    for a,z in enumerate(ys):
                        truth=emp['x'][emp['arms']==a];zt=torch.tensor((z[:,3:]-mu[3:])/sd[3:],device='cuda',dtype=torch.float32)
                        xt=torch.tensor((truth[:,3:]-mu[3:])/sd[3:],device='cuda',dtype=torch.float32)
                        sw.append(float(wasserstein(zt,xt,cfg['evaluation_projections'],44561+ri)))
                        lo,hi=np.quantile(z,[.05,.95],axis=0)
                        coverage.append(float(((truth[:,list(OUTCOMES)]>=lo[list(OUTCOMES)])&(truth[:,list(OUTCOMES)]<=hi[list(OUTCOMES)])).mean()))
                        width.append(float(((hi-lo)/scales)[list(OUTCOMES)].mean()))
                    metrics.append({'method':label,'run':r['run'],'target':r['target'],'panel':r['panel'],
                        'effect_error':score_effect(delta,observed,scales),'joint_sw1':np.mean(sw),'worst_arm_sw1':max(sw),
                        'coverage90':np.mean(coverage),'width90_standardized':np.mean(width)})
                    if not prefix.startswith('refit') and not method.startswith('checkpoint_'):
                        for j in OUTCOMES:
                            batches=np.array([z.reshape(4,-1,len(VARS)).mean(1)[:,j] for z in ys])
                            mc=(batches[1]-batches[0]).std(ddof=1)/2
                            marginal=[]
                            for a,z in enumerate(ys):
                                from scipy.stats import wasserstein_distance
                                marginal.append(wasserstein_distance(emp['x'][emp['arms']==a,j],z[:,j]))
                            effects.append({'method':label,'run':r['run'],'outcome':VARS[j],
                                'pred_low':means[0,j],'pred_high':means[1,j],'pred_effect':delta[j],
                                'observed_effect':observed[j],'absolute_error':abs(delta[j]-observed[j]),'mc_se':mc,
                                'marginal_w1':np.mean(marginal)})
                    if r['panel']=='primary' and not prefix.startswith('refit') and not method.startswith('checkpoint_'):
                        target=protocol['decision']['threshold_pa'];choice=choose_arm(means,target)
                        observed_feasible=np.where(emp['means'][:,7]>=target)[0];current=emp['means'][:,5:7].sum(1)
                        regret=(current[choice]-current[observed_feasible].min()) if choice in observed_feasible else None
                        decisions.append({'method':label,'run':r['run'],'chosen_arm':choice,'threshold_pa':target,
                            'observed_pressure_pa':emp['means'][choice,7],'observed_total_current_a':current[choice],
                            'constraint_violation':bool(emp['means'][choice,7]<target),'measured_feasible_arms':len(observed_feasible),
                            'feasible_current_regret_a':regret,'scope':'recorded binary alternatives; condition means'})
        frame=pd.DataFrame(metrics);primary=[r for r in design if r['panel']=='primary'];summary=[];rng=np.random.default_rng(cfg['bootstrap_seed']+90)
        targets=VARS[:3];draws={t:[] for t in targets}
        for t in targets:
            names=[r['run'] for r in primary if r['target']==t]
            draws[t]=rng.choice(names,size=(B,len(names)),replace=True)
        for label,pred in predictions.items():
            sub=frame[(frame.method==label)&(frame.panel=='primary')]
            errors=dict(zip(sub.run,sub.effect_error));point=weighted_primary(errors,primary);boot=[]
            for b in range(B):
                v=[]
                for t in targets:
                    v.append(np.mean([score_effect(pred[name],empirical[name]['bootstrap_means'][b,1]-empirical[name]['bootstrap_means'][b,0],scales) for name in draws[t][b]]))
                boot.append(np.mean(v))
            ci=np.quantile(boot,[.025,.975]);summary.append({'method':label,'effect_error':point,'ci_low':ci[0],'ci_high':ci[1],
                'joint_sw1':float(sub.joint_sw1.mean()),'worst_run_sw1':float(sub.joint_sw1.max()),
                'coverage90':float(sub.coverage90.mean()),'width90_standardized':float(sub.width90_standardized.mean())})
        reliability=[]
        for method in ('M3','M4','M5','random','semantic_M3','semantic_M4','semantic_M5','semantic_random'):
            if method not in predictions:continue
            ref='semantic_fixed' if method.startswith('semantic') else 'fixed';a=frame[(frame.method==method)&(frame.panel=='primary')].set_index('run')
            b=frame[(frame.method==ref)&(frame.panel=='primary')].set_index('run');delta=a.joint_sw1-b.joint_sw1
            harm=delta>np.maximum(.001,.05*b.joint_sw1)
            reliability.append({'method':method,'harmful_runs':int(harm.sum()),'evaluated_runs':len(a),
                'max_sw_deterioration':float(delta.max()),'mean_harm_severity':float(delta[harm].mean()) if harm.any() else 0,
                'retained_initial':graph_records[method]['retained_initial'],'definition':protocol['harm']})
        contrasts=[]
        for a,b in [('M3','fixed'),('M3','M1'),('M3','M5'),('M5','fixed')]:
            va=frame[(frame.method==a)&(frame.panel=='primary')].set_index('run');vb=frame[(frame.method==b)&(frame.panel=='primary')].set_index('run')
            weights=np.array([1/(3*sum(r['target']==va.loc[name,'target'] for r in primary)) for name in va.index])
            delta=(va.effect_error-vb.effect_error).to_numpy()*weights*len(va);observed=abs(delta.mean())
            p=np.mean([abs(np.mean(delta*np.array(s)))>=observed-1e-14 for s in itertools.product((-1,1),repeat=len(delta))])
            contrasts.append({'contrast':a+'-'+b,'mean_run_difference':float(delta.mean()),'p_raw':float(p),'units':'five acquisition files on one apparatus'})
        running=0
        for rank,i in enumerate(sorted(range(4),key=lambda i:contrasts[i]['p_raw'])):
            running=max(running,min(1,(4-rank)*contrasts[i]['p_raw']));contrasts[i]['p_holm']=running
        # Acoustic results are measured contrasts only: incompatible speaker/OSR
        # settings exclude the microphone from the joint learned model.
        acoustic=[]
        for ri,r in enumerate(protocol['final_design']):
            if r['run'] not in FINAL+['validate_hatch_mic']:continue
            f=pd.read_csv(raw('wt_validate_v1',r['run']));arms=f.flag.to_numpy(int)
            if not np.allclose(f.v_mic,5) or not np.allclose(f.osr_mic,8):raise ValueError('Acoustic calibration changed')
            y=f.mic.to_numpy()[:,None]*5/1023;b=block_means(y,arms,B,44620+ri)
            v=float(y[arms==1].mean()-y[arms==0].mean());ci=np.quantile(b[:,1,0]-b[:,0,0],[.025,.975])
            acoustic.append({'run':r['run'],'target':r['target'],'wait_ms':r['wait_ms'],'effect_signal_volts':v,'ci_low':ci[0],'ci_high':ci[1],
                             'unit':'microphone circuit amplitude V; not dB SPL','generative_prediction':'unavailable: incompatible training measurement configuration'})
        write_csv(ROOT/'reports/all_metrics.csv',metrics);write_csv(ROOT/'reports/all_effects.csv',effects)
        write_csv(ROOT/'reports/all_summary.csv',summary)
        write_csv(RESULTS/'metrics.csv',[r for r in metrics if not r['method'].startswith(('refit','checkpoint'))])
        write_csv(RESULTS/'effects.csv',effects);write_csv(RESULTS/'observed_effects.csv',observed_rows)
        write_csv(RESULTS/'summary.csv',summary);write_csv(RESULTS/'reliability.csv',reliability)
        write_csv(RESULTS/'decisions.csv',decisions);write_csv(RESULTS/'acoustic.csv',acoustic)
        write_csv(RESULTS/'costs.csv',cost_records);write_csv(RESULTS/'contrasts.csv',contrasts)
        atomic_json(ROOT/'reports/graphs_full.json',graph_records)
        atomic_json(RESULTS/'graphs.json',{k:v for k,v in graph_records.items() if not k.startswith('checkpoint')})
        atomic_json(ROOT/'reports/evaluation_manifest.json',{'protocol_sha256':file_hash(RESULTS/'protocol.json'),
            'sealed_sha256':file_hash(RESULTS/'frozen_selections.json'),'prediction_files':{p.name:file_hash(p) for p in (ROOT/'generated_samples').glob('prediction-*.npz')},
            'final_access_sha256':file_hash(boundary),'methods':list(predictions),'observed_primary_rows':sum(r['n'] for r in primary),
            'primary_acquisition_files':len(primary),'apparatuses':1})
        print(json.dumps({'evaluated_method_records':len(predictions),'primary_rows':sum(r['n'] for r in primary),'summary':summary[:8]}),flush=True)
