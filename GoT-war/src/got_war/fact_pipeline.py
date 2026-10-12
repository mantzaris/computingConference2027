"""Source-first application development protocol with bounded, recorded repairs.

The model selects events and mechanisms. Deterministic operations only bind IDs,
check source/temporal contracts, and remove context outside the outcome ancestry.
This protocol does not alter the frozen controlled benchmark.
"""
import copy,hashlib,json,re
import networkx as nx
from .budget import atomic_json
from .construction import variable_error
from .spans import align_quote
from .structural_programs import InvalidModel


def artifact(gen,path,role,prompt,check,tokens=4096,thinking=True):
    base=prompt
    for attempt in range(3):
        response=None;exhausted_replay=False
        try:
            replay=sorted(path.parent.glob(path.stem+'_failed_*.json'))
            previous=json.loads(replay[-1].read_text()).get('response') if replay else None
            if attempt==0 and path.exists():response=json.loads(path.read_text())
            elif attempt==0 and role in ('application_facts_v6','application_coverage_review','application_final_source_review') and previous is not None:
                response=previous;exhausted_replay=any(p.stem.endswith('_failed_2') for p in replay)
            else:response=gen.call(role,prompt,tokens,2027+attempt,thinking=thinking)
            value=check(copy.deepcopy(response))
            atomic_json(path,response)
            return value
        except Exception as exc:
            if exhausted_replay:
                atomic_json(path.with_name(path.stem+'_replay_diagnostic.json'),{'error':str(exc),'response':response,'additional_generation_permitted':False})
                raise
            atomic_json(path.with_name(path.stem+'_failed_%d.json'%attempt),{'response':response,'error':str(exc)})
            if attempt==2:raise
            prompt=base+'\nREPAIR DIAGNOSTIC: '+str(exc)+'\nPREVIOUS JSON: '+json.dumps(response)+'\nCorrect this artifact using only the supplied documents.'


