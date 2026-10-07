"""Resumable phase-two tasks, timed pilots, protocol freeze and method registry."""
import argparse
import copy
import json
import sys
import time
from pathlib import Path
import numpy as np
import torch
from sem_update.training import atomic_torch
from sem_update.graphs import DAG,corrupt,linear_bic_start
from .runtime import (PROJECT,PHASE,RESULTS,root,setup,require_cuda,job,snapshot,
                      atomic_json,compact_json,read_json,digest,file_hash,scientific_hash,freeze_guard,prior_attempt_seconds)
from .data import prepare,prepare_real,load
from .bank import build,fit_graph,cost
from .models import EmpiricalMarginals,ridge_fit
from .objectives import score
from .selection import choose,graph_spec
from .discovery import discover

def default_config():
    old=read_json(PROJECT/'configs/core.yaml')
    return {'version':2,'sizes':[5],'families':old['families'],'scms_per_family':5,
        'family_seed_bases':{'linear':211001,'nonlinear':212001,'heteroscedastic':213001},
        'budgets':[100,400],'corruptions':[.2,.5],'semantic_seeds':list(range(241001,241006)),
        'metadata_variants':['coherent','anonymous','shuffled'],'train':old['train'],'search':old['search'],
        'dcdi':{**old['dcdi'],'flow_layers':2,'flow_width':8},'ridge_grid':[.001,.01,.1,1.],
        'ridge_alpha':.01,'ridge_variance_floor':1e-4,'rho':.5,'tau':.01,
        'evaluation_samples':2048,'evaluation_projections':256,'additional_gpu_hours':16,
        'bootstrap_replicates':2000,'bootstrap_seed':261017,'real_block_rows':10,
        'checkpoints':{'fitting_updates':[4000,6000,8000,10000,12000],
                       'fit_seconds':[60,120,180,240,360]},'parallel_workers':1}

def timed(name,identity,path,fn,estimate=0):
    with job(name,identity,estimate) as active:
        if active:
            torch.cuda.reset_peak_memory_stats();start=time.monotonic()
            result=fn();torch.cuda.synchronize()
            result['actual_incremental_seconds']=time.monotonic()-start+prior_attempt_seconds(name)
            result['actual_peak_vram_bytes']=torch.cuda.max_memory_allocated()
            atomic_json(path,result)
    if not path.exists():raise RuntimeError('Completed job lacks its artifact: '+name)
    return read_json(path)

def learner_item(folder,study):
    m=read_json(folder/'manifest.json')
    return {'study':study,'d':m['d'],'family':m['family'],'seed':m['seed'],
            'budget':m['budget_per_target'],'data_id':m['id'],'data_hash':m['dataset_hash'],
            'manifest_sha256':file_hash(folder/'manifest.json')}

def prepare_item(d,family,seed,budget,study='controlled',development=False):
    folder=prepare(d,family,seed,budget,development,study=='semantic')
    return learner_item(folder,study)

def proposal_stage(items,cfg):
    from .llm import initial
    for item in items:
        if item['study']=='controlled':continue
        m=read_json(root()/'data/processed'/item['data_id']/'manifest.json')
        for variant in cfg['metadata_variants']:
            initial(item['study'],variant,item['seed'],m['root_nodes'],item['data_id'])
            print(json.dumps({'proposal_complete':item['data_id'],'variant':variant}),flush=True)

