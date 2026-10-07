#!/usr/bin/env python3
"""Independently audit saved selection arithmetic, banks and common costs."""
import argparse
import json
import numpy as np
from sem_update.phase2.runtime import root,RESULTS,freeze_guard,read_json,digest,atomic_json,file_hash

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args()
    protocol=freeze_guard();cfg=protocol['config'];rows=[];missing=[]
    for item in protocol['matrix']:
        complete=root()/'runs/datasets'/item['data_id']/'complete.json'
        if not complete.exists():missing.append(item['data_id']);continue
        for task in read_json(complete)['tasks']:
            bank=read_json(root()/task['diagnostic_bank_path'])
            assert digest({k:v for k,v in bank.items() if k!='bank_hash'})==bank['bank_hash']==task['diagnostic_bank_hash']
            assert set(bank['construction_partitions'])=={'fit','early','search'} and bank['immutable']
            initial=bank['initial'];methods=task['methods'];g0={'kind':'flow','graph':bank['candidates'][initial]['graph']}
            selection=read_json(root()/'runs'/(task['task_id']+'-selection')/'selection.json')
            scores=selection['calibration_scores'];baseline=np.asarray(scores[initial]['environment_scores'])
            for value in scores.values():
                assert np.isclose(np.mean(value['environment_scores']),value['total'],rtol=1e-6,atol=1e-5)
            for name,rho in [('M3',0.),('M4',cfg['rho']),('rho0',0.)]:
                changes={key:(1-rho)*np.mean(np.asarray(value['environment_scores'])-baseline)+
                         rho*np.max(np.asarray(value['environment_scores'])-baseline) for key,value in scores.items()}
                best=min(changes,key=lambda key:(changes[key],key))
                chosen=best if changes[best]<=-cfg['search']['improvement'] else initial
                assert methods[name]['selected_key']==chosen
            shortlist=[initial]+sorted((key for key in bank['candidates'] if key!=initial),
                key=lambda key:(bank['candidates'][key]['search']['total'],key))[:2]
            for name in ['M3','M4','M5','rho0','tau0','uniform']:
                method=methods[name]
                assert method['cost']==bank['cost'] and method['initial']==g0
                assert np.isclose(method['logical_seconds']-method['selection_seconds']-method['initialization_seconds'],bank['logical_seconds'])
                audit=method['audit'];base=audit['initial'];candidate=audit['candidate']
                passed=(candidate['sw1']<=cfg['search']['audit_w_factor']*base['sw1']+cfg['search']['audit_w_slack'] and
                        candidate['nll']<=base['nll']+cfg['search']['audit_nll_slack'])
                assert method['audit_pass']==passed
                assert method['selected']==(method['before_audit'] if passed else g0)
            for name in ['M5','tau0','uniform']:
                method=methods[name];weights=np.asarray(method['weights'])
                assert method['shortlist']==shortlist and len(weights)<=3
                assert weights.min()>=0. and abs(weights.sum()-1)<1e-10
            assert methods['rho0']['selected']==methods['M3']['selected']
            for path_key in ['random_bank_path','llm_bank_path']:
                if not task.get(path_key):continue
                other=read_json(root()/task[path_key])
                assert digest({k:v for k,v in other.items() if k!='bank_hash'})==other['bank_hash']
                assert other['initial']==initial
            rows.append({'task_id':task['task_id'],'bank_sha256':file_hash(root()/task['diagnostic_bank_path']),
                'bank_hash':bank['bank_hash'],'candidates':len(bank['candidates']),
                'identical_fitted_bank_and_logical_cost':True,'selection_arithmetic_and_audit_verified':True,
                'calibration_blind_shortlist_verified':True})
    if missing and not args.partial:raise RuntimeError('Incomplete datasets: '+str(missing))
    result={'complete':not missing,'verified_settings':len(rows),'missing_datasets':missing,
        'final_outcomes_loaded':False,'protocol_hash':protocol['protocol_hash'],'checks':rows}
    atomic_json(RESULTS/('selection_audit_partial.json' if args.partial else 'selection_audit.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))

if __name__=='__main__':main()
