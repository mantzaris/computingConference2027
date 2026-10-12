"""Conditional refinement of the first retained v1 LLM proposal; not fresh discovery."""
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v2.application import Construction,variable_json_schema
from got_war.structural_programs import check_spec,valid_value
from got_war.budget import atomic_json


def main():
    c=Construction(ROOT);c.folder=c.run/'application/five_kings_refinement';c.folder.mkdir(exist_ok=True)
    c.semantic_compile_fallback='--semantic-compile-fallback' in sys.argv
    # Canonical first retained candidate, selected without its v2 outcomes or
    # path allocations. Both retained v1 Five Kings programs were equivalent.
    prior_path=c.folder/'prior_record.json'
    prior=json.loads(prior_path.read_text())['model']
    mapping={n['id']:('W' if n['id']==prior['outcome'] else 'X%02d'%(i+1)) for i,n in enumerate(prior['nodes'])}
    provenance={'variant':'prior_refinement','prior_record':'runs/campaign_20261012/application/five_kings/alternative_1.json',
        'version2_input_copy':str(prior_path.relative_to(ROOT)),
        'prior_record_sha256':hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        'selection':'First canonical retained v1 LLM proposal; no v2 outcomes or allocations used.',
        'scope':'Variables and dependencies initialize from an earlier LLM-generated proposal. Operational states/references are regenerated against the new transcript context, all nonroot mechanisms are newly proposed, and dependency retractions remain possible. This is conditional refinement, not successful fresh variable/dependency discovery.',
        'evidence_policy':'The prior is an unverified proposal, never retrieved evidence. No old equation, source score, or mechanism description enters generation.'}
    atomic_json(c.folder/'initialization.json',provenance)
    graph_file=c.folder/'graph.json'
    if not graph_file.exists():
        nodes=[]
        for old in prior['nodes']:
            ident=mapping[old['id']]
            proposal={k:old[k] for k in ('label','definition','type','values','bounds','observed','reference') if k in old}
            if ident=='W':proposal.update(label='Specified conflict outcome',definition=c.case['outcome'])
            context,ids=c.context(query=proposal['label']+' '+proposal['definition'],limit=12500)
            prompt=('Reassess and operationalize this earlier LLM variable proposal against the actual supplied television passages. '
                'The proposal is NOT evidence; do not fill gaps from model memory. No prior equation or mechanism is supplied. '
                'Return {"node":{"id":"'+ident+'","label":"short event label","definition":"precise operational meaning",'
                '"actor":"actor","type":"bool|category|int|float","values":["only if category"],"bounds":[0,1],'
                '"observed":1,"reference":0,"reference_meaning":"explicit comparison state",'
                '"event_time":"s01e01 or unknown","statement_time":"s01e01 or unknown",'
                '"proposition_kind":"narrative_fact|reported_claim|character_belief","segments":["actual supplied passage ID"]}}. '
                'You may revise domain/state/reference meanings when the source justifies that revision. '
                'An unspecified comparison placeholder is invalid: define a meaningful state in the declared domain. '
                'Separate the fact of a report/belief from the truth of its content. Do not treat an outcome manifestation as a necessary cause. '
                'The W variable means exactly the supplied Boolean conflict outcome. Do not change its horizon. '
                'Cite only passages whose text appears below. No causes, parents or equations are requested in this step.\nOUTCOME: '+c.case['outcome']+
                '\nUNVERIFIED PRIOR PROPOSAL:\n'+json.dumps(proposal)+'\nPASSAGES:\n'+context)
            def validate(response):
                n=response['node'];check_spec(n)
                if n['id']!=ident or not valid_value(n['observed'],n) or not valid_value(n['reference'],n):raise ValueError('Keep the requested ID and valid domain states')
                if not n.get('segments') or set(n['segments'])-set(ids):raise ValueError('Use actual supplied passage IDs only')
                if not n.get('definition') or not n.get('reference_meaning') or 'specific comparison state' in str(n.get('reference','')).lower():raise ValueError('A substantive definition and explicit reference are required')
                if ident=='W' and n['type']!='bool':raise ValueError('The specified outcome is Boolean')
                match=re.fullmatch(r's(\d+)e(\d+)',n.get('event_time','').lower())
                n['time']=100*int(match[1])+int(match[2]) if match else None
                if n['time'] is not None and n['time']>c.case['endpoint_code']:raise ValueError('Variable occurs after the supplied outcome horizon')
                n['prior_variable_id']=old['id'];return n
            node=c.artifact('prior_variable_'+ident,prompt,validate,1536,schema=variable_json_schema(ident,ids))
            nodes.append(node)
            atomic_json(c.folder/'variables_checkpoint.json',{'nodes':nodes,'initialization':provenance})
            print('PRIOR_VARIABLE',ident,flush=True)
        blueprint=c.audit_events({'outcome':'W','nodes':nodes,'initialization':provenance,
            'assumptions':[provenance['scope'],'Inherited dependencies remain unverified hypotheses; the new source audits can assign zero support.']})
        for node in blueprint['nodes']:
            old=next(n for n in prior['nodes'] if n['id']==node['prior_variable_id'])
            node['parents']=[mapping[p] for p in old['parents']]
            node['mechanism_hint']='Inherited LLM dependency hypothesis only; generate the function from the actual context and state every unresolved assumption.'
        blueprint['graph_proposal']={'parents':{n['id']:n['parents'] for n in blueprint['nodes']},
            'assumptions':['The earlier generated adjacency is a proposal for conditional refinement, not source evidence or a researcher-written causal graph.']}
        atomic_json(graph_file,blueprint)
    try:
        result=c.build(resume_graph=True)
        print('CONDITIONAL_REFINEMENT_DONE',len(result['records']),flush=True)
    except Exception as error:
        atomic_json(c.folder/'failure.json',{'error':type(error).__name__+': '+str(error),'at':time.time(),'initialization':provenance})
        raise


if __name__=='__main__':
    try:main()
    except Exception as error:
        config=json.loads((ROOT/'configs/budget_v2.json').read_text())
        folder=ROOT/'runs'/config['campaign_id']/'application/five_kings_refinement'
        if not (folder/'failure.json').exists():
            atomic_json(folder/'failure.json',{'error':type(error).__name__+': '+str(error),'at':time.time(),'variant':'prior_refinement'})
        raise
