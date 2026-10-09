"""Reproducible stage coordinator; final evaluation requires sealed selections."""
import argparse
import copy
import json
import time
from pathlib import Path
import numpy as np
import torch
from app_runtime import *
from app_data import *
from app_methods import install, initial_graph, fit_graph, timed, run_task, sample_joint

def development():
    from sem_update.phase2.models import ridge_fit,joint_nll
    setup();cuda();install();cfg=read_json(PHASE/'config.json'); folder=prepare(development=True)
    data=load(folder); graph=initial_graph(load(folder,('fit','early')))
    with job('development-pilot',{'source':source_hash(),'config':cfg}) as active:
        if active:
            grid=[]
            for alpha in cfg['ridge_grid']:
                model=ridge_fit(NuisanceView(data),graph,alpha,1e-4)
                grid.append({'alpha':alpha,'early_conditional_nll':float(joint_nll(model,data.get('early')))})
            start=time.monotonic();model,stats=fit_graph(data,graph,cfg['train']);torch.cuda.synchronize()
            fitting=time.monotonic()-start
            start=time.monotonic();z=sample_joint(model,data.get('search')[0].assignments,cfg['evaluation_samples'],44401);torch.cuda.synchronize()
            assert z.is_cuda and torch.isfinite(z).all()
            from sem_update.phase3.objectives import score
            scoring=score(model,data.get('search'),cfg['search'])
            # A static surrogate does not make serially correlated records iid.
            f=pd.read_csv(raw('wt_walks_v1','actuators_random_walk_16'));ids=eligible(f)
            x=calibrated(f);target=float(np.quantile(x[ids,7],.75))
            report={'ridge_grid':grid,'selected_alpha':min(grid,key=lambda r:(r['early_conditional_nll'],r['alpha']))['alpha'],
                'flow_fit_seconds':fitting,'generation_and_score_seconds':time.monotonic()-start,'fitting_updates':sum(s['updates'] for s in stats),
                'peak_vram_bytes':torch.cuda.max_memory_allocated(),'search_score':scoring,'graph':graph.json(),
                'decision_pressure_threshold_pa':target,'development_acquisition':16,'eligible_rows':len(ids),
                'estimated_full_study_seconds':fitting*25*8+2400+1800}
            atomic_json(RESULTS/'pilot.json',report)
    return read_json(RESULTS/'pilot.json')

def freeze():
    path=RESULTS/'protocol.json'
    if path.exists():
        value=read_json(path)
        if value['scientific_hash']!=source_hash():raise RuntimeError('Scientific source changed after freeze')
        return value
    cfg=read_json(PHASE/'config.json');pilot=read_json(RESULTS/'pilot.json')
    cfg['ridge_alpha']=pilot['selected_alpha']
    if not read_json(RESULTS/'correctness.json')['passed']:raise RuntimeError('Correctness suite required')
    llm=read_json(RESULTS/'llm_prior.json')
    folder=prepare();m=read_json(folder/'manifest.json')
    value={'version':1,'config':cfg,'scientific_hash':source_hash(),'created_unix':time.time(),
        'historical_commits':['ad21e60','8c452ac','a17a8f7'],'data_hash':m['dataset_hash'],'partition_hashes':m['partition_hashes'],
        'roles':ROLES,'final_design':final_design(),'primary_outcomes':[VARS[j] for j in OUTCOMES],
        'primary_endpoint':'mean absolute predicted randomized contrast error / fitting SD, equal outcome and actuator weighting; repeated acquisitions averaged within actuator',
        'secondary_endpoint':'joint non-command SW1; marginal error; 90% predictive coverage; worst randomized regime',
        'formulation':'quasi-steady predictive surrogate on slowly changing command windows, not a proven instantaneous physical DAG',
        'command_filter':{'window_seconds':10,'max_fan_span':.1,'max_hatch_span_degrees':5,'minimum_spacing_seconds':3,'startup_seconds':15},
        'uncertainty':'2,000 paired hierarchical resamples: acquisitions within target, contiguous 10-row blocks within acquisition; conditional on one apparatus, fitted model and fixed Monte Carlo streams',
        'formal_contrasts':['M3-fixed','M3-M1','M3-M5','M5-fixed'],'multiplicity':'Holm across four paired acquisition sign-flip tests; no general population claim',
        'harm':'joint SW1 > fixed + max(0.001, 0.05*fixed); per-run descriptive, not primary effect endpoint',
        'decision':{'outcome':'pressure_upwind minus pressure_ambient','threshold_pa':pilot['decision_pressure_threshold_pa'],
            'objective':'minimize sum of calibrated fan currents among the two recorded arms satisfying predicted mean pressure; if none, maximize pressure, then minimize current, then low arm',
            'scope':'five primary acquisitions only; no unrecorded operating point; measured feasible-set regret only'},
        'figure_rule':'full 11-node main M3 graph; M5 components separate; responses current_in,current_out,upwind,downwind; mismatch example largest absolute M3 primary effect error with lexical ties',
        'llm_graph':llm['graph'],'llm_sha256':file_hash(RESULTS/'llm_prior.json'),
        'fit_refits':list(range(1,cfg['grouped_refits']+1)),'dependency_lock_sha256':file_hash(PROJECT/'requirements.lock'),
        'test_outcomes_opened':False}
    atomic_json(path,value);atomic_json(RESULTS/'split_manifest.json',{'data_hash':m['dataset_hash'],'roles':ROLES,
        'retained_rows_by_role':m['retained_rows_by_role'],'non_test_intervention_rows':m['non_test_intervention_rows'],
        'preprocessing_fit_rows':m['preprocessing_fit_rows'],'partition_hashes':m['partition_hashes'],
        'full_manifest_artifact':str((folder/'manifest.json').relative_to(ROOT)), 'full_manifest_sha256':file_hash(folder/'manifest.json'),
        'final_acquisitions':value['final_design'],'development':{'random_walk_16':10000,'mix_fast_1_prefix':2000,'mix_slow_2_prefix':2000}})
    return value