def run_dataset(item,cfg,development=False):
    folder=root()/'data/processed'/item['data_id'];data=load(folder,allowed=('fit','early','search'))
    if data.key!=item['data_hash']:raise RuntimeError('Dataset changed after protocol preparation')
    if file_hash(folder/'manifest.json')!=item.get('manifest_sha256',file_hash(folder/'manifest.json')):
        raise RuntimeError('Frozen full partition manifest changed')
    roots=data.manifest['root_nodes'];base=item['data_id'];output=root()/'runs/datasets'/base
    output.mkdir(parents=True,exist_ok=True)
    config_hash=digest(cfg)
    if (output/'complete.json').exists():
        completed=read_json(output/'complete.json')
        if completed['config_hash']!=config_hash:raise ValueError('Incompatible dataset resume')
        return completed
    # Discovery has no reference graph, calibration, audit or final-test view.
    def discovery():
        result=discover(data,cfg['dcdi'],roots)
        graph=DAG.from_json(result['graph']);_,fits=fit_graph(data,graph,cfg['train'])
        return {'discovery':result,'graph':graph.json(),'fits':fits,
                'cost':cost({'discovered':{'fits':fits}})}
    dcdi=timed(base+'-discovery',{'data':data.key,'config':cfg['dcdi'],'train':cfg['train']},
               output/'discovery.json',discovery,300)
    def marginals():
        start=time.monotonic();m=EmpiricalMarginals(data.get('fit')[0].x)
        atomic_torch(output/'marginals.pt',m.state_dict())
        return {'spec':{'kind':'marginal','path':str((output/'marginals.pt').relative_to(root()))},
                'fit_seconds':time.monotonic()-start,'data_hash':data.key}
    marginal=timed(base+'-marginal',{'data':data.key},output/'marginal.json',marginals)
    if item['study']=='controlled':
        truth=DAG.from_json(read_json(folder/'truth.json')['graph'])
        tasks=[]
        for fraction in cfg['corruptions']:
            g,edits=corrupt(truth,fraction,item['seed']+int(fraction*1000)+37)
            tasks.append((fraction,'none',[g],{'corruption_operations':edits}))
    else:
        def initialize():
            start=time.monotonic();graph=linear_bic_start(data.get('fit')[0].x.cpu().numpy(),root_nodes=roots)
            return {'graph':graph.json(),'seconds':time.monotonic()-start}
        init=timed(base+'-data-initialization',{'data':data.key,'roots':roots},output/'initializer.json',initialize)
        tasks=[]
        for variant in cfg['metadata_variants']:
            result=read_json(root()/'runs/proposals'/(base+'-'+variant+'.request.result.json'))
            graphs=[DAG.from_json(g) for r in result['records'] if r['valid'] for g in r['graphs']]
            graphs.append(DAG.from_json(init['graph']));graphs=list({g.key:g for g in graphs}.values())
            tasks.append((-1.,variant,graphs,{'initialization_seconds':init['seconds']+result['stage_seconds'],
                'initial_llm_peak_bytes':result['peak_vram_bytes'],'initial_llm_identity':result['identity_hash']}))
    records=[]
    for fraction,variant,starts,extra in tasks:
        task=f'{base}-c{fraction:g}-{variant}';tp=root()/'runs'/task;tp.mkdir(parents=True,exist_ok=True)
        identity={'data':data.key,'starts':[g.json() for g in starts],'config':cfg}
        diagnostic=timed(task+'-diagnostic',identity,tp/'bank_execution.json',
            lambda:build(data,starts,task+'-diagnostic',cfg,'diagnostic',roots),120)
        # Runtime wrapper fields are outside the immutable bank payload.
        diagnostic=read_json(root()/'runs'/(task+'-diagnostic')/'bank.json')
        initial_graph=DAG.from_json(diagnostic['candidates'][diagnostic['initial']]['graph'])
        initial=graph_spec(initial_graph.json())
        def ridge():
            start=time.monotonic();model=ridge_fit(data,initial_graph,cfg['ridge_alpha'],cfg['ridge_variance_floor'])
            atomic_torch(tp/'ridge.pt',model.state_dict())
            return {'spec':{'kind':'ridge','graph':initial_graph.json(),'path':str((tp/'ridge.pt').relative_to(root()))},
                    'fit_seconds':time.monotonic()-start}
        ridge_result=timed(task+'-ridge',{'data':data.key,'graph':initial_graph.json(),'alpha':cfg['ridge_alpha']},tp/'ridge.json',ridge)
        with_view=load(folder,allowed=('fit','early','calibration','audit'))
        selected=timed(task+'-selection',{'bank':diagnostic['bank_hash'],'config':cfg},tp/'selected_execution.json',
            lambda:choose(diagnostic,with_view,cfg,task+'-selection',development))
        methods=selected['methods']
        fixed_cost=cost({'initial':diagnostic['candidates'][diagnostic['initial']]})
        def baseline(spec,seconds,cost_record=None,extra_record=None):
            return {'initial':initial,'before_audit':spec,'selected':spec,'retained_initial':None,
                    'audit_pass':None,'candidate_count':1,'selection_seconds':0.,'logical_seconds':seconds,
                    'cost':cost_record or {'fit_seconds':seconds,'fitting_updates':0,'parent_sets':0},**(extra_record or {})}
        methods['fixed']=baseline(initial,fixed_cost['fit_seconds'],fixed_cost)
        methods['M0']=baseline(marginal['spec'],marginal['fit_seconds'])
        methods['M1']=baseline(ridge_result['spec'],ridge_result['fit_seconds'])
        methods['M2']=baseline(graph_spec(dcdi['graph']),dcdi['cost']['fit_seconds']+dcdi['discovery']['seconds'],dcdi['cost'],
            {'discovery_seconds':dcdi['discovery']['seconds'],'discovery_updates':dcdi['discovery']['optimization_steps'],
             'discovery_converged':dcdi['discovery']['converged'],'projection_removed_edges':dcdi['discovery']['projection_removed_edges'],
             'discovery_peak_bytes':dcdi['discovery']['peak_vram_bytes']})
        random=timed(task+'-random',identity,tp/'random_execution.json',
            lambda:build(data,starts,task+'-random',cfg,'random',roots),60)
        random=read_json(root()/'runs'/(task+'-random')/'bank.json')
        if random['initial']!=diagnostic['initial']:raise RuntimeError('Repair policies received different G0 models')
        random_selection=timed(task+'-random-selection',{'bank':random['bank_hash'],'config':cfg},tp/'random_selected_execution.json',
            lambda:choose(random,with_view,cfg,task+'-random-selection',development))
        methods.update(random_selection['methods'])
        if methods['M3']['selected']!=methods['rho0']['selected']:
            raise RuntimeError('rho=0 control must reproduce average calibration selection exactly')
        llm_bank=None
        if item['study']!='controlled':
            from .llm import callback
            cb=callback(item['study'],variant,item['seed'],roots,task+'-llm')
            # llm_callback moves every instantiated flow to CPU before the
            # separate frozen LLM process; this caller holds no flow models.
            llm_bank=timed(task+'-llm',identity,tp/'llm_execution.json',
                lambda:build(data,starts,task+'-llm',cfg,'llm',roots,cb),120)
            llm_bank=read_json(root()/'runs'/(task+'-llm')/'bank.json')
            llm_selected=timed(task+'-llm-selection',{'bank':llm_bank['bank_hash'],'config':cfg},tp/'llm_selected_execution.json',
                lambda:choose(llm_bank,with_view,cfg,task+'-llm-selection',development,False))
            methods.update(llm_selected['methods'])
        row={**item,'task_id':task,'corruption':fraction,'metadata_variant':variant,'initial_graph':initial_graph.json(),
             'data_hash':data.key,'methods':methods,'diagnostic_bank_hash':diagnostic['bank_hash'],
             'random_bank_hash':random['bank_hash'],'diagnostic_bank_path':str((root()/'runs'/(task+'-diagnostic')/'bank.json').relative_to(root())),
             'random_bank_path':str((root()/'runs'/(task+'-random')/'bank.json').relative_to(root())),
             'llm_bank_path':None if llm_bank is None else str((root()/'runs'/(task+'-llm')/'bank.json').relative_to(root())),
             'non_test_intervention_rows':data.manifest['non_test_intervention_rows'],**extra}
        for name,m in row['methods'].items():
            bank=llm_bank if name=='llm_edit' else random if name=='random' or name.startswith('checkpoint_random') else diagnostic
            m['peak_vram_bytes']=max(bank['peak_vram_bytes'] if name not in ('M0','M1','M2') else
                marginal['actual_peak_vram_bytes'] if name=='M0' else ridge_result['actual_peak_vram_bytes'] if name=='M1' else dcdi['actual_peak_vram_bytes'],
                m.get('discovery_peak_bytes',0),extra.get('initial_llm_peak_bytes',0) if name not in ('M0','M2') else 0)
            m['initialization_seconds']=extra.get('initialization_seconds',0) if name not in ('M0','M2') else 0
            m['logical_seconds']+=m['initialization_seconds']
            # Actual incremental attribution depends on the documented execution
            # order; all repair variants still pay the full logical bank cost.
            actual=m.get('actual_selection_seconds',0.)
            execution={'M3':'bank_execution.json','random':'random_execution.json','llm_edit':'llm_execution.json'}
            if name in execution:actual+=read_json(tp/execution[name])['actual_incremental_seconds']
            if name=='M0':actual=marginal['actual_incremental_seconds']
            if name=='M1':actual=ridge_result['actual_incremental_seconds']
            if name=='M2':actual=dcdi['actual_incremental_seconds']
            m['actual_incremental_seconds']=actual
        atomic_json(tp/'task.json',row);records.append(row)
        print(json.dumps({'task_complete':task,'methods':len(methods),'phase2_gpu_hours':snapshot()['phase2_gpu_seconds']/3600}),flush=True)
    result={'config_hash':config_hash,'item':item,'tasks':records,'complete':True}
    atomic_json(output/'complete.json',result);return result

