"""Resumable phase-three pipeline. Final evaluation is gated by frozen selections."""
import argparse
import copy
import datetime
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from sem_update.graphs import DAG,structural_metrics
from sem_update.training import atomic_torch
from sem_update.phase2.models import EmpiricalMarginals,ridge_fit
from .runtime import PROJECT,PHASE,RESULTS,root,setup,job,doctor,require_cuda,atomic_json,read_json,digest,file_hash,scientific_hash,snapshot,freeze_guard
from .data import prepare,load,System,graph_stats,seed_for
from .graphs import corrupt
from .flows import fit_graph
from .bank import build,cost,subbank,prefix_keys
from .selection import choose,graph_spec
from .discovery import discover

def config_for(config,task):
    cfg=copy.deepcopy(config);d=task['d'];cap=8 if task['profile']=='dense' else 6 if task['profile']=='hub' else 3
    cfg['search'].update(max_indegree=cap,candidate_budget=cfg['adjusted_candidates'][str(d)])
    cfg['search'].setdefault('seconds',1800)
    cfg['search']['update_limit']=(d+2*(cfg['search']['candidate_budget']-1))*cfg['train']['steps']
    cfg['dcdi']['max_indegree']=cap;cfg['dcdi']['seed']=seed_for(task['seed'],'discovery')
    cfg['search']['seed']=seed_for(task['seed'],'search')
    if 'checkpoint_limits' in cfg:cfg['checkpoints']=cfg['checkpoint_limits'][str(d)]
    return cfg

def timed(name,identity,function):
    path=root()/'runs'/(name+'.json')
    with job(name,identity) as active:
        if active:
            torch.cuda.reset_peak_memory_stats();start=time.monotonic();value=function();torch.cuda.synchronize()
            value['stage_seconds']=time.monotonic()-start;value['stage_peak_bytes']=torch.cuda.max_memory_allocated()
            atomic_json(path,value)
    return read_json(path)

def task_run(task,config):
    identity={'task':task,'config':config,'source':scientific_hash()}
    name='task-'+digest(identity)[:24];path=root()/'runs'/(name+'-records.json')
    with job(name,identity) as active:
        if active:atomic_json(path,{'records':_task_run(task,config)})
    return read_json(path)['records']

