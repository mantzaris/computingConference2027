"""Source-semantic development gate for application blueprints.

All substantive corrections and parent choices are generated. The researcher
supplies no literary rule or edge. These checks remain same-model judgments.
"""
import copy,json
import networkx as nx
from .budget import atomic_json
from .construction import variable_error
from .application import cite_nodes
from .structural_programs import InvalidModel
from .spans import align_quote,locate_excerpt
from .timing import annotate_times


def review_blueprint(gen,packet,proposal):
    folder=gen.run/'application'/packet['case']['id'];folder.mkdir(parents=True,exist_ok=True)
    destination=folder/'blueprint.json'
    if destination.exists():return json.loads(destination.read_text())
    segments={s['id']:s for s in packet['segments']};nodes=[];dropped=[]
    proposed=proposal['nodes'] if 'nodes' in proposal else proposal['variables']
    for start in range(0,len(proposed),3):
        batch=proposed[start:start+3];dest=folder/('semantic_variables_%d.json'%start)
        compact=[{k:n.get(k) for k in ('id','label','definition','actor','type','values','bounds','measurement_rule','observed','reference','reference_meaning','status','time')} for n in batch]
        prompt='Perform a STRICT source-entailment audit and correction of these proposed narrative variables. Check WHO did WHAT to WHOM, negation, whether it was merely reported/believed, and WHEN it happened. A related topic or matching name does not entail the claim. Correct the variable label/definition to what the document actually says; do not replace it with a different event. Mark retain=false if it is unsupported or irrelevant to the specified outcome. This is evidence-grounded concept refinement, not memory completion. Do not invent numeric latent measurements. Return {"variables":[{"id":"UNCHANGED ID","retain":true,"label":"short faithful event label","definition":"faithful operational definition","type":"bool","observed":1,"reference":0,"reference_meaning":"specific absence or alternative state","actor":"documented actor","status":"established_event OR character_report OR character_belief OR disputed_account OR modeling_assumption","time":105,"story_time_basis":"source-grounded chronology justification; distinguish retrospective reporting","event_assessment":"supported OR partial OR unsupported","event_assessment_reason":"actor/action/time entailment check and remaining limits","citations":[{"segment_id":"EXACT valid packet ID","quote":"EXACT contiguous span of 2-10 words"}]}]}. Category variables require values; numeric variables require bounds and measurement_rule. Use story ranks as season*100+episode when the event is contemporary with the passage, and explain any earlier event time. W is the exact supplied outcome and must remain Boolean; its occurrence can be evidenced by several passages. Do not present a partial proxy as complete support for W. Maximum two short citations per variable.\nOUTCOME: '+packet['case']['outcome']+'\nPROPOSED VARIABLES: '+json.dumps(compact)+'\nVALID SEGMENT IDS: '+json.dumps(list(segments))+'\nFROZEN PACKET:\n'+packet['packet_text']
        for attempt in range(3):
            response=json.loads(dest.read_text()) if attempt==0 and dest.exists() else gen.call('application_semantic_variables_v5' if not attempt else 'application_semantic_variables_repair_v5',prompt,3072,2027+attempt,thinking=True)
            try:
                rows=response['variables']
                if {n['id'] for n in rows}!={n['id'] for n in batch}:raise InvalidModel('Return every proposed ID exactly once, unchanged')
                for n in rows:
                    if not n.get('retain',True):
                        if n['id']=='W':raise InvalidModel('Outcome cannot be dropped; report missing support explicitly')
                        continue
                    if n.get('event_assessment') not in ('supported','partial','unsupported'):raise InvalidModel('Missing event-support assessment for '+n['id'])
                    if n.get('event_assessment')=='unsupported':raise InvalidModel('Unsupported event must be omitted, never labeled retained')
                    citations=n.get('citations',[])
                    if not citations or len(citations)>2:raise InvalidModel('Need one or two short source citations for '+n['id'])
                    for c in citations:
                        quote=c.get('quote','');sid=c.get('segment_id')
                        aligned=align_quote(quote,segments[sid]['text']) if sid in segments else None
                        if aligned is None and sid in segments:
                            aligned=locate_excerpt(n['definition'],quote,segments[sid]['text'])
                        if aligned is None:raise InvalidModel('No literal contiguous source alignment for '+n['id'])
                        c.update(aligned)
                        if aligned.get('entailment_review_required'):
                            n.setdefault('model_event_assessment',n.get('event_assessment'))
                            n['event_assessment']='partial'
                            n['event_assessment_reason']+=' Generated quotation was not literal; a navigational excerpt was retrieved from the selected paragraph, and entailment remains unverified.'
                    n['segment_id']=citations[0]['segment_id']
                    error=variable_error(n,segments)
                    if error:raise InvalidModel(n['id']+': '+error)
                    if n.get('event_assessment')=='unsupported':raise InvalidModel('Unsupported event must be omitted, never labeled retained')
                atomic_json(dest,response);break
            except Exception as e:
                atomic_json(folder/('semantic_variables_%d_failed_%d.json'%(start,attempt)),{'response':response,'error':str(e)})
                if attempt==2:raise
                prompt=prompt.split('\nVALIDATION REPAIR:')[0]+'\nVALIDATION REPAIR: '+str(e)+'\nPrevious response: '+json.dumps(response)
        nodes.extend(n for n in rows if n.get('retain',True));dropped.extend(n for n in rows if not n.get('retain',True))
    if len(nodes)<10:raise InvalidModel('Fewer than ten source-supported substantive variables after semantic audit')
    nodes=annotate_times(gen,packet,nodes)
    # Parents are discovered separately for each child, avoiding a sequential
    # adjacency template that can encourage chronological-chain imitation.
    compact=[{k:n.get(k) for k in ('id','label','definition','time','status','actor')} for n in nodes]
    proposals=[]
    for start in range(0,len(nodes),3):
        batch=nodes[start:start+3];dest=folder/('mechanism_proposals_%d.json'%start)
        prompt='For EACH requested child variable, discover which other listed variables could directly affect its state by a defensible mechanism supported or motivated by this evidence. Do not mechanically chain events in narrative/list order. Earlier occurrence is not a mechanism. An unrelated event cannot cause another just because both occurred. Roots are legitimate external boundary conditions; multiple pathways may converge where justified, but do not manufacture convergence. Explain each proposed link in terms of a concrete enabling, inhibiting, institutional, material or informational process. Separate evidence for event occurrence from the assumed counterfactual dependence. Return {"children":[{"id":"child ID","parents":["parent ID"],"links":[{"parent":"parent ID","mechanism":"specific causal rationale","status":"explicit OR inferred","segments":["packet source IDs"],"limitation":"unidentified dependence or functional form"}]}]}. Choose 0-4 direct parents per child from the listed variables. Do not include an unsupported or temporally reversed link merely to keep a node connected. Parent story rank must be <= child rank. No equations yet.\nREQUESTED CHILDREN: '+json.dumps([n['id'] for n in batch])+'\nOUTCOME: '+packet['case']['outcome']+'\nVARIABLES: '+json.dumps(compact)+'\nFROZEN PACKET:\n'+packet['packet_text']
        response=json.loads(dest.read_text()) if dest.exists() else gen.call('application_mechanism_discovery_v5',prompt,4096,2027,thinking=True)
        atomic_json(dest,response);proposals.extend(response.get('children',[]))
    graph={r['id']:r.get('parents',[]) for r in proposals};mapping={n['id']:n for n in nodes};dropped_ids=[]
    for attempt in range(3):
        try:
            ids=set(mapping)-set(dropped_ids)
            if len(ids)<10 or 'W' not in ids:raise InvalidModel('Fewer than 10 relevant nodes or W omitted; never fix by inventing links')
            g=nx.DiGraph();g.add_nodes_from(ids);errors=[]
            for child in sorted(ids):
                if child not in graph:errors.append('Missing child '+child);continue
                if len(set(graph[child]))!=len(graph[child]) or len(graph[child])>4:errors.append('Invalid parent list '+child)
                for parent in graph[child]:
                    if parent not in ids or parent==child:errors.append('Unknown/self/dropped parent '+parent+' for '+child);continue
                    a=mapping[parent]['time'];z=mapping[child]['time']
                    if a is not None and z is not None and a>z:errors.append('Temporal reversal '+parent+' -> '+child)
                    g.add_edge(parent,child)
            if not nx.is_directed_acyclic_graph(g):errors.append('Cycle '+str(nx.find_cycle(g)))
            missing=ids-(nx.ancestors(g,'W')|{'W'})
            if missing:errors.append('Variables outside W ancestry: '+str(sorted(missing))+'. Drop irrelevant variables if ten remain, or identify evidence-motivated links; never chain by chronology.')
            if errors:raise InvalidModel('; '.join(errors))
            break
        except Exception as e:
            atomic_json(folder/('mechanism_graph_failed_%d.json'%attempt),{'parents':graph,'dropped':dropped_ids,'error':str(e)})
            if attempt==2:raise
            prompt='Reconcile the proposed dependencies into a source-bounded DAG for the specified outcome. Fix ALL diagnostics using evidence. Check causal direction against the passage: a response cannot be the cause of the event that prompted it. Do not invent a connection merely to satisfy a node count. Drop irrelevant nodes if at least ten substantive variables remain. Preserve variable meanings and episode ranks. Return compact JSON {"parents":{"id":["parent"]},"drop":[],"reasons":["brief evidence-based correction and uncertainty"]}. Parents <=4 each. Every retained non-W variable must lead to W.\nDIAGNOSTICS: '+str(e)+'\nOUTCOME: '+packet['case']['outcome']+'\nVARIABLES: '+json.dumps(compact)+'\nCURRENT GRAPH: '+json.dumps(graph)+'\nPACKET:\n'+packet['packet_text']
            repair_file=folder/('mechanism_graph_repair_%d.json'%attempt)
            response=json.loads(repair_file.read_text()) if repair_file.exists() else gen.call('application_mechanism_graph_repair_compact',prompt,3072,2027+attempt)
            atomic_json(repair_file,response)
            # A partial correction must not silently erase unchanged generated
            # parent sets. Only the explicit drop list removes a variable.
            graph.update(response['parents']);dropped_ids=response.get('drop',dropped_ids)
    nodes=[dict(n,parents=graph[n['id']]) for n in nodes if n['id'] in ids]
    limits={(link.get('parent'),p['id']):link.get('limitation','Unidentified functional form') for p in proposals for link in p.get('links',[])}
    assumptions=[parent+' -> '+n['id']+': '+limits.get((parent,n['id']),'LLM-reconciled dependency; counterfactual mechanism is not identified by the source observations.') for n in nodes for parent in n['parents']]
    result={'outcome':'W','nodes':nodes,'assumptions':assumptions,
            'source_audit':cite_nodes(nodes,packet),'mechanism_proposals':proposals,'dropped_variables':dropped,'dropped_graph_ids':dropped_ids,
            'protocol_version':'semantic-modular-v5-thinking','source_grounding':'source-exact spans plus same-model actor/action/time and mechanism review; no independent human validation'}
    atomic_json(destination,result);return result