def test_suite():
    import pytest
    tests=root()/'tests';tests.mkdir(exist_ok=True)
    label='correctness-'+scientific_hash()[:12]+'-'+str(int(time.time()))
    report=RESULTS/'correctness.json'
    with job(label,{'scientific_hash':scientific_hash()}) as active:
        code=pytest.main(['-q','tests','phase2/tests/test_methods.py','phase2/tests/test_phase2_protocol.py',
                         '--basetemp='+str(tests/label)])
        atomic_json(report,{'passed':code==0,'exit_code':int(code),'scientific_hash':scientific_hash(),
                           'test_files':[str(p.relative_to(PROJECT)) for p in (PHASE/'tests').glob('*.py')]})
        if code:raise RuntimeError('Correctness suite failed; results preserved')
    return read_json(report)

def development():
    cfg=default_config();rows=[]
    for family,seed in [('linear',290001),('nonlinear',291001),('heteroscedastic',292001)]:
        with job('ridge-development-'+family,{'family':family,'seed':seed,'grid':cfg['ridge_grid']}) as active:
            path=RESULTS/('development-ridge-'+family+'.json')
            if active:
                item=prepare_item(5,family,seed,100,development=True)
                data=load(root()/'data/processed'/item['data_id'],allowed=('fit','early','search'))
                # Data-only initial graph; the regularizer is never chosen using truth.
                graph=linear_bic_start(data.get('fit')[0].x.cpu().numpy())
                values=[]
                for alpha in cfg['ridge_grid']:
                    model=ridge_fit(data,graph,alpha,cfg['ridge_variance_floor'])
                    values.append({'alpha':alpha,'score':score(model,data.get('search'),cfg['search'])})
                atomic_json(path,{'item':item,'graph':graph.json(),'values':values})
        rows.append(read_json(path))
    means={a:float(np.mean([v['score']['total'] for r in rows for v in r['values'] if v['alpha']==a])) for a in cfg['ridge_grid']}
    chosen=min(means,key=lambda a:(means[a],a));cfg['ridge_alpha']=chosen
    atomic_json(RESULTS/'ridge_development.json',{'rows':rows,'mean_scores':means,'chosen':chosen,'complete':True})
    atomic_json(PHASE/'configs/phase2.json',cfg);return cfg

