"""Offline numerical verification of version-2 records, never inference."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.budget import atomic_json
from got_war.structural_programs import SCM
from got_war.v2.runtime import paths,application_record
from got_war.v2.mechanisms import compatible_family,outcome_sets,inspect_mechanism
from got_war.v2.paths import explain_query,game_report


def verify(root):
    root,run,result=paths(root);frozen=json.loads((root/'configs/v2_frozen_protocol.json').read_text())
    failures=[]
    changed=[name for name,digest in frozen['files'].items() if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
    if changed:failures.append({'frozen_files_changed':changed})
    casefile=run/'benchmark_cases.jsonl'
    if hashlib.sha256(casefile.read_bytes()).hexdigest()!=frozen['design']['sha256']:failures.append('Frozen benchmark manifest changed')
    cases=[json.loads(line) for line in casefile.read_text().splitlines()];counts={};numerical=0;accepted=0;rejected=0;oracle_queries=0
    for case in cases:
        supplied=copy.deepcopy(case['gold'])
        for node in supplied['nodes']:node['unknown']=node['id'] in case['hidden_nodes']
        oracle=compatible_family(supplied);answers=outcome_sets(oracle['models'],case['queries'])
        if not oracle['summary']['exhaustive'] or any(a['values']!=q['gold_possible'] for a,q in zip(answers,case['queries'])):
            failures.append({'oracle_family_execution':case['id']})
        true=SCM(case['gold'])
        if any(true.solve(interventions=q['do'])[q['target']]!=q['generating_outcome'] for q in case['queries']):
            failures.append({'oracle_generating_execution':case['id']})
        oracle_queries+=len(case['queries'])
        record_path=run/'benchmark'/(case['id']+'.json')
        if not record_path.exists():failures.append({'missing_record':case['id']});continue
        record=json.loads(record_path.read_text());counts[case['split']]=counts.get(case['split'],0)+bool(record.get('completed'))
        if not record.get('completed'):failures.append({'incomplete':case['id']})
        if not record.get('model'):
            rejected+=1
            if not record.get('synthesis_attempts') or not record['methods'].get('B2',{}).get('error'):failures.append({'unexplained_rejection':case['id']})
            continue
        accepted+=1;model=record['model'];scm=SCM(model);family=compatible_family(model)
        if record['methods']['B2']['answers']!=outcome_sets([model],case['queries']):failures.append({'single_execution':case['id']})
        if record['methods'].get('ALT',{}).get('answers')!=outcome_sets(family['models'],case['queries']):failures.append({'family_execution':case['id']})
        if record.get('trace'):
            q=next(q for q in case['queries'] if q['id']==record['explanation_query'])
            trace=explain_query(model,q,family['models'])
            if trace['attribution']!=record['trace']['attribution']:failures.append({'coalition_execution':case['id']})
            numerical+=1
        if not all(n['description']==inspect_mechanism(scm,n['id'])['derived_description'] for n in model['nodes']):failures.append({'description_behavior':case['id']})
    apppath=application_record(root,run);app=json.loads(apppath.read_text());appchecks=[]
    for record in app['records']:
        model=record['model'];scm=SCM(model)
        agreement=game_report(scm,record['selection']['paths'])==record['attribution']
        description=all(n['description']==inspect_mechanism(scm,n['id'])['derived_description'] for n in model['nodes'])
        appchecks.append({'model':model['id'],'coalitions_reproduce':agreement,'descriptions_match':description})
        if not agreement or not description:failures.append({'application_execution':model['id']})
    if outcome_sets([r['model'] for r in app['records']],app['queries'])!=app['outcome_sets']:failures.append('Application outcome sets differ')
    report={'version':2,'offline_only':True,'completed_by_split':counts,'accepted_syntheses':accepted,
        'rejected_syntheses_retained':rejected,'controlled_coalition_records_reproduced':numerical,
        'oracle_family_and_generating_queries_reexecuted':oracle_queries,
        'application_record':str(apppath.relative_to(root)),'application':appchecks,
        'frozen_hashes_match':not changed,'failures':failures,'passed':not failures,
        'limits':'Numerical and provenance consistency only. No independent source entailment, historical counterfactual truth, reader benefit or human review is established.'}
    atomic_json(result/'verification.json',report)
    if failures:raise RuntimeError('Verification failures: '+json.dumps(failures))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    print(json.dumps(verify(args.root),indent=2))
