"""Convert LLM-identified story episodes into one consistent time unit."""
import json,re
from .budget import atomic_json
from .structural_programs import InvalidModel


def annotate_times(gen,packet,nodes):
    file=gen.run/'application'/packet['case']['id']/'time_annotations.json'
    variables=[{k:n.get(k) for k in ('id','definition','status','story_time_basis','citations')} for n in nodes]
    allowed={s['source_id'] for s in packet['segments']}
    prompt='Resolve STORY EVENT time for each variable from the frozen documents. Earlier generated numeric ranks mixed incompatible units and must be ignored. Return {"variables":[{"id":"unchanged variable ID","event_episode":"s01e01 OR null","retrospective":false,"basis":"specific documentary basis or why unresolved"}]}. Episode IDs must use sNN eNN without a space, for example s01e01. Use the episode in which the event occurs, not the episode in which somebody later reports it. For a knowledge/report variable, use when the knowledge/report occurs. Use null when event timing is not established. For outcome W use the observation horizon in the exact outcome question, distinguishing onset from later commentary. No causes or parent sets are requested.\nOUTCOME: '+packet['case']['outcome']+'\nVARIABLES: '+json.dumps(variables)+'\nFROZEN PACKET:\n'+packet['packet_text']
    for attempt in range(3):
        response=json.loads(file.read_text()) if attempt==0 and file.exists() else gen.call('application_episode_times_v5' if not attempt else 'application_episode_times_repair_v5',prompt,3072,2027+attempt,thinking=True)
        try:
            rows=response['variables'];mapping={r['id']:r for r in rows}
            if set(mapping)!={n['id'] for n in nodes} or len(rows)!=len(nodes):raise InvalidModel('Return each variable exactly once')
            for node in nodes:
                annotation=mapping[node['id']];episode=annotation.get('event_episode')
                rank=None
                if episode is not None:
                    match=re.fullmatch(r's(\d{1,2})e(\d{1,2})',str(episode).lower())
                    if not match:raise InvalidModel('Invalid episode identifier for '+node['id'])
                    season,number=map(int,match.groups())
                    if not 1<=season<=8 or not 1<=number<=10:raise InvalidModel('Episode outside the declared television continuity')
                    rank=100*season+number
                    annotation['canonical_episode']='s%02de%02d'%(season,number)
                    if annotation['canonical_episode'] not in allowed:raise InvalidModel('Episode is not present in the frozen packet for '+node['id']+'; use null for unresolved retrospective timing')
                node['generated_time_before_unit_normalization']=node['time']
                node['time']=rank;node['story_time_annotation']=annotation
            atomic_json(file,response);return nodes
        except Exception as e:
            atomic_json(file.with_name('time_annotation_failed_%d.json'%attempt),{'response':response,'error':str(e)})
            if attempt==2:raise
            prompt=prompt.split('\nREPAIR:')[0]+'\nREPAIR: '+str(e)+'\nReturn valid episode strings or null, never numeric ranks.'