def pilots():
    prior=read_json(RESULTS/'pilots.json') if (RESULTS/'pilots.json').exists() else {'pilots':[],'complete':False}
    if prior['complete']:return prior['pilots']
    cfg=read_json(PHASE/'configs/phase2.json');records=prior['pilots']
    for family,seed,budget in [('linear',295001,100),('heteroscedastic',295002,400)]:
        if any(r['item']['seed']==seed for r in records):continue
        pilot_cfg={**cfg,'corruptions':[.5]}
        start=snapshot()['phase2_gpu_seconds'];wall=time.monotonic()
        with job('prepare-pilot-'+family,{'seed':seed,'budget':budget}) as active:
            item=prepare_item(5,family,seed,budget,development=True)
        result=run_dataset(item,pilot_cfg,True)
        from .evaluation import evaluate_tasks
        evaluate_tasks(result['tasks'],pilot_cfg,development=True)
        artifact_bytes=sum(p.stat().st_size for p in root().rglob('*') if p.is_file() and not p.is_symlink())
        records.append({'item':item,'gpu_seconds':snapshot()['phase2_gpu_seconds']-start,
            'wall_seconds':time.monotonic()-wall,'artifact_bytes_cumulative':artifact_bytes,
            'discovery':read_json(root()/'runs/datasets'/item['data_id']/'discovery.json')['discovery'],
            'methods_per_task':len(result['tasks'][0]['methods'])})
        atomic_json(RESULTS/'pilots.json',{'pilots':records,'complete':len(records)==2})
        print(json.dumps({'pilot_complete':family,'gpu_seconds':records[-1]['gpu_seconds']}),flush=True)
    return records