def _task_run(task,config):
    require_cuda();cfg=config_for(config,task);tag=f"{task['profile']}-{task['family']}-d{task['d']}-s{task['seed']}-B{task.get('budget',cfg['budget_per_target'])}"
    identity={'task':task,'config':cfg,'source':scientific_hash()}
    prepared=timed(tag+'-prepare',identity,lambda:{'folder':str(prepare(task,cfg).relative_to(root()))})
    folder=root()/prepared['folder'];m=read_json(folder/'manifest.json');ident=m['id']
    view=load(folder,allowed=('fit','early','search'));limited=load(folder,allowed=('fit','early'))
    # DCDI receives no true graph, hidden order, or initial corruption.
    discovery=timed(tag+'-discovery',identity,lambda:discover(limited,cfg['dcdi']))
    def refit():
        model,stats=fit_graph(limited,DAG.from_json(discovery['graph']),cfg['train'])
        return {'spec':graph_spec(model.graph.json()),'fits':stats,'cost':cost({'x':{'fits':stats}})}
    refitted=timed(tag+'-dcdi-refit',identity,refit)
    common={'M0':{'selected':{'kind':'marginal'},'logical_seconds':0.,'training_seconds':0.,'fitting_updates':0,'status':'complete'},
        'M2':{'selected':refitted['spec'],'logical_seconds':discovery['seconds']+refitted['cost']['fit_seconds'],
            'training_seconds':refitted['cost']['fit_seconds'],'discovery_seconds':discovery['seconds'],
            'fitting_updates':refitted['cost']['fitting_updates'],'discovery_updates':discovery['optimization_steps'],
            'parent_sets':refitted['cost']['parent_sets'],'peak_vram_bytes':max(discovery['peak_vram_bytes'],refitted['stage_peak_bytes']),
            'status':discovery['status'],'h_per_node':discovery['h_per_node'],'legacy_converged':discovery['legacy_converged'],
            'discovery_stop_reason':discovery.get('stop_reason'),'input_weighted_updates':refitted['cost']['input_weighted_updates'],
            'projection_removed':len(discovery['projection_removed_edges'])}}
    def fit_marginal():
        model=EmpiricalMarginals(limited.get('fit')[0].x);return {'sorted_shape':list(model.sorted_values.shape)}
    marginal=timed(tag+'-marginal',identity,fit_marginal)
    common['M0'].update(logical_seconds=marginal['stage_seconds'],training_seconds=marginal['stage_seconds'],peak_vram_bytes=marginal['stage_peak_bytes'])
    if task.get('oracle'):
        # Explicit oracle exception: it is fitted separately and never enters a bank.
        truth=DAG.from_json(read_json(folder/'truth.json')['graph'])
        def fit_oracle():
            model,stats=fit_graph(limited,truth,cfg['train'])
            return {'selected':graph_spec(truth.json()),'cost':cost({'oracle':{'fits':stats}}),'fits':stats}
        oracle=timed(tag+'-oracle',identity,fit_oracle)
        common['oracle']={**oracle,'logical_seconds':oracle['cost']['fit_seconds'],'training_seconds':oracle['cost']['fit_seconds'],
            'fitting_updates':oracle['cost']['fitting_updates'],'parent_sets':oracle['cost']['parent_sets'],
            'peak_vram_bytes':oracle['stage_peak_bytes'],'status':'complete'}
    output=[]
    for corruption in task.get('corruptions',cfg['corruptions']):
        condition=f'{tag}-c{corruption:g}';cp=root()/'runs'/condition;cp.mkdir(exist_ok=True)
        prior_path=cp/'prior.json'
        if not prior_path.exists():
            truth=DAG.from_json(read_json(folder/'truth.json')['graph'])
            initial,edits=corrupt(truth,corruption,task['seed']+37+round(1000*corruption),cfg['search']['max_indegree'])
            atomic_json(prior_path,{'graph':initial.json(),'edit_history':edits,'initial_metrics':structural_metrics(initial,truth),
                'topology':graph_stats(initial),'corruption_fraction':corruption})
        prior=read_json(prior_path);initial=DAG.from_json(prior['graph'])
        def fit_linear():
            model=ridge_fit(limited,initial,cfg['ridge_alpha'],cfg['ridge_variance_floor'])
            path=cp/'ridge.pt';atomic_torch(path,model)
            return {'selected':{'kind':'ridge','graph':initial.json(),'path':str(path.relative_to(root())),'sha256':file_hash(path)}}
        ridge=timed(condition+'-ridge',identity,fit_linear)
        banks={}
        for policy in ('diagnostic','random'):
            name=condition+'-'+policy
            timed(name,identity,lambda policy=policy,name=name:build(view,[initial],name,cfg,policy))
            # Runtime wrappers do not form part of immutable scientific bank hashes.
            banks[policy]=read_json(root()/'runs'/name/'bank.json')
        records={}
        for resource in ('fixed','adjusted'):
            methods=copy.deepcopy(common)
            methods['M1']={**ridge,'logical_seconds':ridge['stage_seconds'],'training_seconds':ridge['stage_seconds'],
                'fitting_updates':0,'peak_vram_bytes':ridge['stage_peak_bytes'],'status':'complete'}
            for policy,bank in banks.items():
                if resource=='fixed':
                    keys=[k for k,c in bank['candidates'].items() if c['ordinal']<=bank['fixed_count']]
                    selected_bank=subbank(bank,keys)
                else:selected_bank=bank
                name=condition+'-'+policy+'-'+resource
                selection=timed(name+'-select',identity,lambda bank=selected_bank,name=name:choose(bank,load(folder),cfg,name,task.get('development',False),True))
                for name,row in selection['methods'].items():
                    if name in ('rho0','tau0','uniform'):continue
                    prefix=set(k for k,c in selected_bank['candidates'].items() if c['ordinal']<=row['candidate_count'])
                    methods[name]={**row,'training_seconds':row['cost']['fit_seconds'],
                        'fitting_updates':row['cost']['fitting_updates'],'parent_sets':row['cost']['parent_sets'],
                        'input_weighted_updates':row['cost']['input_weighted_updates'],
                        'peak_vram_bytes':max(selected_bank['peak_vram_bytes'],selection['stage_peak_bytes']),
                        'status':'valid_capped_prediction' if bank.get('resource_capped') else 'complete',
                        'accepted_changes':sum(e['accepted'] for e in selected_bank['edits'] if all(k in prefix for k in e['evaluated'])),
                        'bank_hash':selected_bank['bank_hash']}
                if policy=='diagnostic':
                    initial_stats=bank['candidates'][bank['initial']]['fits'];initial_cost=cost({'x':{'fits':initial_stats}})
                    methods['fixed']={'selected':graph_spec(initial.json()),'logical_seconds':initial_cost['fit_seconds'],
                        'training_seconds':initial_cost['fit_seconds'],'fitting_updates':initial_cost['fitting_updates'],
                        'parent_sets':initial_cost['parent_sets'],'peak_vram_bytes':max(s['peak_vram_bytes'] for s in initial_stats),
                        'input_weighted_updates':initial_cost['input_weighted_updates'],
                        'status':'complete','candidate_count':1,'accepted_changes':0}
            value={'task':task,'condition':condition,'resource':resource,'config':cfg,'data_folder':str(folder.relative_to(root())),
                'data_hash':m['dataset_hash'],'partition_hashes':m['partition_hashes'],'prior':prior,'methods':methods,
                'source_hash':scientific_hash(),'selected_before_final':True}
            path=cp/(resource+'-frozen.json');atomic_json(path,value);records[resource]=str(path.relative_to(root()))
        output.append(records)
    atomic_json(root()/'runs'/(tag+'-complete.json'),{'task':task,'records':output,'identity':identity})
    return output

