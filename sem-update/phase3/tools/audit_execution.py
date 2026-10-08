"""CPU verification of frozen inputs, common banks, selection and final evidence."""
import argparse
import json
import math
import hashlib
import numpy as np
import pandas as pd
from sem_update.graphs import DAG
from sem_update.data import validate_splits
from sem_update.phase2.data import partition_hashes,training_identity
from sem_update.phase3.runtime import root,RESULTS,freeze_guard,read_json,digest,file_hash,atomic_json
from sem_update.phase3.bank import subbank,cost
from sem_update.phase3.evaluation import aggregate

def inputs_and_selection(frozen):
    datasets={};banks={};records=[];weights=[];priors={}
    for name,sha in frozen['records'].items():
        path=root()/name;assert file_hash(path)==sha
        record=read_json(path);folder=root()/record['data_folder'];m=read_json(folder/'manifest.json')
        if m['id'] not in datasets:
            validate_splits(m);assert file_hash(folder/'learner.npz')==m['arrays_sha256']
            with np.load(folder/'learner.npz') as arrays:
                assert partition_hashes(m,arrays)==m['partition_hashes']
                assert training_identity(m)==m['dataset_hash']
                counts={role:sum(len(arrays[e['array']]) for e in envs if e['assignments']) for role,envs in m['splits'].items()}
                assert sum(counts.values())==m['non_test_intervention_rows']==m['budget_per_target']*len(m['seen_targets'])
                assert not set(m['seen_targets'])&set(m['withheld_targets'])
                assert np.allclose(arrays['fit_obs'].mean(0),0,atol=2e-6)
                assert np.allclose(arrays['fit_obs'].std(0),1,atol=2e-6)
            datasets[m['id']]={'scm':m['seed'],'family':m['family'],'profile':m['profile'],'d':m['d'],
                'budget':m['budget_per_target'],'sensitivity':m.get('sensitivity','primary'),
                **read_json(folder/'topology.json'),'visible_targets':len(m['seen_targets']),
                'visible_fraction':m['visible_fraction'],'intervention_rows':sum(counts.values()),
                **{role+'_intervention_rows':n for role,n in counts.items()},'dataset_hash':m['dataset_hash']}
        cfg=record['config'];methods=record['methods']
        prior=record['prior']
        priors[record['condition']]={'scm':m['seed'],'family':m['family'],'profile':m['profile'],'d':m['d'],
            'budget':m['budget_per_target'],'sensitivity':m.get('sensitivity','primary'),
            'corruption':prior['corruption_fraction'],'edit_operations':len(prior['edit_history']),
            'initial_graph_hash':DAG.from_json(prior['graph']).key,
            **{'initial_'+k:v for k,v in prior['topology'].items()},
            **{'initial_'+k:v for k,v in prior['initial_metrics'].items()}}
        assert set(['M0','M1','M2','M3','M4','M5','fixed','random'])<=set(methods)
        for policy in ('diagnostic','random'):
            name=record['condition']+'-'+policy
            full=read_json(root()/'runs'/name/'bank.json')
            assert digest({k:v for k,v in full.items() if k!='bank_hash'})==full['bank_hash']
            assert set(full['construction_partitions'])=={'fit','early','search'}
            bank=subbank(full,[k for k,c in full['candidates'].items() if c['ordinal']<=full['fixed_count']]) if record['resource']=='fixed' else full
            assert bank['cost']==cost(bank['candidates'])
            for candidate in bank['candidates'].values():
                graph=DAG.from_json(candidate['graph']);assert graph.d==m['d']
                assert max(len(graph.parents(j)) for j in range(graph.d))<=cfg['search']['max_indegree']
                assert len(candidate['fits'])==graph.d
                for j,fit in enumerate(candidate['fits']):
                    assert fit['node']==j and fit['parents']==list(graph.parents(j))
                    assert fit['canonical_seed']==int(fit['key'][:8],16)%(2**31-1)
            selection=read_json(root()/'runs'/(name+'-'+record['resource'])/'selection.json')
            assert selection['bank_hash']==bank['bank_hash'] and selection['identity']['calibration_hash']==m['partition_hashes']['calibration']
            assert selection['identity']['audit_hash']==m['partition_hashes']['audit']
            before=read_json(root()/'runs'/(name+'-'+record['resource'])/'before_audit.json')
            assert before['identity']==selection['identity']
            scores=selection['calibration_scores'];initial=bank['initial'];g0={'kind':'flow','graph':bank['candidates'][initial]['graph']}
            for value in scores.values():assert np.isclose(np.mean(value['environment_scores']),value['total'],atol=1e-8)
            base=np.asarray(scores[initial]['environment_scores'])
            selected_methods=selection['methods']
            for method,rho in ([('random',0)] if policy=='random' else [('M3',0),('M4',cfg['rho']),('rho0',0)]):
                changes={k:(1-rho)*np.mean(np.asarray(v['environment_scores'])-base)+rho*np.max(np.asarray(v['environment_scores'])-base) for k,v in scores.items()}
                best=min(changes,key=lambda k:(changes[k],k));chosen=best if changes[best]<=-cfg['search']['improvement'] else initial
                assert selected_methods[method]['selected_key']==chosen
            for method,row in selected_methods.items():
                audit=row['audit'];a,b=audit['initial'],audit['candidate']
                passed=b['sw1']<=cfg['search']['audit_w_factor']*a['sw1']+cfg['search']['audit_w_slack'] and b['nll']<=a['nll']+cfg['search']['audit_nll_slack']
                assert row['audit_pass']==passed and row['selected']==(row['before_audit'] if passed else g0)
                assert row['retained_initial']==(row['selected']==g0)
                assert before['candidates'][method]['spec']==row['before_audit']
                if not method.startswith('checkpoint_'):
                    assert row['cost']==bank['cost']
                    assert np.isclose(row['logical_seconds']-row['selection_seconds'],bank['logical_seconds'])
                if method in methods:assert row['selected']==methods[method]['selected']
            if policy=='diagnostic':
                assert methods['M3']['bank_hash']==methods['M4']['bank_hash']==methods['M5']['bank_hash']==bank['bank_hash']
                shortlist=[initial]+sorted((k for k in bank['candidates'] if k!=initial),key=lambda k:(bank['candidates'][k]['search']['total'],k))[:2]
                for method in ('M5','tau0','uniform'):
                    row=selected_methods[method];w=np.array(row['weights'])
                    assert row['shortlist']==shortlist and 1<=len(w)<=3 and w.min()>=0 and abs(w.sum()-1)<1e-10
                row=selected_methods['M5']
                weights.append({'scm':m['seed'],'d':m['d'],'profile':m['profile'],'family':m['family'],
                    'sensitivity':m.get('sensitivity','primary'),'corruption':record['prior']['corruption_fraction'],
                    'resource':record['resource'],'initial_weight_before_audit':row['weights'][0],
                    'audit_pass':row['audit_pass'],'retained':row['retained_initial'],
                    'components_before_audit':len(row['weights']),'bank_hash':bank['bank_hash']})
            banks[name+'-'+record['resource']]={'hash':bank['bank_hash'],'candidates':len(bank['candidates']),'parent_sets':bank['cost']['parent_sets']}
        records.append(record)
    pd.DataFrame(datasets.values()).sort_values(['d','profile','family','scm','budget']).to_csv(RESULTS/'datasets.csv',index=False,float_format='%.7g')
    pd.DataFrame(weights).to_csv(RESULTS/'mixture_weights.csv',index=False,float_format='%.7g')
    pd.DataFrame(priors.values()).sort_values(['d','profile','family','scm','budget','corruption']).to_csv(RESULTS/'priors.csv',index=False,float_format='%.7g')
    return records,{'datasets':len(datasets),'independent_scms':len({v['scm'] for v in datasets.values()}),'policy_conditions':len(records),'verified_banks':len(banks)}