def llm_check():
    """Actual development generation -> valid edit -> common-flow verifier."""
    from .llm import callback
    cfg=read_json(PHASE/'configs/phase2.json');cfg={**cfg,'metadata_variants':['coherent']}
    with job('llm-development-data',{'seed':295101}) as active:
        item=prepare_item(5,'heteroscedastic',295101,100,'semantic',True)
    proposal_stage([item],cfg)
    data=load(root()/'data/processed'/item['data_id'],allowed=('fit','early','search'))
    proposal=read_json(root()/'runs/proposals'/(item['data_id']+'-coherent.request.result.json'))
    starts=[DAG.from_json(g) for r in proposal['records'] if r['valid'] for g in r['graphs']]
    starts.append(linear_bic_start(data.get('fit')[0].x.cpu().numpy(),root_nodes=[0,1,2]))
    starts=list({g.key:g for g in starts}.values());name=item['data_id']+'-llm-validation'
    cb=callback('semantic','coherent',item['seed'],[0,1,2],name)
    bank=timed(name,{'data':data.key,'config':cfg},root()/'runs'/name/'execution.json',
               lambda:build(data,starts,name,cfg,'llm',[0,1,2],cb))
    counts={}
    for edit in bank['edits']:
        for key,value in edit['proposal_record']['counts'].items():counts[key]=counts.get(key,0)+value
        counts['score_rejections']=counts.get('score_rejections',0)+edit['score_rejections']
        counts['accepted_changes']=counts.get('accepted_changes',0)+int(edit['accepted'])
    report={'item':item,'actual_local_generation':True,'counts':counts,'candidate_count':len(bank['candidates']),
        'complete':counts.get('valid_new_edits',0)>0,'revision':proposal['revision'],
        'bank_hash':bank['bank_hash'],'no_main_or_final_outcomes':True}
    atomic_json(RESULTS/'llm_development_check.json',report)
    if not report['complete']:raise RuntimeError('No new development LLM edit reached the verifier; inspect actual outputs')
    return report