def pilot():
    config=read_json(PHASE/'configs/pilot.json');results=[]
    for d,seed,profile in [(20,390020,'sparse'),(50,390050,'dense'),(100,390100,'sparse')]:
        task={'d':d,'family':'heteroscedastic','profile':profile,'seed':seed,'development':True,'oracle':True,'corruptions':[.5]}
        start=time.monotonic();records=task_run(task,config)
        from .evaluation import evaluate_records
        evaluation_path=root()/'runs'/f'pilot-evaluation-{d}.json'
        with job(f'pilot-evaluation-{d}',{'task':task,'source':scientific_hash()}) as active:
            if active:atomic_json(evaluation_path,evaluate_records([root()/p for r in records for p in r.values()],development=True))
        evaluation=read_json(evaluation_path)
        results.append({'task':task,'wall_seconds':time.monotonic()-start,'records':records,'evaluation':evaluation})
        atomic_json(RESULTS/'pilots.json',results);print(json.dumps({'pilot_complete':d,'wall_seconds':results[-1]['wall_seconds']}),flush=True)

def main_tasks():
    tasks=[]
    # Balanced replication order preserves every primary size/family if the
    # device ceiling prevents optional profiles or later replications.
    for i in range(5):
        for fi,family in enumerate(('nonlinear','heteroscedastic')):
            for d in (20,50,100):tasks.append({'d':d,'family':family,'profile':'sparse','seed':310000+fi*10000+d*10+i,'oracle':i==0})
    for i in range(5):
        for pi,profile in enumerate(('dense','hub','deep')):
            tasks.append({'d':50,'family':'heteroscedastic','profile':profile,'seed':350000+pi*1000+i,'oracle':i==0})
    return tasks

def freeze():
    path=RESULTS/'protocol.json'
    if path.exists():return freeze_guard()
    if len(read_json(RESULTS/'pilots.json'))!=3:raise RuntimeError('Three complete pilots required')
    from .runtime import ledger
    book=ledger();tested=book.db.execute("SELECT config,status FROM jobs WHERE id='phase3-correctness-v4'").fetchone();book.db.close()
    if tested!=(digest({'source':scientific_hash()}),'complete'):raise RuntimeError('Current scientific source must pass the full correctness suite before freezing')
    cfg=read_json(PHASE/'configs/main.json');tasks=main_tasks()
    if cfg.get('fixed_total_sensitivity'):
        for d,b in [(50,160),(100,80)]:
            original=next(t for t in tasks if t['d']==d and t['family']=='heteroscedastic' and t['profile']=='sparse' and t['oracle'])
            tasks.append({**original,'budget':b,'sensitivity':'fixed-total-1600'})
    protocol={'config':cfg,'tasks':tasks,'scientific_hash':scientific_hash(),'historical_commit':'8c452ac',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pilot_sha256':file_hash(RESULTS/'pilots.json'),
        'source_files':{str(p.relative_to(PROJECT)):file_hash(p) for folder in (PROJECT/'src/sem_update/phase3',PHASE/'tests') for p in sorted(folder.glob('*.py'))},
        'dependency_lock_sha256':file_hash(PROJECT/'requirements.lock'),
        'primary_contrasts':['M3-fixed','M3-random','M3-M4','M3-M5'],'primary_endpoint':'T2 joint non-target SW1',
        'harm_definition':'returned T2 > fixed + max(0.001, 0.05*fixed)',
        'uncertainty':'paired independent SCM cluster bootstrap, 2000; Holm across all declared primary contrasts and study strata',
        'final_test_opened':False}
    atomic_json(path,protocol);return protocol

