"""Verify the end-to-end development gate and freeze inference before test access."""
import hashlib
import copy
import json
from pathlib import Path
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.budget import atomic_json
from got_war.structural_programs import SCM
from got_war.v2.runtime import paths,application_record
from got_war.v2.mechanisms import compatible_family,inspect_mechanism,outcome_sets
from got_war.v2.paths import explain_query
from got_war.v2.analysis import structural_scores


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def gate():
    root,run,result=paths(ROOT)
    cases=[json.loads(x) for x in (run/'benchmark_cases.jsonl').read_text().splitlines()]
    cases=[c for c in cases if c['split']=='development' and c['size']==8 and c['seed']%100==0]
    checks=[];passed=True
    for case in cases:
        record=json.loads((run/'benchmark'/(case['id']+'.json')).read_text())
        model=record.get('model');row={'id':case['id'],'condition':case['condition'],'valid_model':bool(model)}
        oracle=copy.deepcopy(case['gold'])
        for n in oracle['nodes']:n['unknown']=n['id'] in case['hidden_nodes']
        oracle_family=compatible_family(oracle)
        oracle_answers=outcome_sets(oracle_family['models'],case['queries'])
        row['controlled_information_configuration_verified']=all(a['values']==q['gold_possible'] for a,q in zip(oracle_answers,case['queries'])) and oracle_family['summary']['exhaustive']
        if model:
            scm=SCM(model);family=compatible_family(model)
            row.update(function_family_exhaustive=family['summary']['exhaustive'],
                family_size=len(family['models']),
                descriptions_match_all_tables=all(n['description']==inspect_mechanism(scm,n['id'])['derived_description'] for n in model['nodes']),
                outcome_sets_reproduce=record['methods']['ALT']['answers']==outcome_sets(family['models'],case['queries']),
                known_function_agreement=structural_scores(record,case)['known_function_agreement'])
            q=next(q for q in case['queries'] if q['id']==record['explanation_query'])
            trace=explain_query(model,q,family['models'])
            row['coalition_values_reproduce']=trace['attribution']==record['trace']['attribution']
            e=record.get('explanation',{})
            row['actual_sentence_ids_reviewed']=sorted(r['sentence_id'] for r in e.get('review',{}).get('reviews',[]))==sorted(s['id'] for s in e.get('sentences',[])) and bool(e.get('sentences'))
            row['explanation_displayable']=e.get('displayable',False)
        row['failed_synthesis_rejected_and_retained']=not model and bool(record.get('synthesis_attempts')) and bool(record['methods']['B2'].get('error'))
        row['technical_pass']=row['controlled_information_configuration_verified'] and (row['failed_synthesis_rejected_and_retained'] or all(row.get(k) for k in ('function_family_exhaustive','descriptions_match_all_tables','outcome_sets_reproduce','coalition_values_reproduce','actual_sentence_ids_reviewed')))
        checks.append(row);passed &= row['technical_pass']
    app_path=application_record(root,run);app=json.loads(app_path.read_text())
    a=app['records'][0];model=a['model'];scm=SCM(model)
    from got_war.v2.paths import game_report
    application={'variables':len(model['nodes']),'edges':scm.graph.number_of_edges(),'models':len(app['records']),
        'record':str(app_path.relative_to(root)), 'construction_context':app.get('construction_context',{'variant':'fresh'}),
        'fresh_source_construction_succeeded':(run/'application/five_kings/final.json').exists(),
        'conditional_initialization_used':app.get('construction_context',{}).get('variant')=='prior_refinement',
        'ten_node_reporting_target_met':len(model['nodes'])>=10,
        'coalition_values_reproduce':game_report(scm,a['selection']['paths'])==a['attribution'],
        'descriptions_match_all_tables':all(n['description']==inspect_mechanism(SCM(r['model']),n['id'])['derived_description'] for r in app['records'] for n in r['model']['nodes']),
        'actual_sentence_ids_reviewed':sorted(r['sentence_id'] for r in app['explanation'].get('review',{}).get('reviews',[]))==sorted(s['id'] for s in app['explanation'].get('sentences',[])) and bool(app['explanation'].get('sentences')),
        'explanation_displayable':app['explanation'].get('displayable',False),
        'source_validity':'Conditional on automated contextual review; independent researcher adjudication pending.'}
    passed &= application['coalition_values_reproduce'] and application['descriptions_match_all_tables'] and application['actual_sentence_ids_reviewed']
    supervision=json.loads((run/'supervision_probe.json').read_text())
    passed &= all(supervision.get(k) is True for k in ('registered_identity_nonnull','deadline_enforced','owned_stopped','unregistered_test_child_survived','artifact_preserved'))
    report=json.loads((result/'pilot_gate.json').read_text())
    report.update(status=('technical_gate_passed_with_synthesis_failure' if any(not r['valid_model'] for r in checks) else 'technical_gate_passed') if passed else 'gate_failed',benchmark=checks,application=application,
        all_benchmark_conditions_synthesized=all(r['valid_model'] for r in checks),
        supervision=supervision,checked_at=datetime.now(timezone.utc).isoformat(),
        interpretation='This gate checks the controlled information configurations using the declared oracle family, rejection/retention of invalid synthesis, numerical reproduction of accepted models and actual sentence review. Failed LLM synthesis is an experimental failure in the primary denominator, not a passing end-to-end example. It does not certify source entailment.')
    atomic_json(result/'pilot_gate.json',report)
    if not passed:raise RuntimeError('Development gate failed; inspect results/v2/pilot_gate.json')
    return report


