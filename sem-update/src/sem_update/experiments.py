"""Resumable orchestration, development-only selection, sealed benchmark protocol."""
import json
import time
import traceback
import subprocess
import sys
from pathlib import Path
import numpy as np
import torch
from .runtime import PROJECT,artifact_root,atomic_json,read_json,digest,file_hash,Ledger,source_state
from .graphs import DAG,corrupt,linear_bic_start,structural_metrics
from .data import prepare_synthetic,load_learner
from .training import DEFAULT_TRAIN,fit_graph
from .search import DEFAULT_SEARCH,repair,score

FAMILIES=('linear','nonlinear','heteroscedastic')
DEVELOPMENT_SEEDS={f:[90001+fi*1000+i for i in range(3)] for fi,f in enumerate(FAMILIES)}

def implementation_hash():
    names=('data.py','flows.py','graphs.py','training.py','diagnostics.py','metrics.py','search.py','dcdi.py','llm.py','chambers.py','evaluation.py','real_uncertainty.py','analysis.py','experiments.py','runtime.py')
    sources={name:file_hash(Path(__file__).with_name(name)) for name in names}
    sources.update({str(p.relative_to(PROJECT)):file_hash(p) for p in sorted((PROJECT/'prompts').glob('*.txt'))})
    return digest(sources)

def timed_job(ledger,job,config,fn,estimate=600):
    if not ledger.claim(job,config,expected_seconds=estimate):
        return None
    try:
        with ledger.device_interval(job):
            result=fn()
        ledger.finish(job)
        atomic_json(PROJECT/'results/curated/runtime_ledger.json',ledger.snapshot())
        return result
    except Exception:
        ledger.finish(job,traceback.format_exc())
        atomic_json(PROJECT/'results/curated/runtime_ledger.json',ledger.snapshot())
        raise

def tune_dcdi(validation_only=False):
    from .dcdi import discover,DEFAULT
    from .cli import require_cuda
    require_cuda()
    ledger=Ledger()
    rows=[]
    for family in FAMILIES:
        for seed in DEVELOPMENT_SEEDS[family]:
            root=prepare_synthetic(5,family,seed,400,development=True)
            data=load_learner(root,'cuda')
            for reg in (.1,1.):
                cfg={**DEFAULT,'reg_coeff':reg}
                job=f'development-dcdi-{family}-{seed}-{reg}-{implementation_hash()[:8]}'
                result_path=artifact_root()/'runs'/job/'summary.json'
                def run_one():
                    result=discover(data,cfg)
                    model,stats=fit_graph(data,DAG.from_json(result['graph']),DEFAULT_TRAIN)
                    scored=score(model,data.get('search'),DEFAULT_SEARCH)
                    row={'family':family,'seed':seed,'reg_coeff':reg,'score':scored,'discovery':result,
                         'refit_seconds':sum(s['actual_seconds'] for s in stats),'data_hash':data.key}
                    atomic_json(result_path,row)
                timed_job(ledger,job,{'data':data.key,'dcdi':cfg,'implementation':implementation_hash()},run_one,900)
                rows.append(read_json(result_path))
                atomic_json(PROJECT/'results/curated/dcdi_development.json',{'rows':rows,'complete':False})
                print(json.dumps({k:rows[-1][k] for k in ('family','seed','reg_coeff','score')}),flush=True)
                if validation_only:
                    return rows
    means={reg:float(np.mean([r['score']['total'] for r in rows if r['reg_coeff']==reg])) for reg in (.1,1.)}
    selected=min(means,key=lambda k:(means[k],k))
    atomic_json(PROJECT/'results/curated/dcdi_development.json',{'rows':rows,'complete':True,
                'selected_reg_coeff':selected,'mean_scores':means,'criterion':'development search score only; no reference graph or final outcomes'})

def make_config(sizes=(5,),study='controlled'):
    from .dcdi import DEFAULT
    return {'version':1,'study':study,'sizes':list(sizes),'families':list(FAMILIES),'scms_per_family':5,
            'budgets':[100,400],'corruptions':[.2,.5],'train':DEFAULT_TRAIN,'search':DEFAULT_SEARCH,
            'dcdi':DEFAULT,'metadata_variants':['coherent','anonymous','shuffled'],
            'semantic_seeds':[41001+i for i in range(5)],'cap_hours':64,'evaluation_samples':2048,
            'evaluation_projections':256,'cluster_bootstrap_replicates':2000,'bootstrap_seed':81123,
            'real_block_bootstrap_replicates':200,'real_block_rows':10,'parallel_workers':1}

