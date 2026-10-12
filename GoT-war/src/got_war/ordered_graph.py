"""Incremental, source-bounded graph discovery with explicit eligible parents.

The LLM orders same-episode events and chooses every dependency. The constructor
only prevents references to unselected/future states and prunes unused context.
"""
import hashlib,json,re
import networkx as nx
from .budget import atomic_json
from .structural_programs import InvalidModel


def episode(value):
    match=re.match(r'(?i)^s(\d{1,2})e(\d{1,2})(?:_p\d+)?$',str(value).strip())
    if not match:raise InvalidModel('Episode must identify season and episode, such as s01e02')
    return 's%02de%02d'%(int(match[1]),int(match[2]))


def discover(gen,packet,inventory,outcome):
    from .fact_pipeline import artifact
    from .application import packet_for_nodes
    folder=gen.run/'application'/packet['case']['id']/'ordered_graph';folder.mkdir(parents=True,exist_ok=True)
    prompt='Identify the ASSESSMENT ENDPOINT of this outcome question. This is the time at which the outcome state will be evaluated, not the first time a conflict might already have begun, and not a later source-access/report date. Do not treat eventual victory as interchangeable with undertaking a campaign. Return {"episode_id":"s00e00","reason":"one precise sentence"}. Use the supplied question and episode list only.\nQUESTION: '+packet['case']['outcome']+'\nAVAILABLE EPISODES: '+json.dumps(packet['case']['source_episodes'])
    def frame_check(response):
        ep=episode(response.get('episode_id'))
        if ep not in packet['case']['source_episodes']:raise InvalidModel('Choose an episode in the supplied list')
        return ep
    endpoint_file=gen.root/'configs/outcome_endpoints.json'
    declared=json.loads(endpoint_file.read_text()).get('cases',{}).get(packet['case']['id']) if endpoint_file.exists() else None
    if declared:
        ep=episode(declared['episode_id'])
        if ep not in packet['case']['source_episodes']:raise InvalidModel('Configured research endpoint lies outside the frozen packet horizon')
        atomic_json(folder/'declared_outcome_frame.json',dict(declared,provenance='Explicit endpoint of the supplied research question; not a story cause or a model-selected graph.'))
        reason=declared['reason']
    else:
        ep=artifact(gen,folder/'outcome_frame.json','application_outcome_frame',prompt,frame_check,1024)
        reason=json.loads((folder/'outcome_frame.json').read_text())['reason']
    outcome['time']=int(ep[1:3])*100+int(ep[4:6]);outcome['story_time_basis']=reason
    eligible=[n for n in inventory if n['time'] is None or n['time']<=outcome['time']]
    mapping={n['id']:n for n in eligible};mapping['W']=outcome
    compact=[{k:n.get(k) for k in ('id','label','definition','time','segment_id')} for n in eligible]
    prompt='Select 10-18 distinct relevant event variables from this source-audited inventory, followed by W. No causal graph or desired causes have been supplied. Exclude duplicates and unrelated events; do not fill a count. Return {"order":["event ID","W"],"selection_reason":"brief limitations"}. Arrange selected events in chronological order by their episode rank. Within an episode, use their documented causal/temporal precedence; acknowledge uncertain ordering. W must be last, at the stated assessment endpoint. Later events have already been excluded. A smaller supported model is preferable to invented relevance.\nOUTCOME: '+json.dumps(outcome)+'\nAUDITED SOURCE CLAIMS: '+json.dumps(compact)
    def order_check(response):
        order=response['order']
        if not isinstance(order,list) or len(order)!=len(set(order)) or not set(order)<=mapping.keys() or not order or order[-1]!='W':raise InvalidModel('Return distinct listed IDs with W last')
        if not 10<=len(order)<=20:raise InvalidModel('Need 10-20 substantive selected nodes without padding')
        times=[mapping[x]['time'] for x in order if mapping[x]['time'] is not None]
        if times!=sorted(times):raise InvalidModel('Episode ranks must be nondecreasing; reorder same-episode events based on their source statements')
        return order
    prompt+='\nRelevance is to the entire specified horizon. Consider the full inventory, including its latest eligible events; do not select a chronological prefix merely because earlier rows appear first. Exclude a cause that simply restates W. Do not substitute eventual victory for undertaking or continuing a campaign.'
    inv_hash=hashlib.sha256(prompt.encode()).hexdigest()[:12]
    order=artifact(gen,folder/('order_'+inv_hash+'.json'),'application_source_order',prompt,order_check,3072)
    parents={};links=[]
    for index,ident in enumerate(order):
        node=mapping[ident];prior=[mapping[x] for x in order[:index]]
        candidates=[{k:n.get(k) for k in ('id','label','definition','time','observed','segment_id')} for n in prior]
        prompt='Discover the direct causal parents of this ONE child from the eligible earlier states. Only propose a link when a concrete informational, institutional, material, enabling or inhibiting process is defensible from the documents. Earlier occurrence, shared character names, and list adjacency alone are insufficient. Zero parents is legitimate when the event is an external boundary; do not invent a relation to keep a graph connected. Select at most four parents. Return {"parents":["eligible ID"],"links":[{"parent":"eligible ID","mechanism":"specific concise process","status":"explicit OR inferred","segments":["exact source segment ID"],"limitation":"unidentified causal dependence or functional form"}],"boundary_reason":"why external if parents empty"}. Do not generate equations yet. All states refer to the recorded time, not a later change in the same character. W means the exact supplied campaign question. Think briefly and give compact JSON.\nOUTCOME: '+packet['case']['outcome']+'\nCHILD: '+json.dumps({k:node.get(k) for k in ('id','definition','label','time','observed')})+'\nELIGIBLE PARENTS: '+json.dumps(candidates)+'\nSOURCE DOCUMENTS:\n'+packet_for_nodes(packet,[node]+prior,8000)
        if ident=='W':
            # W has no occurrence citation until the final citation stage. The
            # generic node retriever therefore favors its parents' earlier
            # passages and can omit the endpoint itself. Supply the complete
            # frozen packet for this composite target, without choosing a cause.
            prompt=prompt.split('\nSOURCE DOCUMENTS:\n')[0]+'\nSOURCE DOCUMENTS (complete frozen outcome packet):\n'+packet['packet_text']
        def parent_check(response):
            ps=response['parents'];allowed={n['id'] for n in prior}
            if not isinstance(ps,list) or len(ps)>4 or len(ps)!=len(set(ps)) or not set(ps)<=allowed:raise InvalidModel('Parents must be distinct IDs from '+json.dumps(sorted(allowed))+' only')
            ls=response.get('links',[])
            if {x.get('parent') for x in ls}!=set(ps):raise InvalidModel('One source-linked rationale per selected parent is required')
            for link in ls:
                if link.get('status') not in ('explicit','inferred') or not link.get('mechanism'):raise InvalidModel('Specify explicit/inferred status and a concrete mechanism')
                if not link.get('segments') or not set(link['segments'])<={s['id'] for s in packet['segments']}:raise InvalidModel('Every proposed mechanism needs valid source paragraph IDs; inferential limitations remain explicit')
            return ps,ls
        key=hashlib.sha256(prompt.encode()).hexdigest()[:12]
        ps,ls=artifact(gen,folder/(ident+'_'+key+'.json'),'application_local_parent_discovery',prompt,parent_check,3072)
        parents[ident]=ps;links.extend(dict(link,child=ident) for link in ls)
    graph=nx.DiGraph();graph.add_nodes_from(order);graph.add_edges_from((p,n) for n,ps in parents.items() for p in ps)
    retained=nx.ancestors(graph,'W')|{'W'}
    atomic_json(folder/'selection.json',{'order':order,'parents':parents,'links':links,'retained':sorted(retained),'excluded_context':sorted(set(mapping)-retained),'outcome_frame':outcome,'outcome_evidence_policy':'complete frozen packet; never a chronological-prefix retrieval','note':'Acyclicity follows from source-ordered eligibility; no automatic causal link is inserted.'})
    if len(retained)<2:raise InvalidModel('No nontrivial explanatory dependency reaches the outcome')
    nodes=[dict(mapping[n],parents=parents[n]) for n in order if n in retained]
    for node in nodes:node['principal_figure_size_target_met']=len(retained)>=10
    # Outcome occurrence gets its own literal source selection, separate from the
    # occurrence citations attached to candidate causes.
    prompt='Select one or two source paragraphs documenting occurrence of this EXACT campaign outcome at its assessment endpoint. Return {"citations":[{"segment_id":"provided ID","quote":"EXACT contiguous 2-7 words"}],"limitation":"what this evidence does not establish"}. Do not equate a campaign with only its eventual victory.\nOUTCOME: '+json.dumps(outcome)+'\nDOCUMENTS:\n'+packet['packet_text']
    from .spans import align_quote
    def citation_check(response):
        result=[];segments={s['id']:s for s in packet['segments']}
        for c in response['citations']:
            aligned=align_quote(c.get('quote',''),segments.get(c.get('segment_id'),{}).get('text',''))
            if aligned is None:raise InvalidModel('Select a literal short source span from a valid paragraph')
            result.append(dict(segment_id=c['segment_id'],**aligned))
        if not 1<=len(result)<=2:raise InvalidModel('One or two bounded source citations required')
        return result
    citations=artifact(gen,folder/'outcome_citations.json','application_outcome_citations',prompt,citation_check,1536)
    w=next(n for n in nodes if n['id']=='W');w.update(citations=citations,segment_id=citations[0]['segment_id'],event_assessment='partial',event_assessment_reason='Composite campaign outcome; selected passages document occurrence, not its causal identification.')
    return nodes,links,sorted(set(mapping)-retained)
