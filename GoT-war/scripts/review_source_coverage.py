"""One bounded source-coverage review per undersized application schema."""
import copy,json
from pathlib import Path
from got_war.generation import Generator
from got_war.fact_pipeline import artifact
from got_war.construction import variable_error
from got_war.ordered_graph import episode
from got_war.spans import align_quote,locate_excerpt
from got_war.structural_programs import InvalidModel
from got_war.budget import atomic_json

gen=Generator('.')
for folder in sorted((gen.run/'application').iterdir()):
    files=sorted(folder.glob('alternative_*.json'))
    if not files or (folder/'coverage_supplement.json').exists():continue
    record=json.loads(files[0].read_text())
    if len(record['model']['nodes'])>=10:continue
    packet=json.loads((gen.root/'.private/packets'/(folder.name+'.json')).read_text())
    segments={s['id']:s for s in packet['segments']}
    model=[{k:n.get(k) for k in ('id','label','definition','parents','time')} for n in record['model']['nodes']]
    prompt='Critically review source coverage of this candidate explanatory model against the frozen documents. Identify at most FOUR documented missing events or mediators that would materially improve its causal account of the specified outcome. Do not add character names, duplicate the current variables, invent a common cause, restate the outcome, or fill a node quota. Prefer explicit causal steps or reported decisions/resources that the model omits; distinguish event support from an inferred dependence. If no grounded addition exists, return an empty list. Return {"new_variables":[{"label":"short faithful label","definition":"precise event, <=20 words","type":"bool","observed":1,"reference":0,"reference_meaning":"specific alternative assumption","actor":"documented actor","status":"established_event OR character_report OR character_belief OR disputed_account","segment_id":"provided source ID","quote":"EXACT contiguous 2-7 word span","episode_id":"s00e00","coverage_reason":"specific documented explanatory gap, not mere topical relevance"}],"limitations":["remaining evidence gaps"]}. Category states require values (>=2 distinct strings), with observed/reference strings from that list. Numeric states require bounds and a source-grounded measurement_rule. Do not supply an equation or a desired graph; dependencies will be discovered separately. Use the actual document, never memory.\nOUTCOME: '+record['case']['outcome']+'\nCURRENT MODEL: '+json.dumps(model)+'\nFROZEN DOCUMENTS:\n'+packet['packet_text']
    def check(response):
        rows=response['new_variables']
        if not isinstance(rows,list) or len(rows)>4:raise InvalidModel('At most four source-grounded additions, or none')
        result=[];rejected=[]
        for i,n in enumerate(rows):
            n=copy.deepcopy(n);n['id']='c%02d'%i
            ep=episode(n['episode_id'])
            if ep not in packet['case']['source_episodes']:raise InvalidModel('Event time must be traceable to the supplied packet')
            n['time']=int(ep[1:3])*100+int(ep[4:6]);sid=n['segment_id']
            if sid not in segments:raise InvalidModel('Unknown source paragraph')
            aligned=align_quote(n.get('quote',''),segments[sid]['text'])
            if aligned is None:aligned=locate_excerpt(n['definition'],n.get('quote',''),segments[sid]['text'])
            if aligned is None:
                rejected.append({'variable':n,'error':'No traceable short span in the claimed source paragraph; candidate excluded.'})
                continue
            n['citations']=[dict(segment_id=sid,**aligned)]
            error=variable_error(n,segments)
            if error:raise InvalidModel(error)
            if n['definition'] in {x['definition'] for x in record['model']['nodes']}:raise InvalidModel('Do not duplicate an existing event')
            n['event_assessment']='partial';n['event_assessment_reason']='Proposed source-coverage supplement; separate full-paragraph semantic review required. Any navigation excerpt is a source pointer, not a verified supporting quotation.'
            result.append(n)
        atomic_json(folder/'coverage_rejections.json',rejected)
        return result
    try:
        nodes=artifact(gen,folder/'coverage_review.json','application_coverage_review',prompt,check,4096)
        atomic_json(folder/'coverage_supplement.json',{'packet_sha256':packet['packet_sha256'],'reviewed_model':record['model']['id'],'variables':nodes,'protocol':'one source-coverage review, at most two repairs; no target node count supplied in prompt','status':'unvalidated supplementary claims; pass the standard source audit before use'})
        print(folder.name,'coverage candidates',len(nodes),flush=True)
    except Exception as exc:
        atomic_json(folder/'coverage_review_failure.json',{'error':str(exc),'no_researcher_supplied_events':True});print(folder.name,'coverage review failed',str(exc),flush=True)