def freeze(config_path):
    cfg=read_json(config_path)
    pilots=read_json(PROJECT/'results/curated/pilots.json')
    if len(pilots['pilots'])!=3:
        raise RuntimeError('three completed pilots are required')
    correctness=read_json(PROJECT/'results/curated/correctness.json')
    if not correctness['passed']:
        raise RuntimeError('correctness gate failed')
    if correctness.get('scientific_implementation_hash')!=implementation_hash():
        raise RuntimeError('correctness checks must cover the implementation being frozen')
    tuning=read_json(PROJECT/'results/curated/dcdi_development.json')
    if not tuning['complete'] or len(tuning['rows'])!=18:
        raise RuntimeError('DCDI development grid incomplete')
    if cfg['scms_per_family']!=5 or cfg['families']!=list(FAMILIES):
        raise ValueError('the authorized minimum preserves five SCMs in each of three families')
    cfg['dcdi']['reg_coeff']=tuning['selected_reg_coeff']
    target=PROJECT/'results/curated/frozen_protocol.json'
    if target.exists():
        old=read_json(target)
        if old['config']!=cfg or old['implementation_hash']!=implementation_hash():
            raise RuntimeError('protocol already frozen; amendments require explicit invalidation')
        return old
    matrix=[]
    for d in cfg['sizes']:
        for fi,family in enumerate(FAMILIES):
            for index in range(5):
                seed=11001+1000*fi+(d-5)*100+index
                for budget in cfg['budgets']:
                    root=prepare_synthetic(d,family,seed,budget)
                    manifest=read_json(root/'manifest.json')
                    matrix.append({'study':'controlled','d':d,'family':family,'seed':seed,'budget':budget,
                                   'data_id':manifest['id'],'data_hash':manifest['dataset_hash']})
    for seed in cfg['semantic_seeds']:
        root=prepare_synthetic(5,'heteroscedastic',seed,100,semantic=True)
        manifest=read_json(root/'manifest.json')
        matrix.append({'study':'semantic','d':5,'family':'heteroscedastic','seed':seed,'budget':100,
                       'data_id':manifest['id'],'data_hash':manifest['dataset_hash']})
    from .chambers import prepare
    root=prepare(400)
    manifest=read_json(root/'manifest.json')
    matrix.append({'study':'real','d':6,'family':'real','seed':34001,'budget':400,
                   'data_id':manifest['id'],'data_hash':manifest['dataset_hash']})
    protocol={'config':cfg,'matrix':matrix,'implementation_hash':implementation_hash(),
              'source':source_state(),'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
              'human_scientific_review':'pending','primary_endpoint':'T2 macro joint non-target SW1',
              'primary_comparisons':['diagnostic vs fixed','diagnostic vs random'],
              'defaults_retained_without_flow_score_tuning':True,
              'development_results_sha256':file_hash(PROJECT/'results/curated/dcdi_development.json'),
              'llm_revision_sha256':file_hash(PROJECT/'results/curated/llm_revision.json'),
              'dependency_lock_sha256':file_hash(PROJECT/'requirements.lock'),
              'final_test_opened':False,'pilots_hash':file_hash(PROJECT/'results/curated/pilots.json')}
    protocol['protocol_hash']=digest(protocol)
    compact=[]
    for item in matrix:
        path=artifact_root()/'data/processed'/item['data_id']/'manifest.json'
        manifest=read_json(path)
        compact.append({**item,'manifest_sha256':file_hash(path),
                        'non_test_intervention_rows':manifest['non_test_intervention_rows'],
                        'standardization':manifest['standardization'],'seen_targets':manifest['seen_targets'],
                        'roles':{role:[{'environment':e['name'],'rows':len(e['row_ids']),
                                      'row_ids_sha256':digest(e['row_ids']),'assignments':e['assignments'],
                                      'block_count':len(e.get('blocks',[]))} for e in environments]
                                 for role,environments in manifest['splits'].items()}})
    atomic_json(PROJECT/'results/curated/split_manifest.json',{'protocol_hash':protocol['protocol_hash'],
                'full_manifests':'.artifacts/data/processed/<data_id>/manifest.json','datasets':compact})
    atomic_json(target,protocol)
    return protocol