def build(gen,packet):
    from .application import cite_nodes
    folder=gen.run/'application'/packet['case']['id'];folder.mkdir(parents=True,exist_ok=True)
    dest=folder/'blueprint.json'
    if dest.exists():return json.loads(dest.read_text())
    segments={s['id']:s for s in packet['segments']};inventory=[]
    for start in range(0,len(packet['segments']),6):
        batch=packet['segments'][start:start+6]
        prompt='Extract 2-6 distinct SOURCE-ENTAILED events, decisions, resources, or constraints in these paragraphs that could be relevant to explaining the specified campaign. Select substantive claims; do not fill a quota. Check the exact actor, action, object, negation, and whether a claim is only reported or believed. Do not infer an event from a related name. Do not use outside knowledge. Do not yet invent causal edges. Keep each definition at most 20 words and include a 2-7 word contiguous exact source quotation. Use Boolean states for events only when appropriate; category states or measured numbers are allowed when warranted. Return {"variables":[{"label":"short event name","definition":"precise documented fact","type":"bool","observed":1,"reference":0,"reference_meaning":"specific comparison state","actor":"actor","status":"established_event OR character_report OR character_belief OR disputed_account","segment_id":"exact provided ID","quote":"exact short source span","episode_id":"s00e00 of the EVENT, or null if unknown"}]}. For category include values; for numeric include bounds and source-grounded measurement_rule. Reference states are assumptions, not claims about what happened. Do not include the whole campaign outcome as a candidate cause.\nOUTCOME: '+packet['case']['outcome']+'\nPASSAGES:\n'+'\n'.join('['+s['id']+'] '+s['text'] for s in batch)
        def check(response):
            rows=response['variables']
            if not 0<=len(rows)<=8:raise InvalidModel('At most eight distinct claims per chunk')
            result=[];rejected=[]
            for i,n in enumerate(rows):
                try:
                    n['id']='e%02d_%d'%(start,i)
                    sid=n.get('segment_id');ep=n.get('episode_id')
                    if sid not in {s['id'] for s in batch}:raise InvalidModel('Use a segment from this chunk')
                    if ep is not None and not re.fullmatch(r's\d\de\d\d',ep):raise InvalidModel('Episode identifier format')
                    if ep is not None and ep not in packet['case']['source_episodes']:raise InvalidModel('Event episode absent from packet; use null for unknown retrospective time')
                    n['time']=int(ep[1:3])*100+int(ep[4:6]) if ep else None
                    aligned=align_quote(n.get('quote',''),segments[sid]['text'])
                    if aligned is None:raise InvalidModel('Quotation must be copied exactly, not paraphrased: '+n['label'])
                    n['citations']=[dict(segment_id=sid,**aligned)]
                    if n.get('type')=='bool' and n.get('observed') in (0,1) and 'reference' not in n:
                        n['original_reference_meaning']=n.get('reference_meaning')
                        n['reference']=1-n['observed']
                        n['reference_meaning']='Declared comparison assumption: '+('absence' if n['observed']==1 else 'presence')+' of the Boolean event "'+n['definition']+'"'
                        n['reference_policy']='Missing binary reference supplied by the declared complement-of-observation policy; not an extracted historical claim.'
                    error=variable_error(dict(n,time=n['time'] or 0),segments)
                    if error and any(term in error for term in ('categorical domain','Observed/reference','Invalid bounds','Integer bounds','Missing reference')):
                        original=copy.deepcopy(n)
                        state_prompt='Repair ONLY the state schema of this already extracted source event. Keep its event meaning unchanged. Return fields type, observed, reference, reference_meaning, and values for a category or bounds plus measurement_rule for a number. A category requires at least TWO distinct STRING values and observed/reference must be strings in that list (never 0/1 unless the type is bool). A Boolean event uses 0/1; choose the appropriate type from the evidence, not by default. Numeric states need a documented measurement and numeric bounds. The reference is a clearly labeled comparison assumption, not another factual observation. Do not return a causal graph or equation.\nDIAGNOSTIC: '+error+'\nEXTRACTED EVENT: '+json.dumps(n)+'\nACTUAL SOURCE: '+segments[sid]['text']
                        def state_check(response):
                            candidate=copy.deepcopy(original)
                            for key in ('type','observed','reference','reference_meaning','values','bounds','measurement_rule'):
                                if key in response:candidate[key]=response[key]
                            problem=variable_error(dict(candidate,time=candidate['time'] or 0),segments)
                            if problem:raise InvalidModel(problem+'; categorical values must be >=2 strings, with observed/reference from that exact list')
                            return candidate
                        key=hashlib.sha256(state_prompt.encode()).hexdigest()[:12]
                        n=artifact(gen,folder/('state_schema_'+n['id']+'_'+key+'.json'),'application_state_schema',state_prompt,state_check,1024,False)
                        n['state_schema_provenance']='GPU-generated local type/state repair; source event and citation unchanged.'
                        error=None
                    if error:raise InvalidModel(error)
                    n['event_assessment']='supported';n['event_assessment_reason']='Source-bounded generated extraction; independent entailment review pending.'
                    result.append(n)
                except (InvalidModel,KeyError,TypeError) as exc:rejected.append({'variable':n,'error':str(exc)})
            atomic_json(folder/('fact_rejections_%02d.json'%start),rejected)
            return result
        inventory.extend(artifact(gen,folder/('facts_%02d.json'%start),'application_facts_v6',prompt,check))
    supplement=folder/'coverage_supplement.json'
    if supplement.exists():
        extra=json.loads(supplement.read_text())
        if extra['packet_sha256']!=packet['packet_sha256']:raise InvalidModel('Coverage supplement must use the same frozen packet')
        inventory.extend(copy.deepcopy(extra['variables']))
    # Audit each proposed event against its actual paragraph before graph selection.
    audited=[]
    for start in range(0,len(inventory),5):
        batch=inventory[start:start+5]
        prompt='Audit these extracted claims against the attached passages. A matching name does not entail the claim. Return {"audits":[{"id":"unchanged","assessment":"supported OR partial OR unsupported","reason":"specific actor/action/time check","corrected_label":"faithful short label","corrected_definition":"faithful same-event definition"}]}. Do not silently interpret home as a named place or inferred intentions as observed actions. A partial or unsupported event will be excluded before causal modeling. Correct minor wording only; do not replace the event with a different one.\n'+json.dumps([{'claim':n,'passage':segments[n['segment_id']]['text']} for n in batch])
        def check(response):
            audits=response['audits']
            if {a['id'] for a in audits}!={n['id'] for n in batch}:raise InvalidModel('Return every claim ID exactly once')
            if any(a.get('assessment') not in ('supported','partial','unsupported') for a in audits):raise InvalidModel('Invalid audit classification')
            return audits
        input_hash=hashlib.sha256(prompt.encode()).hexdigest()[:12]
        audits=artifact(gen,folder/('fact_audit_%02d_%s.json'%(start,input_hash)),'application_fact_audit_v6',prompt,check,3072)
        lookup={a['id']:a for a in audits}
        for n in batch:
            a=lookup[n['id']];n.update(event_assessment=a['assessment'],event_assessment_reason=a['reason'])
            if a['assessment']=='supported':
                n['label']=a['corrected_label'];n['definition']=a['corrected_definition'];audited.append(n)
    atomic_json(folder/'fact_inventory.json',{'all':inventory,'retained':audited,'review':'same GPU model; no independent human adjudication'})
    if len(audited)<9:raise InvalidModel('Fewer than nine supported candidate causes; do not pad')
    # The research question supplies W; it supplies no cause, edge or equation.
    outcome={'id':'W','label':'Campaign outcome','definition':packet['case']['outcome'],'type':'bool','observed':1,'reference':0,'reference_meaning':'The specified campaign is not active through the stated horizon','time':None,'actor':packet['case']['actor_scope'],'status':'established_event'}
    from .ordered_graph import discover
    nodes,links,excluded=discover(gen,packet,audited,outcome)
    result={'outcome':'W','nodes':nodes,'assumptions':[r['parent']+' -> '+r['child']+': '+r['limitation'] for r in links],
            'source_audit':cite_nodes(nodes,packet),'mechanism_proposals':links,'excluded_inventory_ids':excluded,
            'protocol_version':'source-inventory-incremental-v7-complete-outcome-packet','source_grounding':'literal spans and same-model full-paragraph event/parent audit; no independent human validation'}
    atomic_json(dest,result);return result