def freeze():
    root,run,result=paths(ROOT);destination=ROOT/'configs/v2_frozen_protocol.json'
    if destination.exists():raise RuntimeError('Protocol already frozen; never overwrite it')
    gate_report=gate();design=json.loads((run/'benchmark_design.json').read_text())
    budget=json.loads((ROOT/'configs/budget_v2.json').read_text())
    if not budget.get('output_token_ceiling'):raise RuntimeError('Token allowance must be measured before freezing')
    if any(json.loads(p.read_text()).get('split')=='test' for p in (run/'benchmark').glob('*.json')):raise RuntimeError('Cannot claim pretest freeze after test inference')
    files=[p for p in (ROOT/'src/got_war/v2').glob('*.py') if p.name not in ('figures.py','reporting.py')]+[ROOT/'src/got_war'/name for name in
        ('structural_programs.py','attribution.py','budget.py','generation.py','experiments.py','benchmark.py')]
    selected=application_record(root,run)
    atomic_json(ROOT/'configs/application_selection_v2.json',{'record':str(selected.relative_to(root)),
        'construction_context':gate_report['application']['construction_context'],
        'selection':'Fresh completion preferred; otherwise separately labeled conditional refinement. No selection by outcomes, attribution or source scores.',
        'record_sha256_at_freeze':sha(selected)})
    files += [ROOT/'prompts/ast_contract.txt',ROOT/'configs/models.json',ROOT/'configs/application_v2.json',ROOT/'configs/budget_v2.json',ROOT/'configs/application_selection_v2.json']
    files += [ROOT/name for name in ('docs/V2_PROTOCOL.md','docs/V2_METHODOLOGY.md',
        'scripts/v2_refine_prior.py','scripts/v2_sources.py','scripts/v2_launch_benchmark.py','scripts/v2_gate_refresh.py','scripts/v2_freeze.py')]
    manifest={'version':2,'frozen_at':datetime.now(timezone.utc).isoformat(),'campaign_id':budget['campaign_id'],
        'design':design,'budget':budget,'gate_sha256':sha(result/'pilot_gate.json'),
        'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},
        'model':json.loads((ROOT/'configs/models.json').read_text()),
        'inference':{'seeds':[2701],'temperature':.2,'top_p':.8,'synthesis_max_tokens':4096,'baseline_max_tokens':2048,'max_repairs':2,
            'repair':'At most two repairs: one local LLM node-replacement repair, then one fresh reconstruction. Original record and candidate factual-row diagnostics only; no gold rules or answers.',
            'graph_baseline':'Generated adjacency may remain usable when expression validation fails; no equations are exposed to B1.',
            'family':'Joint finite function enumeration; max 512 global candidates, max 256 local tables; report exhaustive versus bounded coverage.',
            'attribution':'Exact shared-edge coalitions, at most eight selected paths; explicit factual edge references for intervention traces.',
            'explanation_query':'case generating seed modulo query count, chosen independently of method outputs'},
        'analysis':{'unit':'Independent generating SCM','bootstrap_seed':271828,'bootstrap_replicates':5000,
            'primary_denominator':'All 72 test SCMs, including failed synthesis; questions remain repeated measurements.',
            'strata':['complete','incomplete','missing_intermediate','missing_outcome','multiple_missing','identified_changed','identified_unchanged','underidentified'],
            'metrics':['identified intervention accuracy','changed accuracy','unchanged accuracy','appropriate uncertainty','exact outcome set','unsupported confident answers','synthesis/repair success','known-function agreement','controlled evidence grounding','source nDCG@5','explanation numeric/ID checks','same-model review','reviewer controls','runtime/tokens/failures'],
            'source_relevance':design['source_relevance'],'conditional_analysis':'Successful synthesis only is secondary.',
            'paired_comparisons':['B1-B0','B2-B0','ALT-B2','FULL-B0','FULL-CARRY','FULL rank versus B0/B1/UNIFORM'],
            'stopping':'Complete fixed design; no significance-seeking continuation. Optional second model and extra seeds deferred.'},
        'application_status':gate_report['application']['construction_context'],
        'application_limits':'Aligned local alternatives are sensitivity cases, not posterior samples. No synthetic validation of literary claims.'}
    atomic_json(destination,manifest)
    return {'path':str(destination.relative_to(ROOT)),'sha256':sha(destination),'gate':gate_report['status']}


if __name__=='__main__':
    print(json.dumps(gate() if '--gate-only' in sys.argv else freeze(),indent=2))
