"""Recheck fixed accepted models and repair only their explanation presentation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.budget import atomic_json
from got_war.v2.runtime import paths,V2Generator,application_record
from got_war.v2.mechanisms import compatible_family,outcome_sets
from got_war.v2.paths import explain_query,game_report,edge_support
from got_war.v2.explanations import generate,reviewer_controls
from got_war.structural_programs import SCM
from got_war.attribution import evidence_priority


def main(include_app=False):
    root,run,result=paths(ROOT);gen=V2Generator(root);changed=[]
    cases={c['id']:c for c in map(json.loads,(run/'benchmark_cases.jsonl').read_text().splitlines())}
    for f in sorted((run/'benchmark').glob('*.json')):
        record=json.loads(f.read_text());case=cases[record['id']]
        if case['split']!='development' or not record.get('model'):continue
        backup=run/'pilot_trace_before_context'/f.name
        if not backup.exists():atomic_json(backup,record)
        start=time.time();model=record['model'];family=compatible_family(model)
        assert outcome_sets(family['models'],case['queries'])==record['methods']['ALT']['answers']
        q=next(q for q in case['queries'] if q['id']==record['explanation_query'])
        trace=explain_query(model,q,family['models'])
        assert trace['attribution']['phi']==record['trace']['attribution']['phi']
        trace['source_context']=case['narrative']
        trace['source_review_scope']='Complete explicit controlled rule record; no hidden generating equation or gold query answer.'
        record['trace']=trace;record['explanation']=generate(gen,trace)
        record['reviewer_controls']=reviewer_controls(gen,trace)
        record['methods']['FULL'].update(ranked_sources=[s['segment_id'] for s in trace['evidence_priority']['segments'] if s['priority']>0],ranking_available=trace['ranking_available'])
        record['derived_trace_revision']={'primary_answers_unchanged':True,'attribution_values_unchanged':True,
            'reason':'Actual source context and actual-sentence splitting added to explanation review; exact coalition diagnostic and description consistency rechecked.',
            'seconds':time.time()-start}
        atomic_json(f,record);changed.append(record['id'])
        print('REFRESHED',record['id'],'displayable',record['explanation']['displayable'],flush=True)
    if include_app:
        f=application_record(root,run);folder=f.parent;app=json.loads(f.read_text())
        backup=folder/'final_before_trace_review.json'
        if not backup.exists():atomic_json(backup,app)
        packet=json.loads((root/'.private/v2/five_kings_packet.json').read_text())
        clusters={s['id']:s['dependence_cluster'] for s in packet['segments']}
        for r in app['records']:
            scm=SCM(r['model']);game=game_report(scm,r['selection']['paths'])
            assert game['phi']==r['attribution']['phi']
            r['attribution']=game;r['edge_evidence']=edge_support(r['model'])
            r['evidence_priority']=evidence_priority(r['selection']['paths'],game,r['edge_evidence'],clusters)
            r['ranking_available']=any(s['priority']>0 for s in r['evidence_priority']['segments'])
        trace=explain_query(app['records'][0]['model'],app['trace']['query'],[r['model'] for r in app['records']])
        context=json.loads((folder/'explanation_context.private.json').read_text())['source_context']
        trace.update(source_context=context,source_context_private=True,
            source_review_scope='Bounded actual passage context for selected paths; missing support remains unverifiable. Same-model review; researcher adjudication pending.')
        app['explanation']=generate(gen,trace,2801);app['reviewer_controls']=reviewer_controls(gen,trace,2801)
        trace['source_context_sha256']=hashlib.sha256(trace.pop('source_context').encode()).hexdigest()
        app['trace']=trace;app['derived_trace_revision']='No equation, background or intervention outcome changed; exact diagnostics and actual-context sentence review updated before protocol freeze.'
        atomic_json(f,app);changed.append('five_kings')
        print('REFRESHED flagship','displayable',app['explanation']['displayable'],flush=True)
    atomic_json(run/'gate_recompute.json',{'updated':changed,'no_structural_model_changes':True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--include-app',action='store_true');a=p.parse_args();main(a.include_app)
