"""Calibration selection/combination and a single frozen-candidate audit."""
import time
import numpy as np
from sem_update.search import audit_pass
from .runtime import root,atomic_json,read_json,digest
from .bank import load_models,prefix_keys,cost
from sem_update.phase2.models import Ensemble
from .objectives import score,select,audit_score,energy_matrices,fit_weights

def graph_spec(graph):return {'kind':'flow','graph':graph}

def mixture_spec(keys,weights,bank):
    # Even a tiny positive component can dominate the density in its tail.
    # Drop exact zeros only, so saved predictions and audit logsumexp agree.
    pairs=[(k,float(w)) for k,w in zip(keys,weights) if w>0.]
    if len(pairs)==1:return graph_spec(bank['candidates'][pairs[0][0]]['graph'])
    total=sum(w for k,w in pairs)
    return {'kind':'ensemble','components':[bank['candidates'][k]['graph'] for k,w in pairs],
            'weights':[w/total for k,w in pairs]}

def choose(bank,data,config,run_id,development=False,controls=True):
    folder=root()/'runs'/run_id;folder.mkdir(parents=True,exist_ok=True)
    path=folder/'selection.json';frozen=folder/'before_audit.json'
    manifest=getattr(data,'manifest',{})
    partitions=manifest.get('partition_hashes',{})
    identity={'bank_hash':bank['bank_hash'],'config':config,'development':development,'controls':controls,
              'calibration_hash':partitions.get('calibration',manifest.get('arrays_sha256')),
              'audit_hash':partitions.get('audit',manifest.get('arrays_sha256'))}
    if path.exists():
        result=read_json(path)
        if result['identity']!=identity:raise ValueError('Incompatible selection resume')
        return result
    models=load_models(bank,data,config);initial=bank['initial'];base=graph_spec(bank['candidates'][initial]['graph'])
    scores={};score_times={}
    for key,model in models.items():
        start=time.monotonic();scores[key]=score(model,data.get('calibration'),config['search'])
        score_times[key]=time.monotonic()-start
    candidates={};predictions={};calibration_cost=sum(score_times.values())
    is_random=bank['identity']['policy']=='random';is_llm=bank['identity']['policy']=='llm'
    for name,rho in ([('random',0.)] if is_random else [('llm_edit',0.)] if is_llm else [('M3',0.),('M4',config['rho']),('rho0',0.)]):
        start=time.monotonic();chosen,values=select(scores,initial,rho,config['search']['improvement'])
        own_seconds=time.monotonic()-start
        candidates[name]={'spec':graph_spec(bank['candidates'][chosen]['graph']), 'selected_key':chosen,
            'calibration_objectives':values,'rho':rho,'selection_seconds':calibration_cost+own_seconds,
            'actual_selection_seconds':own_seconds+(calibration_cost if name in ('M3','random','llm_edit') else 0.),
            'logical_seconds':bank['logical_seconds'],'cost':bank['cost'],'candidate_count':len(models)}
        predictions[name]=models[chosen]
    if not is_random and not is_llm:
        # This list uses search-only scores and is fixed before using calibration.
        shortlist=[initial]+sorted((k for k in models if k!=initial),key=lambda k:(bank['candidates'][k]['search']['total'],k))[:2]
        start=time.monotonic()
        a,b,arrays=energy_matrices([models[k] for k in shortlist],data.get('calibration'),config['search']['samples'])
        np.savez_compressed(folder/'fixed_calibration_mixture_samples.npz',**arrays,a=a,b=b)
        energy_seconds=time.monotonic()-start
        for name,tau in [('M5',config['tau']),('tau0',0.),('uniform',None)]:
            start=time.monotonic()
            if tau is None:weights=np.ones(len(shortlist))/len(shortlist);opt={'kind':'uniform'}
            else:weights,opt=fit_weights(a,b,tau,development)
            own_seconds=time.monotonic()-start
            candidates[name]={'spec':mixture_spec(shortlist,weights,bank),'shortlist':shortlist,'weights':weights.tolist(),
                'optimizer':opt,'energy_a':a.tolist(),'energy_b':b.tolist(),
                'selection_seconds':energy_seconds+own_seconds,'actual_selection_seconds':own_seconds+(energy_seconds if name=='M5' else 0.),
                'logical_seconds':bank['logical_seconds'],
                'cost':bank['cost'],'candidate_count':len(models)}
            predictions[name]=Ensemble([models[k] for k in shortlist],weights)
    if controls and not is_llm:
        for axis,budgets in config['checkpoints'].items():
            for budget in budgets:
                keys=prefix_keys(bank,axis,budget)
                if not keys:continue
                name=f'checkpoint_{bank["identity"]["policy"]}_{axis}_{budget:g}'
                chosen,values=select({k:scores[k] for k in keys},initial,0.,config['search']['improvement'])
                subset={k:bank['candidates'][k] for k in keys};cc=cost(subset)
                prefix_seconds=max(c['prefix_cost'].get('gpu_job_seconds',c['prefix_cost']['fit_seconds']) for c in subset.values())
                candidates[name]={'spec':graph_spec(bank['candidates'][chosen]['graph']),'selected_key':chosen,
                    'checkpoint_axis':axis,'checkpoint_limit':budget,'cost':cc,'candidate_count':len(keys),
                    'prefix_gpu_job_seconds':prefix_seconds,
                    'selection_seconds':sum(score_times[k] for k in keys),
                    'logical_seconds':prefix_seconds,
                    'checkpoint_cost_scope':'canonical grouped fitting plus prefix search generation/scoring/diagnostics, then own calibration/audit'}
                predictions[name]=models[chosen]
    # Persist complete choices before any audit outcome is opened.
    scientific={name:{k:v for k,v in row.items() if k not in ('selection_seconds','actual_selection_seconds','logical_seconds')}
                for name,row in candidates.items()}
    freeze={'identity':identity,'initial':base,'candidates':scientific}
    if frozen.exists() and read_json(frozen)!=freeze:raise RuntimeError('Choices cannot change after audit access')
    atomic_json(frozen,freeze)
    audit_cache={}
    def audit(model,spec):
        key=digest(spec)
        if key not in audit_cache:
            ap=folder/('audit-'+key+'.json')
            if ap.exists():value=read_json(ap)
            else:
                start=time.monotonic();value={'score':audit_score(model,data.get('audit'),config['search']),
                                            'seconds':time.monotonic()-start}
                atomic_json(ap,value)
            audit_cache[key]=value
        return audit_cache[key]
    initial_audit=audit(models[initial],base)
    charged_audits=set()
    for name,row in candidates.items():
        chosen_audit=audit(predictions[name],row['spec'])
        passed=audit_pass(initial_audit['score'],chosen_audit['score'],config['search'])
        row.update(before_audit=row.pop('spec'),audit_pass=passed)
        row['selected']=row['before_audit'] if passed else base
        row['initial']=base;row['retained_initial']=digest(row['selected'])==digest(base)
        row['audit']={'initial':initial_audit['score'],'candidate':chosen_audit['score'],'pass':passed}
        row['selection_seconds']+=initial_audit['seconds']+(0. if digest(row['before_audit'])==digest(base) else chosen_audit['seconds'])
        for spec,value in [(base,initial_audit),(row['before_audit'],chosen_audit)]:
            if digest(spec) not in charged_audits:
                row['actual_selection_seconds']=row.get('actual_selection_seconds',0.)+value['seconds']
                charged_audits.add(digest(spec))
        row['logical_seconds']+=row['selection_seconds']
    result={'identity':identity,'bank_hash':bank['bank_hash'],'calibration_scores':scores,
            'methods':candidates,'one_time_audit':True,'no_candidate_after_rejection':True}
    atomic_json(path,result);return result