def run():
    protocol=freeze_guard();records=[]
    target=RESULTS/'frozen_selections.json'
    if target.exists():
        frozen=read_json(target)
        if frozen['source_hash']!=scientific_hash() or frozen['protocol_sha256']!=file_hash(RESULTS/'protocol.json'):
            raise ValueError('Incompatible sealed selection boundary')
        for name,sha in frozen['records'].items():
            if file_hash(root()/name)!=sha:raise ValueError('A sealed selected-model record changed')
        # Once sealed, even an incomplete result set is immutable. A later
        # reporting/evaluation resume must not replace it or fit new models.
        return
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
    from .runtime import ledger
    failures_path=root()/'runs/main_failures.json'
    pending=[];failures=read_json(failures_path) if failures_path.exists() else [];blocked=[];retries={}
    nontransient={digest(r['task']) for r in failures if not r['transient']}
    source=scientific_hash();book=ledger()
    for task in protocol['tasks']:
        identity={'task':task,'config':protocol['config'],'source':source};name='task-'+digest(identity)[:24]
        completed=book.db.execute('SELECT config,status FROM jobs WHERE id=?',('phase3-'+name,)).fetchone()
        if completed==(digest(identity),'complete'):
            output=read_json(root()/'runs'/(name+'-records.json'))['records']
            records.extend(p for r in output for p in r.values())
        elif digest(task) in nontransient:blocked.append(task)
        else:pending.append(task)
    book.db.close()
    with ProcessPoolExecutor(max_workers=protocol['config']['parallel_workers'],mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={}
        while pending or futures:
            while pending and len(futures)<protocol['config']['parallel_workers']:
                task=pending[0];book=snapshot();remaining=book['cumulative_cap_seconds']-book['cumulative_gpu_seconds']
                estimate=protocol['config'].get('estimated_task_seconds',{}).get(str(task['d']),5000)
                if remaining<protocol['config'].get('final_reserve_seconds',7200)+estimate:
                    blocked.extend(pending);pending=[];break
                pending.pop(0);futures[pool.submit(task_run,task,protocol['config'])]=task
            if not futures:break
            done,_=wait(futures,return_when=FIRST_COMPLETED)
            for future in done:
                task=futures.pop(future)
                try:
                    output=future.result();records.extend(p for r in output for p in r.values())
                    print(json.dumps({'completed_scm':task['seed'],'policy_conditions':len(records)}),flush=True)
                except Exception as error:
                    # Retry only identified transient resource/I/O failures, never
                    # a fresh seed or a numerical failure in search of a better fit.
                    message=str(error);key=digest(task);transient=any(s in message.lower() for s in ('out of memory','input/output error','temporarily unavailable'))
                    failures.append({'task':task,'error':message,'transient':transient,'traceback':traceback.format_exc()})
                    if transient and retries.get(key,0)<2:retries[key]=retries.get(key,0)+1;pending.append(task)
                    else:blocked.append(task)
                    atomic_json(root()/'runs/main_failures.json',failures)
    mechanism_manifest={str(p.relative_to(root())):file_hash(p) for p in sorted((root()/'checkpoints').glob('*.pt')) if not p.name.endswith('.partial.pt')}
    atomic_json(root()/'frozen_mechanisms.json',mechanism_manifest)
    frozen={'protocol_sha256':file_hash(RESULTS/'protocol.json'),'source_hash':scientific_hash(),
        'mechanism_manifest_sha256':file_hash(root()/'frozen_mechanisms.json'),'completed_mechanisms':len(mechanism_manifest),
        'planned_datasets':len(protocol['tasks']),'incomplete_tasks':blocked,'failure_records':len(failures),
        'records':{p:file_hash(root()/p) for p in records},'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(target,frozen)

def cli():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['doctor','test','pilot','freeze','run','evaluate','report'])
    args=parser.parse_args();setup()
    if args.command=='doctor':print(json.dumps(doctor(),indent=2))
    elif args.command=='test':
        import pytest
        require_cuda();status=0
        with job('correctness-v4',{'source':scientific_hash()}) as active:
            if active:
                previous=RESULTS/'correctness.json'
                if previous.exists():atomic_json(root()/'logs'/('correctness-summary-'+file_hash(previous)+'.json'),read_json(previous))
                xml=root()/'logs/correctness-v4.xml'
                status=pytest.main(['-q','--junitxml='+str(xml),'--basetemp='+str(root()/'correctness-v4-data'),'phase3/tests','tests','phase2/tests/test_methods.py','phase2/tests/test_phase2_protocol.py'])
                import xml.etree.ElementTree as ET
                cases=ET.parse(xml).findall('.//testcase')
                counts={k:sum(c.find(k) is not None for c in cases) for k in ('failure','error','skipped')}
                atomic_json(RESULTS/'correctness.json',{'exit_code':int(status),'tests':len(cases),
                    'passed':len(cases)-sum(counts.values()),**counts,'scientific_hash':scientific_hash(),
                    'junit_artifact':str(xml.relative_to(root())),'junit_sha256':file_hash(xml),
                    'scope':'Historical SCM tests, phase-two selection/baselines/protocol tests, and phase-three large-graph/grouped-flow/scaling checks'})
                if status:raise RuntimeError('Correctness tests failed')
        raise SystemExit(status)
    elif args.command=='pilot':pilot()
    elif args.command=='freeze':freeze()
    elif args.command=='run':run()
    elif args.command=='evaluate':
        from .evaluation import main
        main()
    else:
        from .reporting import main
        main()

if __name__=='__main__':cli()
