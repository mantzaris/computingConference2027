"""Modular construction: variable, graph and citation artifacts have separate checks.

Every semantic choice is generated from the same frozen packet. Repairs are
localized to an artifact and capped at two; no topic-specific edge is supplied.
"""
import copy,json,re
import networkx as nx
from .budget import atomic_json
from .structural_programs import check_spec,valid_value,InvalidModel


def variable_error(node,segments,allow_unverified_source=False):
    try:
        for key in ('id','label','definition','type','time','observed','reference','reference_meaning','actor','status','segment_id'):
            if key not in node:raise ValueError('Missing '+key)
        if not isinstance(node['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,47}',node['id']):raise ValueError('Invalid variable identifier; use letters, digits and underscores')
        check_spec(node)
        if node['type'] in ('int','float') and not node.get('measurement_rule'):raise ValueError('Numeric states require an explicit source-grounded measurement_rule; do not assign latent numeric scores without one')
        if node['id']=='W' and node['type']!='bool':raise ValueError('The specified outcome W is Boolean: conflict present=1, absent=0')
        if not valid_value(node['observed'],node) or not valid_value(node['reference'],node):raise ValueError('Observed/reference values do not match type/domain')
        if not allow_unverified_source and node['segment_id'] not in segments:raise ValueError('Unknown source segment')
        if not isinstance(node['time'],int):raise ValueError('Relative story time must be integer')
        return None
    except (ValueError,KeyError,TypeError) as e:return str(e)


def build_blueprint(gen,packet,variables_only=False):
    # Lazy import avoids a circular dependency with the shared citation auditor.
    from .application import cite_nodes
    case=packet['case'];folder=gen.run/'application'/case['id'];folder.mkdir(parents=True,exist_ok=True)
    destination=folder/'blueprint.json'
    if destination.exists():return json.loads(destination.read_text())
    segments={s['id']:s for s in packet['segments']}
    proposal=folder/'variable_proposal.json'
    instruction='From this frozen television evidence, DISCOVER 12-14 substantive observable variables useful to explaining the specified war outcome. Include the outcome as W, with its exact specified meaning and Boolean states (conflict present=1, absent=0). Do not use generic introductions, mere character names, duplicate events or unrelated plotlines to fill a count. A variable is a state/event with an operational definition. Do not yet assign causal parents. Return compact JSON {"variables":[{"id":"v1","label":"short label","definition":"at most 15 words","type":"bool","observed":1,"reference":0,"reference_meaning":"absence of this named event","time":1,"actor":"actor","status":"established_event","segment_id":"EXACT source segment"},... ]}. Types can be bool, category, int or float as evidence warrants. Bool observations are 0/1. Category requires values with at least two strings, and string observation/reference in that list. Numeric types require explicit two-element bounds and a measurement_rule field grounded in documented quantities. For each variable time is relative STORY order, not audience revelation. Mark reports, beliefs and assumptions distinctly. Use only the packet; no memory. The reference must state the specific comparison condition, not a generic placeholder.\nOUTCOME: '+case['outcome']+'\nSCOPE: '+case['horizon']+'\nPACKET:\n'+packet['packet_text']
    if proposal.exists():out=json.loads(proposal.read_text())
    else:out=gen.call('application_variable_discovery_v3',instruction,3072,2027);atomic_json(proposal,out)
    nodes=out.get('variables',out.get('nodes',[]))
    if not 10<=len(nodes)<=18:raise InvalidModel('Insufficient/noncompact generated variable set')
    # Identifiers are serialization, not causal content. Bind the explicitly named
    # outcome and canonicalize IDs before any dependency graph is requested.
    candidates=[i for i,n in enumerate(nodes) if n.get('id')=='W' or n.get('status')=='outcome']
    if len(candidates)!=1:
        binding=gen.call('application_outcome_binding_v3','Which proposed variable represents EXACTLY the supplied outcome? Return {"index":0} with its zero-based position. This is identifier binding, not choosing causes. OUTCOME: '+case['outcome']+' VARIABLES: '+json.dumps([{'index':i,'label':n.get('label'),'definition':n.get('definition')} for i,n in enumerate(nodes)]),256,2027)
        candidates=[binding['index']]
    chosen=candidates[0]
    if not isinstance(chosen,int) or not 0<=chosen<len(nodes):raise InvalidModel('Invalid outcome binding')
    mapping=[]
    for i,n in enumerate(nodes):
        old=n.get('id');n['id']='W' if i==chosen else 'v%d'%(i+1)
        if n.get('status')=='outcome':n['status']='modeling_assumption';n['role']='outcome'
        mapping.append({'proposal_id':old,'canonical_id':n['id']})
    atomic_json(folder/'identifier_binding.json',{'mapping':mapping,'outcome_index':chosen,'note':'Identifier normalization only; no generated causal relationship changed.'})
    repaired=[]
    for node in nodes:
        node=copy.deepcopy(node)
        # Root domain/observation errors are repaired in a bounded individual artifact.
        for attempt in range(3):
            error=variable_error(node,segments,allow_unverified_source=True)
            if not error:break
            atomic_json(folder/('variable_'+re.sub(r'[^A-Za-z0-9_]','_',str(node.get('id','unknown')))[:64]+'_failed_%d.json'%attempt),{'node':node,'error':error})
            if attempt==2:raise InvalidModel('Unrepaired variable '+node.get('id','?')+': '+error)
            prompt='Repair ONLY this typed variable using the source packet. Keep its ID and intended event, or state that support is absent. Return the corrected variable object with id,label,definition,type,observed,reference,reference_meaning,time,actor,status,segment_id. For category provide values (>=2 strings) and string states; for int/float bounds and a measurement_rule field.\nDIAGNOSTIC: '+error+'\nVARIABLE: '+json.dumps(node)+'\nSOURCE:\n'+packet['packet_text']
            node=gen.call('application_variable_type_repair_v3',prompt,1024,2027+attempt)
        repaired.append(node)
    nodes=repaired;atomic_json(folder/'typed_variables.json',nodes)
    if variables_only:return {'nodes':nodes}
    # Short exact spans are selected by the LLM from the already chosen paragraph.
    for start in range(0,len(nodes),4):
        batch=nodes[start:start+4];citation_file=folder/('citations_%d.json'%start)
        request=[{'id':n['id'],'claim':n['definition'],'segment_id':n['segment_id'],'passage':segments.get(n['segment_id'],{}).get('text','Proposed ID absent: select from the frozen packet.')} for n in batch]
        prompt='For each claim select the best supporting segment from the frozen packet (the proposed segment may be wrong), and a SHORT CONTIGUOUS EXACT span (2-8 words) from its supplied passage supporting the event. Return {"citations":[{"id":"variable ID","segment_id":"given segment ID","quote":"EXACT copied span","event_assessment":"supported OR partial OR unsupported","reason":"brief entailment limit"}]}. Never fabricate a quote. A matching span is not by itself proof of the claim or its outgoing mechanism.\n'+json.dumps(request)+'\nFULL FROZEN PACKET:\n'+packet['packet_text']
        for attempt in range(3):
            response=json.loads(citation_file.read_text()) if attempt==0 and citation_file.exists() else gen.call('application_span_audit_v3' if attempt==0 else 'application_span_repair_v3',prompt,1024,2027+attempt)
            lookup={r['id']:r for r in response.get('citations',[])};errors=[]
            for n in batch:
                c=lookup.get(n['id'],{});quote=c.get('quote','');selected=c.get('segment_id');text=segments.get(selected,{}).get('text','')
                if quote and quote in text and len(quote.split())>14:
                    # A source-exact bounded prefix preserves the selected occurrence.
                    end=list(re.finditer(r'\S+',quote))[9].end();quote=quote[:end];c['quote']=quote;c['excerpt_shortened']=True
                if selected not in segments or not quote or quote not in text:errors.append(n['id'])
                elif c.get('event_assessment')=='unsupported':errors.append(n['id']+' unsupported event')
                else:n['segment_id']=selected;n['citations']=[{'segment_id':selected,'quote':quote}];n['event_assessment']=c.get('event_assessment');n['event_assessment_reason']=c.get('reason')
            if not errors:atomic_json(citation_file,response);break
            atomic_json(folder/('citations_%d_failed_%d.json'%(start,attempt)),{'response':response,'errors':errors})
            if attempt==2:raise InvalidModel('Citation/entailment artifact exhausted repairs: '+str(errors))
            prompt=prompt.split('\nREPAIR:')[0]+'\nREPAIR: invalid/non-exact/unsupported entries '+str(errors)+'. Use short exact substrings. Do not declare an unsupported claim supported.'
    graph_file=folder/'generated_graph.json'
    compact=[{k:n[k] for k in ('id','label','definition','time','observed','type')} for n in nodes]
    graph_prompt='Discover a plausible CAUSAL dependency graph over these generated variables leading to the EXACT war outcome W. Temporal sequence alone does not establish causality. Do not confuse a narrative report with the reported event. Retain only substantively relevant variables; you may drop unrelated non-W variables, but never pad the graph. Return compact JSON {"parents":{"v1":[],"v2":["v1"],"W":["v2"]},"drop":[],"assumptions":["which proposed links the evidence does not identify"]}. Every retained non-outcome must be an ancestor of W. DAG only, parents at equal/earlier story times. Each variable has at most 4 parents; choose a small root boundary, not an all-root event inventory. Use only listed IDs and supplied evidence. The user has supplied no desired causal graph: discover it.\nOUTCOME: '+case['outcome']+'\nVARIABLES: '+json.dumps(compact)+'\nPACKET:\n'+packet['packet_text']
    graph_prompt+='\nIf a proposed time rank is inconsistent with the actual chronology in the supplied evidence, return a times object mapping variable IDs to corrected integer STORY ranks. In particular the outcome concerns the stated time horizon, not the order in which variables were listed. No future event may cause an already completed earlier outcome. Every correction must have a brief time_correction_reason. Valid segment IDs: '+json.dumps(list(segments))
    graph_out=None
    for attempt in range(3):
        graph_out=json.loads(graph_file.read_text()) if attempt==0 and graph_file.exists() else gen.call('application_dependency_discovery_v3' if attempt==0 else 'application_dependency_repair_v3',graph_prompt,1536,2027+attempt)
        try:
            ids={n['id'] for n in nodes}-set(graph_out.get('drop',[]));parents=graph_out['parents']
            if len(ids)<10 or 'W' not in ids:raise ValueError('Fewer than 10 substantive retained nodes or outcome dropped')
            g=nx.DiGraph();g.add_nodes_from(ids);mapping={n['id']:dict(n) for n in nodes}
            for ident,time_rank in graph_out.get('times',{}).items():
                if ident not in mapping or not isinstance(time_rank,int):raise ValueError('Invalid generated chronology correction')
                mapping[ident]['time']=time_rank
            for ident in ids:
                if ident not in parents:raise ValueError('Missing parents entry '+ident)
                for parent in parents[ident]:
                    if parent not in ids:raise ValueError('Unknown/dropped parent '+parent+' for '+ident)
                    if mapping[parent]['time']>mapping[ident]['time']:raise ValueError('Later event '+parent+' cannot parent earlier '+ident)
                    g.add_edge(parent,ident)
            if not nx.is_directed_acyclic_graph(g):raise ValueError('Cycle '+str(nx.find_cycle(g)))
            irrelevant=ids-(nx.ancestors(g,'W')|{'W'})
            if irrelevant:raise ValueError('Disconnected from W: '+str(sorted(irrelevant)))
            nodes=[dict(mapping[n['id']],parents=parents[n['id']]) for n in nodes if n['id'] in ids]
            atomic_json(graph_file,graph_out);break
        except Exception as e:
            atomic_json(folder/('graph_failed_%d.json'%attempt),{'response':graph_out,'error':str(e)})
            if attempt==2:raise InvalidModel('Graph artifact exhausted two repairs: '+str(e))
            graph_prompt=graph_prompt.split('\nREPAIR:')[0]+'\nREPAIR: '+str(e)+'\nPrevious compact graph: '+json.dumps(graph_out)+'\nReturn the entire corrected parents mapping; keep the source-bounded variable meanings.'
    audit=cite_nodes(nodes,packet)
    result={'outcome':'W','nodes':nodes,'assumptions':graph_out.get('assumptions',[]),'source_audit':audit,'protocol_version':'modular-v3','source_grounding':'exact-span traceability plus same-model entailment assessment; no independent review'}
    atomic_json(destination,result);return result