def predictions(records):
    path=root()/'analysis/metrics-full.csv'
    if not path.exists():path=RESULTS/'metrics.csv'
    frame=pd.read_csv(path);assert 'endpoint' in frame
    index=['scm','budget','corruption','resource','method','endpoint'];assert not frame.duplicated(index).any()
    sample_count=0;generated_rows=0;target_hashes={};seen=set();mapped=0
    for record in records:
        task=record['task'];m=read_json(root()/record['data_folder']/'manifest.json');cfg=record['config']
        part=frame[(frame.scm==task['seed'])&(frame.budget==m['budget_per_target'])&(frame.corruption==record['prior']['corruption_fraction'])&(frame.resource==record['resource'])]
        assert set(part.method)==set(record['methods'])
        for method,method_rows in part.groupby('method'):
            assert set(method_rows.endpoint)=={'T1','T2','T3'} and method_rows.prediction_key.nunique()==1
            key=method_rows.iloc[0].prediction_key;folder=root()/'generated_samples'/key;value=read_json(folder/'metrics.json')
            assert value['identity']['spec']==record['methods'][method]['selected'] and value['identity']['data']==m['dataset_hash']
            for row in method_rows.itertuples():
                expected=aggregate([v for v in value['metrics'] if v['endpoint']==row.endpoint])
                for k,v in expected.items():
                    if v is None:assert pd.isna(getattr(row,k))
                    else:assert math.isfinite(v) and np.isclose(getattr(row,k),v,rtol=1e-7,atol=1e-9),(key,k)
                assert row.sw1>=0
                if method=='M0':assert pd.isna(row.nll) and pd.isna(row.harmful)
                if row.endpoint=='T2' and (method in ('M3','M4','M5','random') or method.startswith('checkpoint_')):
                    fixed=float(part[(part.method=='fixed')&(part.endpoint=='T2')].sw1.iloc[0])
                    assert row.harmful==int(row.sw1-fixed>max(.001,.05*fixed))
                mapped+=1
            if key in seen:continue
            seen.add(key);sample_path=folder/'samples.npz';assert file_hash(sample_path)==value['samples_sha256']
            with np.load(sample_path) as arrays:
                assert len(arrays.files)==3*len(m['seen_targets'])+1
                for name in arrays.files:
                    y=arrays[name];assert y.shape==(cfg['evaluation_samples'],task['d']) and np.isfinite(y).all()
                    generated_rows+=len(y);sample_count+=1
                    if name!='final-obs':
                        target=int(name.split('-do')[-1]);token=(m['dataset_hash'],name,target)
                        sha=hashlib.sha256(np.ascontiguousarray(y[:,target]).tobytes()).hexdigest()
                        if token in target_hashes:assert sha==target_hashes[token],'Unequal assignment draws'
                        else:target_hashes[token]=sha
    assert mapped==len(frame)
    return {'metric_rows':len(frame),'unique_predictions':len(seen),'model_environment_arrays':sample_count,
        'generated_observations':generated_rows,'assignment_streams':len(target_hashes),'full_metrics_sha256':file_hash(path)}