def freeze():
    cfg=read_json(PHASE/'configs/phase2.json');pilots=read_json(RESULTS/'pilots.json')
    correctness=read_json(RESULTS/'correctness.json')
    if not pilots['complete'] or len(pilots['pilots'])!=2:raise RuntimeError('Two pilots are required')
    if not correctness['passed'] or correctness['scientific_hash']!=scientific_hash():raise RuntimeError('Correctness does not cover frozen source')
    if not read_json(RESULTS/'llm_development_check.json')['complete']:raise RuntimeError('Actual LLM edit path has not passed development validation')
    if (RESULTS/'protocol.json').exists():return freeze_guard()
    matrix=[]
    with job('prepare-main-data',{'config':cfg,'scientific_hash':scientific_hash()}) as active:
        for d in cfg['sizes']:
            for family in cfg['families']:
                for i in range(cfg['scms_per_family']):
                    seed=cfg['family_seed_bases'][family]+i+(d-5)*100
                    for budget in cfg['budgets']:matrix.append(prepare_item(d,family,seed,budget))
        for seed in cfg['semantic_seeds']:matrix.append(prepare_item(5,'heteroscedastic',seed,100,'semantic'))
        matrix.append(learner_item(prepare_real(),'real'))
    splits=[]
    for item in matrix:
        p=root()/'data/processed'/item['data_id']/'manifest.json';m=read_json(p)
        splits.append({**item,'manifest_sha256':file_hash(p),'non_test_intervention_rows':m['non_test_intervention_rows'],
            'roles':{r:[{'environment':e['name'],'rows':len(e['row_ids']),'row_ids_sha256':digest(e['row_ids']),
                        'assignment_sha256':digest(e['assignments']),'blocks':e.get('blocks',[])} for e in envs] for r,envs in m['splits'].items()}})
    atomic_json(RESULTS/'splits.json',splits)
    record={'config':cfg,'matrix':matrix,'scientific_hash':scientific_hash(),'splits_sha256':file_hash(RESULTS/'splits.json'),
        'historical_commit':'ad21e604ef37f65e20ce32d78b0c2d04a0737cd7','dependency_lock_sha256':file_hash(PROJECT/'requirements.lock'),
        'primary_endpoint':'T2 standardized joint non-target sliced Wasserstein, equal environments',
        'pilots_sha256':file_hash(RESULTS/'pilots.json'),'correctness_sha256':file_hash(RESULTS/'correctness.json'),
        'reporting_source_at_freeze':file_hash(Path(__file__).with_name('reporting.py')),
        'illustration_source_at_freeze':file_hash(Path(__file__).with_name('illustrations.py')),
        'human_scientific_review':'pending; no approval inferred','timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    record['protocol_hash']=digest(record);atomic_json(RESULTS/'protocol.json',record);return record

def run_suite(data_id=None):
    protocol=freeze_guard();cfg=protocol['config']
    if data_id is None:proposal_stage(protocol['matrix'],cfg)
    if data_id is None and cfg['parallel_workers']>1:
        import subprocess
        from collections import deque
        waiting=deque(item for item in protocol['matrix'] if item['study']=='controlled');active={};failures=[]
        while waiting or active:
            while waiting and len(active)<cfg['parallel_workers'] and not failures:
                item=waiting.popleft();log=open(root()/'logs'/('dataset-'+item['data_id']+'.log'),'a')
                process=subprocess.Popen([sys.executable,'-u','-m','sem_update.phase2.runner','run','--data-id',item['data_id']],
                    stdout=log,stderr=subprocess.STDOUT,cwd=PROJECT)
                active[process]=(item,log)
            for process,(item,log) in list(active.items()):
                code=process.poll()
                if code is None:continue
                log.close();del active[process]
                if code:failures.append({'data_id':item['data_id'],'exit_code':code})
                print(json.dumps({'dataset_complete':item['data_id'],'exit_code':code}),flush=True)
            if failures and not active:
                atomic_json(root()/'runs/worker_failures.json',failures)
                raise RuntimeError('Worker failures preserved; resume the same data/configuration after diagnosis')
            if waiting or active:time.sleep(5)
        # No flow workers overlap the subsequent memory-heavy LLM edit stages.
        for item in protocol['matrix']:
            if item['study']!='controlled':run_dataset(item,cfg)
    else:
        for item in protocol['matrix']:
            if data_id is None or item['data_id']==data_id:run_dataset(item,cfg)
    if data_id is not None:return
    tasks=[]
    for item in protocol['matrix']:
        record=read_json(root()/'runs/datasets'/item['data_id']/'complete.json')
        if not record['complete']:raise RuntimeError('Incomplete matrix')
        # Detailed calibration objectives and optimizer matrices remain in the
        # immutable artifact records; the Git manifest retains selected models.
        for task in record['tasks']:
            compact=copy.deepcopy(task)
            for method in compact['methods'].values():
                for key in ('calibration_objectives','energy_a','energy_b','optimizer'):
                    method.pop(key,None)
            tasks.append(compact)
    selected={'protocol_hash':protocol['protocol_hash'],'tasks':tasks,'complete':True}
    path=RESULTS/'selected_models.json'
    if path.exists() and read_json(path)!=selected:raise RuntimeError('Frozen selections cannot change')
    compact_json(path,selected)
    import csv
    mechanism_rows=[]
    for checkpoint in sorted((root()/'checkpoints').glob('*/*.pt')):
        if checkpoint.name.endswith('.partial.pt'):continue
        value=torch.load(checkpoint,map_location='cpu',weights_only=False)
        stats=value['stats']
        mechanism_rows.append({'cache_key':value['key'],'checkpoint_sha256':file_hash(checkpoint),
            'checkpoint_bytes':checkpoint.stat().st_size,'data_hash':value['data_hash'],
            'node':stats['node'],'parents':json.dumps(stats['parents']),
            'canonical_seed':stats['canonical_seed'],'fitting_updates':stats['updates'],'fit_seconds':stats['fit_seconds']})
    mp=RESULTS/'mechanism_manifest.csv'
    with open(mp,'w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(mechanism_rows[0]));writer.writeheader();writer.writerows(mechanism_rows)
    simple={m[stage]['path'] for t in tasks for m in t['methods'].values() for stage in ('selected','before_audit') if 'path' in m[stage]}
    atomic_json(RESULTS/'simple_model_manifest.json',{p:file_hash(root()/p) for p in sorted(simple)})
    frozen={'protocol_hash':protocol['protocol_hash'],'selected_models_sha256':file_hash(path),
            'scientific_hash':scientific_hash(),'tasks':len(tasks),
            'mechanism_manifest_sha256':file_hash(mp),'simple_model_manifest_sha256':file_hash(RESULTS/'simple_model_manifest.json'),
            'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    if not (RESULTS/'frozen_selections.json').exists():atomic_json(RESULTS/'frozen_selections.json',frozen)
    return selected

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['doctor','test','development','pilots','llm-check','freeze','run','evaluate','report'])
    parser.add_argument('--data-id');args=parser.parse_args();setup();require_cuda()
    class Tee:
        def __init__(self,stream,file):self.stream=stream;self.file=file
        def write(self,text):self.stream.write(text);self.file.write(text);self.file.flush()
        def flush(self):self.stream.flush();self.file.flush()
        def isatty(self):return False
    log=open(root()/'logs'/(args.command+'-'+str(time.time_ns())+'.log'),'a')
    sys.stdout=Tee(sys.stdout,log);sys.stderr=Tee(sys.stderr,log)
    if args.command=='doctor':
        from .runtime import doctor
        print(json.dumps(doctor(),indent=2))
    elif args.command=='test':test_suite()
    elif args.command=='development':development()
    elif args.command=='pilots':pilots()
    elif args.command=='llm-check':llm_check()
    elif args.command=='freeze':freeze()
    elif args.command=='run':run_suite(args.data_id)
    elif args.command=='evaluate':
        from .evaluation import evaluate
        evaluate()
    elif args.command=='report':
        from .reporting import report
        report()

if __name__=='__main__':main()