def proposal_stage(protocol):
    from .llm import metadata,generate_request
    for item in protocol['matrix']:
        if item['study']=='controlled':
            continue
        for variant in protocol['config']['metadata_variants']:
            nodes=metadata(item['study'],variant,item['seed'])
            root=artifact_root()/'runs'/'proposals'
            root.mkdir(parents=True,exist_ok=True)
            request=root/f'{item["data_id"]}-{variant}-request.json'
            output=root/f'{item["data_id"]}-{variant}.json'
            atomic_json(request,{'nodes':nodes,'roots':[0,1,2] if item['study']=='semantic' else [0,1,2,4],
                        'count':2,'seed':item['seed']+88500,'output':str(output)})
            result=generate_request(request)
            atomic_json(PROJECT/'results/curated/proposals'/output.name,result)

def run_suite(protocol_path=None,data_id=None):
    from .cli import require_cuda
    from .dcdi import discover
    from .llm import metadata,edit_callback
    require_cuda()
    protocol=read_json(protocol_path or PROJECT/'results/curated/frozen_protocol.json')
    if protocol['implementation_hash']!=implementation_hash():
        raise RuntimeError('frozen scientific implementation changed')
    if protocol['llm_revision_sha256']!=file_hash(PROJECT/'results/curated/llm_revision.json'):
        raise RuntimeError('frozen LLM model identity changed')
    cfg=protocol['config']
    if data_id is not None and data_id not in {item['data_id'] for item in protocol['matrix']}:
        raise ValueError('worker dataset is absent from the frozen matrix')
    ledger=Ledger(cap_hours=cfg['cap_hours'])
    if data_id is None and cfg.get('parallel_workers',1)>1:
        return parallel_suite(protocol,protocol_path)
    # Complete local LLM initialization stage before any flow fitting stage.
    if data_id is None:
        proposal_stage(protocol)
    run_index=[]
    summary_path=(artifact_root()/'runs/shards'/f'{data_id}.json') if data_id else PROJECT/'results/curated/run_index.json'
    if summary_path.exists():
        run_index=read_json(summary_path)['runs']
    known={r['run_id'] for r in run_index}

    for item in protocol['matrix']:
        if data_id is not None and item['data_id']!=data_id:
            continue
        root=artifact_root()/'data/processed'/item['data_id']
        data=load_learner(root,'cuda')
        if data.key!=item['data_hash']:
            raise RuntimeError('dataset changed after protocol freeze')
        roots=data.manifest.get('root_nodes',())
        if item['study']=='semantic':
            roots=(0,1,2)
        initialization_path=artifact_root()/'runs/initialization'/f'{item["data_id"]}.json'
        if initialization_path.exists():
            initialization=read_json(initialization_path)
            if initialization['data_hash']!=data.key:
                raise ValueError('initializer data changed')
            starter=DAG.from_json(initialization['graph'])
        else:
            began=time.monotonic()
            starter=linear_bic_start(data.get('fit')[0].x.cpu().numpy(),root_nodes=roots)
            initialization={'graph':starter.json(),'seconds':time.monotonic()-began,'data_hash':data.key,
                            'method':'fit-observational greedy linear Gaussian BIC; 100 moves; indegree 3'}
            atomic_json(initialization_path,initialization)
        truth=None if item['study']=='real' else DAG.from_json(read_json(root/'truth.json')['graph'])
        tasks=[]
        corruption_history={}
        base_id=item['data_id']
        tasks.append(('data_only',-1.,'none',[starter],'diagnostic','flow',None))
        # DCDI runs once per SCM/budget; no reference graph enters its interface.
        dcdi_job=base_id+'-dcdi-discovery'
        dcdi_summary=artifact_root()/'runs'/dcdi_job/'summary.json'
        def baseline():
            atomic_json(dcdi_summary,discover(data,cfg['dcdi'],roots))
        timed_job(ledger,dcdi_job,{'protocol':protocol['protocol_hash'],'data':data.key,'config':cfg['dcdi']},baseline,900)
        discovered=read_json(dcdi_summary)
        tasks.append(('dcdi',-1.,'none',[DAG.from_json(discovered['graph'])],'fixed','flow',None))
        if truth is not None:
            tasks.extend([('oracle',-1.,'none',[truth],'fixed','flow',None),
                          ('additive_oracle',-1.,'none',[truth],'fixed','additive',None)])
        if item['study']=='controlled':
            fractions=list(cfg['corruptions'])
            if item['family']=='heteroscedastic' and item['d']==5:
                fractions.append(0.)
            for fraction in fractions:
                start,corrupt_edits=corrupt(truth,fraction,item['seed']+int(fraction*1000)+37)
                corruption_history[fraction]=corrupt_edits
                for method,policy,kind in [('fixed','fixed','flow'),('diagnostic','diagnostic','flow'),
                                           ('random','random','flow'),('additive_fixed','fixed','additive')]:
                    tasks.append((method,fraction,'none',[start],policy,kind,None))
                if item['family']=='heteroscedastic' and item['d']==5 and item['budget']==100 and fraction==.5:
                    tasks.extend([('marginal',fraction,'none',[start],'marginal','flow',None),
                                  ('no_wasserstein',fraction,'none',[start],'diagnostic','flow',{'beta':0.}),
                                  ('additive_repair',fraction,'none',[start],'diagnostic','additive',None)])
        else:
            for variant in cfg['metadata_variants']:
                output=read_json(artifact_root()/'runs/proposals'/f'{base_id}-{variant}.json')
                llm_graphs=[DAG.from_json(g) for r in output['records'] if r['valid'] for g in r['graphs']][:2]
                starts=llm_graphs+[starter]
                # Duplicate initial DAGs are fitted/scored once; generation calls still count.
                starts=list({g.key:g for g in starts}.values())
                for method,policy in [('fixed','fixed'),('diagnostic','diagnostic'),('random','random'),('llm_edit','llm')]:
                    tasks.append((method,-1.,variant,starts,policy,'flow',None))
        for method,fraction,variant,starts,policy,kind,overrides in tasks:
            run_id=f'{base_id}-{method}-c{fraction:g}-{variant}'
            search_cfg={**cfg['search'],**(overrides or {})}
            def execute():
                cb=edit_callback(metadata(item['study'],variant,item['seed']),roots,run_id) if policy=='llm' else None
                return repair(data,starts,run_id,policy,cfg['train'],search_cfg,kind,roots,cb)
            timed_job(ledger,run_id,{'protocol':protocol['protocol_hash'],'method':method,'starts':[g.key for g in starts],
                                   'kind':kind,'search':search_cfg},execute,600)
            record=read_json(artifact_root()/'runs'/run_id/'selection.json')
            if run_id not in known:
                row={**item,'run_id':run_id,'method':method,'corruption':fraction,'metadata_variant':variant,
                     'selection_sha256':file_hash(artifact_root()/'runs'/run_id/'selection.json'),
                     'candidate_count':record['candidate_count'],'wall_seconds':record['wall_seconds'],
                     'data_initializer_seconds_once_per_dataset':initialization['seconds']}
                if truth is not None:
                    row['realized_initial_shd']=structural_metrics(DAG.from_json(record['candidates'][record['initial']]['graph']),truth)['shd']
                if fraction in corruption_history:
                    row['corruption_operations']=corruption_history[fraction]
                if method=='dcdi':
                    row['dcdi_discovery']=discovered
                run_index.append(row)
                known.add(run_id)
                atomic_json(summary_path,{'protocol_hash':protocol['protocol_hash'],'runs':run_index,'complete':False})
            print(json.dumps({'completed':run_id,'candidates':record['candidate_count'],
                              'gpu_job_hours':ledger.used_seconds()/3600}),flush=True)
    atomic_json(summary_path,{'protocol_hash':protocol['protocol_hash'],'runs':run_index,'complete':True})
    if data_id is not None:
        return run_index
    freeze_selections(protocol)