def main():
    global RESULTS
    parser=argparse.ArgumentParser();parser.add_argument('--predictions',action='store_true')
    parser.add_argument('--development',action='store_true');args=parser.parse_args()
    if args.development:
        assert not args.predictions
        destination=RESULTS/'pilot_integrity.json';pilots=read_json(RESULTS/'pilots.json')
        names=[p for pilot in pilots for record in pilot['records'] for p in record.values()]
        frozen={'records':{p:file_hash(root()/p) for p in names}}
        RESULTS=root()/'development_integrity';RESULTS.mkdir(exist_ok=True)
        records,counts=inputs_and_selection(frozen)
        value={'passed':True,**counts,'development_only':True,'source_sha256':file_hash(__file__)}
        atomic_json(destination,value);print(json.dumps(value,indent=2));return
    protocol=freeze_guard();frozen=read_json(RESULTS/'frozen_selections.json')
    assert frozen['protocol_sha256']==file_hash(RESULTS/'protocol.json')
    records,counts=inputs_and_selection(frozen)
    result={'passed':True,**counts,'incomplete_tasks':frozen['incomplete_tasks'],
        'scope':'CPU integrity audit; no fitting, model selection changes or new generated outcomes',
        'checks':['split hashes and disjoint IDs','training-only standardization','all five non-test intervention counts',
            'same immutable M3-M5 banks and full logical costs','canonical node/parent identities and indegree caps',
            'mean/robust calibration arithmetic','search-only mixture shortlist','one-time audit and fallback',
            'valid mixture simplex; predictive weights only'],'protocol_sha256':file_hash(RESULTS/'protocol.json')}
    if args.predictions:
        assert (RESULTS/'final_test_access.json').exists();result['predictions']=predictions(records)
    atomic_json(RESULTS/('execution_audit.json' if args.predictions else 'preselection_audit.json'),result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