def legacy_global_graph(gen,packet,audited,outcome,folder,dest):
    from .application import cite_nodes
    segments={s['id']:s for s in packet['segments']}
    compact=[{k:n.get(k) for k in ('id','label','definition','time','observed','reference','type','segment_id')} for n in audited]+[outcome]
    prompt='Think briefly, reserving output for the compact JSON. Select a defensible causal DAG explaining W from these source-audited candidate events. Discover dependencies; no desired graph is supplied. Earlier occurrence alone does not cause a later event. Select about 10-18 substantive nodes including W only where a mechanism is defensible; fewer is an honest failure, not a reason to add filler. Distinct pathways may converge and events may inhibit a later state. Remove duplicate descriptions and irrelevant context. Return ONLY {"parents":{"W":["event_id"],"event_id":[]},"outcome_episode_id":"s00e00","outcome_time_reason":"one sentence","outcome_citations":[{"segment_id":"source ID","quote":"exact 2-7 word span"}],"assumptions":["up to three short limitations"]}. Do NOT return long per-edge explanations in this artifact: those receive a separate source/mechanism audit. Include an entry for EVERY selected node; nodes absent from parents are excluded context. Max 4 parents per child. Parent episode rank must be <= child rank; no cycles. All retained nodes should lead to W. Roots are source-event boundary conditions. Internal nodes need a meaningful dependence, not just chronology or correlation. W means EXACTLY the supplied research outcome, not an eventual victory or a single battle. Identify the episode by which W is already true; later documents can provide context but cannot cause an earlier completed outcome.\nOUTCOME: '+packet['case']['outcome']+'\nCANDIDATES: '+json.dumps(compact)+'\nFROZEN DOCUMENTS:\n'+packet['packet_text']
    def check_graph(response):
        mapping={n['id']:n for n in audited};mapping['W']=outcome
        ep=response.get('outcome_episode_id')
        if ep not in packet['case']['source_episodes']:raise InvalidModel('Identify the outcome event episode from the supplied horizon')
        mapping['W']['time']=int(ep[1:3])*100+int(ep[4:6])
        mapping['W']['story_time_basis']=response.get('outcome_time_reason','Model-selected outcome episode')
        parents=response['parents'];ids=set(parents)
        if 'W' not in ids or not ids<=mapping.keys():raise InvalidModel('Only listed IDs and mandatory W may be selected')
        g=nx.DiGraph();g.add_nodes_from(ids);errors=[]
        for child,ps in parents.items():
            if not isinstance(ps,list) or len(ps)>4 or len(set(ps))!=len(ps):raise InvalidModel('Parent list requires <=4 distinct IDs')
            for parent in ps:
                if parent not in ids or parent==child:errors.append('Unknown/self/unselected parent '+parent+' for '+child);continue
                a,z=mapping[parent]['time'],mapping[child]['time']
                if a is not None and z is not None and a>z:errors.append('Temporal reversal '+parent+' -> '+child)
                g.add_edge(parent,child)
        if not nx.is_directed_acyclic_graph(g):errors.append('Cycle '+str(nx.find_cycle(g)))
        if errors:raise InvalidModel('; '.join(errors))
        ancestry=nx.ancestors(g,'W')|{'W'}
        if len(ancestry)<10:raise InvalidModel('Only '+str(len(ancestry))+' substantive outcome ancestors; do not fabricate links to meet a count')
        if len(ancestry)>20:raise InvalidModel('Select at most twenty substantive ancestors')
        links={}
        citations=[]
        for c in response['outcome_citations']:
            aligned=align_quote(c.get('quote',''),segments.get(c.get('segment_id'),{}).get('text',''))
            if aligned is None:raise InvalidModel('Outcome needs exact short source quotations')
            citations.append(dict(segment_id=c['segment_id'],**aligned))
        if not citations:raise InvalidModel('Outcome source citation absent')
        result=[]
        for ident in nx.topological_sort(g):
            if ident in ancestry:result.append(dict(mapping[ident],parents=parents[ident]))
        w=next(n for n in result if n['id']=='W');w.update(citations=citations,segment_id=citations[0]['segment_id'],event_assessment='partial',event_assessment_reason='Composite campaign outcome; citations document stages, not identification of a counterfactual law.')
        return result,links,sorted(set(mapping)-ancestry)
    nodes,links,excluded=artifact(gen,folder/'fact_graph_compact.json','application_fact_graph_compact_v6',prompt,check_graph)
    graph=json.loads((folder/'fact_graph_compact.json').read_text())
    result={'outcome':'W','nodes':nodes,'assumptions':graph.get('assumptions',[])+[a+' -> '+z+': '+r['limitation'] for (a,z),r in links.items()],
            'source_audit':cite_nodes(nodes,packet),'mechanism_proposals':graph.get('links',[]),'excluded_inventory_ids':excluded,
            'protocol_version':'source-inventory-v6','source_grounding':'exact source spans and same-model claim review; no independent human validation'}
    atomic_json(dest,result);return result