def run():
    protocol=freeze();path=RESULTS/'frozen_selections.json'
    if path.exists():return read_json(path)
    cfg=protocol['config']; records={}
    tasks=[(0,None)]+[(i,None) for i in protocol['fit_refits']]
    if protocol['llm_graph'] is not None: tasks.append((0,protocol['llm_graph']))
    for replicate,semantic in tasks:
        name='main'+('-semantic' if semantic is not None else '') if replicate==0 else f'group-refit-{replicate}'
        with job('task-'+name,{'protocol':file_hash(RESULTS/'protocol.json'),'name':name}) as active:
            if active: run_task(cfg,replicate,semantic)
        file=ROOT/'runs'/name/'frozen.json';records[str(file.relative_to(ROOT))]=file_hash(file)
        print(json.dumps({'completed':name,'phase4_gpu_hours':snapshot()['phase4_gpu_seconds']/3600}),flush=True)
    checkpoints={str(p.relative_to(ROOT)):file_hash(p) for p in (ROOT/'checkpoints').glob('*.pt') if not p.name.endswith('.partial.pt')}
    atomic_json(ROOT/'sealed_checkpoints.json',checkpoints)
    value={'protocol_sha256':file_hash(RESULTS/'protocol.json'),'scientific_hash':source_hash(),'records':records,
        'checkpoints_manifest_sha256':file_hash(ROOT/'sealed_checkpoints.json'),'sealed_unix':time.time(),'test_outcomes_opened':False}
    atomic_json(path,value);return value

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['doctor','development','llm','test','freeze','run','evaluate','status'])
    args=parser.parse_args();setup()
    if args.command=='doctor':print(json.dumps(doctor()))
    elif args.command=='development':print(json.dumps(development()))
    elif args.command=='llm':
        from app_llm import generate
        print(json.dumps(generate()))
    elif args.command=='test':
        import pytest
        cuda()
        with job('correctness-'+source_hash()[:12],{'source':source_hash()}) as active:
            if active:
                code=pytest.main(['-q','--basetemp='+str(ROOT/'test_temp'),str(PHASE/'tests'),'tests','phase2/tests/test_methods.py','phase3/tests/test_scaling.py'])
                atomic_json(RESULTS/'correctness.json',{'passed':code==0,'exit_code':int(code),'source_hash':source_hash()})
                if code:raise RuntimeError('Correctness failed')
    elif args.command=='freeze':print(json.dumps(freeze()))
    elif args.command=='run':run()
    elif args.command=='evaluate':
        # The frozen evaluator completed/wrote all outputs before its final
        # json.dumps log exposed a missing module import. Inject only that
        # standard-library logging dependency; preserve the frozen source,
        # selections, cached predictions and failed-attempt record unchanged.
        import app_evaluate
        app_evaluate.json=json
        app_evaluate.evaluate()
    else:print(json.dumps(snapshot(),indent=2))

if __name__=='__main__':main()