def freeze_selections(protocol):
    index_path=PROJECT/'results/curated/run_index.json'
    index=read_json(index_path)
    if not index['complete']:
        raise RuntimeError('incomplete matrix cannot freeze selections')
    compact=[]
    mechanisms={}
    for row in index['runs']:
        path=artifact_root()/'runs'/row['run_id']/'selection.json'
        if file_hash(path)!=row['selection_sha256']:
            raise ValueError('selection changed before freeze')
        result=read_json(path)
        for stage in ('initial','before_audit','selected'):
            for fitted in result['candidates'][result[stage]]['fits']:
                mechanisms[fitted['key']]={'cache_key':fitted['key'],'data_id':row['data_id'],
                    'kind':result['identity']['kind'],'node':fitted['node'],
                    'parents':json.dumps(fitted['parents']),'canonical_seed':fitted['canonical_seed'],
                    'optimizer_updates':fitted['updates'],'fit_seconds':fitted['fit_seconds']}
        compact.append({'run_id':row['run_id'],'data_id':row['data_id'],
                        'selection_sha256':row['selection_sha256'],'audit':result['audit'],
                        'graphs':{stage:result['candidates'][result[stage]]['graph']
                                  for stage in ('initial','before_audit','selected')},
                        'search_components':{stage:result['candidates'][result[stage]]['search']
                                             for stage in ('initial','before_audit','selected')},
                        'accepted_moves':[{**result['candidates'][e['after']]['edit'],
                                           'round':e['round'],'score_change':e['score_change']}
                                          for e in result['edits'] if e['accepted']]})
    graph_path=PROJECT/'results/curated/selected_graphs.json'
    atomic_json(graph_path,{'protocol_hash':protocol['protocol_hash'],'runs':compact})
    import csv
    mechanism_path=PROJECT/'results/curated/mechanism_manifest.csv'
    ordered=[mechanisms[k] for k in sorted(mechanisms)]
    with open(mechanism_path,'w') as output:
        writer=csv.DictWriter(output,fieldnames=list(ordered[0]))
        writer.writeheader()
        writer.writerows(ordered)
    frozen={'protocol_hash':protocol['protocol_hash'],'run_index_sha256':file_hash(index_path),
            'selected_graphs_sha256':file_hash(graph_path),'mechanism_manifest_sha256':file_hash(mechanism_path),
            'implementation_hash':implementation_hash(),
            'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    target=PROJECT/'results/curated/frozen_selections.json'
    if target.exists():
        old=read_json(target)
        if any(old.get(k)!=frozen[k] for k in ('protocol_hash','run_index_sha256','selected_graphs_sha256','mechanism_manifest_sha256','implementation_hash')):
            raise RuntimeError('frozen selections cannot change')
        return old
    atomic_json(target,frozen)
    return frozen

def parallel_suite(protocol,protocol_path=None):
    """Independent dataset processes; semantic/LLM edits execute only afterward."""
    import gc
    from collections import deque
    proposal_stage(protocol)
    gc.collect()
    torch.cuda.empty_cache()
    waiting=deque(item for item in protocol['matrix'] if item['study']=='controlled')
    active={}
    failures=[]
    workers=protocol['config']['parallel_workers']
    if workers not in (2,3,4):
        raise ValueError('only a measured small worker pool is supported')
    def harvest():
        runs=[]
        completed=0
        for item in protocol['matrix']:
            path=artifact_root()/'runs/shards'/f'{item["data_id"]}.json'
            if path.exists():
                shard=read_json(path)
                if shard['protocol_hash']!=protocol['protocol_hash']:
                    raise ValueError('incompatible matrix shard')
                runs.extend(shard['runs'])
                completed+=bool(shard['complete'])
        atomic_json(PROJECT/'results/curated/run_index.json',{'protocol_hash':protocol['protocol_hash'],
                    'runs':runs,'complete':completed==len(protocol['matrix'])})
        return completed
    while waiting or active:
        while waiting and len(active)<workers and not failures:
            item=waiting.popleft()
            log=open(artifact_root()/'logs'/f'suite-{item["data_id"]}.log','a')
            command=[sys.executable,'-u','-m','sem_update.cli','run','--data-id',item['data_id']]
            if protocol_path:
                command.extend(['--frozen-manifest',str(protocol_path)])
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=PROJECT)
            active[process]=(item['data_id'],log)
        for process,(identity,log) in list(active.items()):
            code=process.poll()
            if code is not None:
                log.close()
                del active[process]
                if code:
                    failures.append({'data_id':identity,'exit_code':code})
                print(json.dumps({'dataset_completed':identity,'exit_code':code}),flush=True)
        harvest()
        if failures and not active:
            atomic_json(artifact_root()/'runs/pool_failures.json',failures)
            raise RuntimeError('dataset workers failed; inspect preserved logs: '+str(failures))
        if waiting or active:
            time.sleep(5)
    for item in protocol['matrix']:
        if item['study']!='controlled':
            run_suite(protocol_path,item['data_id'])
            harvest()
    if harvest()!=len(protocol['matrix']):
        raise RuntimeError('incomplete matrix cannot freeze selections')
    freeze_selections(protocol)

def dispatch(args):
    if args.command=='freeze':
        print(json.dumps(freeze(args.config),indent=2))
    elif args.command=='run':
        if args.config and read_json(args.config).get('study')=='development':
            tune_dcdi(read_json(args.config).get('validation_only',False))
        else:
            run_suite(args.frozen_manifest,args.data_id)
    elif args.command=='evaluate':
        from .evaluation import evaluate
        evaluate(args.frozen_manifest)
    elif args.command=='export-paper':
        from .plotting import export_paper
        export_paper(args.plots_only)
