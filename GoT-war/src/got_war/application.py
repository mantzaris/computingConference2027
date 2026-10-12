"""LLM-discovered literary variables, generated mechanisms, and auditable traces."""
import copy, json, time
from pathlib import Path
import networkx as nx
from .generation import Generator
from .structural_programs import SCM, InvalidModel, equation, domain,check_spec,valid_value
from .experiments import leaf_keys
from .attribution import select_paths,coalitions,disjoint_mechanism_groups,evidence_priority
from .budget import atomic_json


def packet_for_nodes(packet,nodes,max_chars=9000):
    wanted={c['segment_id'] for n in nodes for c in n.get('citations',[])}
    selected=[s for s in packet['segments'] if s['id'] in wanted]
    extra=[s for s in packet['segments'] if s['id'] not in wanted]
    text='\n'.join('['+s['id']+'] '+s['text'] for s in selected)
    for s in extra:
        line='['+s['id']+'] '+s['text']
        if len(text)+len(line)<max_chars:text+='\n'+line
    return text


def cite_nodes(nodes,packet):
    segments={s['id']:s for s in packet['segments']};audit=[]
    for node in nodes:
        citations=[]
        for citation in node.get('citations',[]):
            sid=citation.get('segment_id');quote=citation.get('quote','');seg=segments.get(sid)
            offset=seg['text'].find(quote) if seg and quote else -1
            valid=offset>=0 and 1<=len(quote.split())<=14
            record={'node_id':node['id'],'segment_id':sid,'quote':quote if len(quote.split())<=14 else '',
                    'reference_valid':valid,'source_id':seg['source_id'] if seg else None,
                    'start':seg['start']+offset if valid else None,'end':seg['start']+offset+len(quote) if valid else None,
                    'proposition_status':node.get('status','modeling_assumption'),
                    'event_assessment':node.get('event_assessment','not assessed'),
                    'event_assessment_reason':node.get('event_assessment_reason',''),
                    'story_relative_time':node.get('time'),
                    'statement_time':seg.get('statement_time') if seg else None,
                    'audience_revelation_time':seg.get('audience_revelation_time') if seg else None,
                    'event_support':'cited passage; entailment not independently verified' if valid else 'unverified citation',
                    'mechanism_support':'separate edge assessment required'}
            for key in ('raw_quote_exact','original_generated_quote','span_method','excerpt_terms_matched','entailment_review_required'):
                if key in citation:record[key]=citation[key]
            audit.append(record)
            if valid:citations.append(record)
        node['verified_citations']=citations
    return audit


def blueprint_v2(gen,packet):
    case=packet['case'];path=gen.run/'application'/case['id']/'blueprint.json'
    if path.exists():return json.loads(path.read_text())
    prompt='Discover a source-grounded DAG explaining this frozen outcome: '+case['outcome']+'\nScope: '+case['horizon']+'; '+case['actor_scope']+'.\nUse only this HBO television source packet (secondary summaries). Do not use model memory. Aim for 12-16 substantive nodes, minimum 10 ONLY if supported. Avoid disconnected padding, restating the outcome, spurious edges, unmeasured feelings, or future events causing past ones. Every node must be an ancestor of the outcome or the outcome itself. Distinguish event occurrence from beliefs/reports. Variable types may be bool, category (provide values), int/float (provide bounds and measurement rule); use the state space supported by the evidence, not a forced all-Boolean template. Numbers for time give relative STORY EVENT order, not audience revelation order. Return JSON {"outcome":"node_id","nodes":[{"id":"short_id","label":"concise label","definition":"operational definition","type":"bool","time":1,"actor":"actor context","parents":["earlier_id"],"observed":1,"reference":0,"reference_meaning":"explicit comparison assumption","status":"established_event OR character_report OR character_belief OR disputed_account OR modeling_assumption","citations":[{"segment_id":"exact segment ID","quote":"exact supporting span of at most 10 words"}]}],"assumptions":["unidentified links or omitted context"]}. No equations yet. References must be meaningful alternative inputs, not automatically zero. Do not invent confidence probabilities.\nPACKET:\n'+packet['packet_text']
    prompt = 'Build a CAUSAL MODEL, not a list of plot summaries. The outcome variable must be W and mean exactly the specified war outcome. Identify 10-14 substantive observable states. Use short identifiers distinct from segment IDs. Keep definitions brief and each quote to 2-8 EXACT words. For each nonroot, discover 1-4 causal parents from the other variables; every variable must lead to W. Mark inferred relations as assumptions, never conflate event occurrence with a causal law. Include only supported material. Do not use filler. For bool use observed/reference integers 0 or 1. For category provide values and string observed/reference from that list; for int/float supply bounds. Do not reproduce the packet paragraph by paragraph.\n' + prompt
    schema=json.loads((gen.root/'prompts/application_blueprint_schema.json').read_text())
    last=None
    for attempt in range(3):
        output=None
        try:
            output=gen.call('application_variables_v2' if not attempt else 'application_variable_repair_v2',prompt,4096,2127+attempt,schema=schema)
            nodes=output['nodes'];ids={n['id'] for n in nodes}
            if len(ids)!=len(nodes) or not 10<=len(nodes)<=24:raise ValueError('Need 10-24 distinct substantive nodes when evidence permits')
            graph=nx.DiGraph();graph.add_nodes_from(ids)
            if output['outcome']!='W':raise ValueError('Outcome must be the specified war state W')
            for n in nodes:
                check_spec(n)
                if not valid_value(n['observed'],n) or not valid_value(n['reference'],n):raise ValueError('Observed/reference values violate type for '+n['id'])
                for p in n['parents']:
                    if p not in ids:raise ValueError('Unknown parent '+p)
                    if next(x for x in nodes if x['id']==p)['time']>n['time']:raise ValueError('Temporal reversal '+p+' -> '+n['id'])
                    graph.add_edge(p,n['id'])
            if not nx.is_directed_acyclic_graph(graph):raise ValueError('Cycle')
            if output['outcome'] not in ids:raise ValueError('Unknown outcome')
            absent=ids-(nx.ancestors(graph,output['outcome'])|{output['outcome']})
            if absent:raise ValueError('Nodes outside outcome ancestry '+str(absent))
            audit=cite_nodes(nodes,packet)
            unsupported=[n['id'] for n in nodes if not n['verified_citations']]
            if unsupported:raise ValueError('Need exact supporting short quotations for '+str(unsupported))
            output['source_audit']=audit;atomic_json(path,output);return output
        except Exception as e:
            last=str(e);atomic_json(path.with_name('blueprint_failed_%d.json'%attempt),{'response':output,'error':last})
            prompt=prompt.split('\nREPAIR DIAGNOSTIC:')[0]+'\nREPAIR DIAGNOSTIC: '+last+'\nRegenerate the whole valid blueprint from the packet. Use contiguous exact quotes.'
    raise ValueError('Blueprint failed: '+last)


def blueprint(gen,packet):
    from .fact_pipeline import build
    return build(gen,packet)


def blueprint_legacy(gen,packet):
    from .construction import build_blueprint
    from .grounding import review_blueprint
    folder=gen.run/'application'/packet['case']['id']
    if (folder/'blueprint.json').exists():return json.loads((folder/'blueprint.json').read_text())
    source=folder/'semantic_input.json'
    proposed=json.loads(source.read_text()) if source.exists() else build_blueprint(gen,packet,variables_only=True)
    return review_blueprint(gen,packet,proposed)


def synthesize(gen,packet,bp,alternative):
    contract=(gen.root/'prompts/ast_contract.txt').read_text();nodes=copy.deepcopy(bp['nodes']);rules={};failures=[]
    # Mechanisms differ, variable meanings/outcome stay aligned across alternatives.
    for index in range(0,len(nodes),4):
        batch=nodes[index:index+4]
        schema=[{k:n[k] for k in ['id','label','type','observed','reference','parents','time','values','bounds'] if k in n} for n in nodes]
        prompt=contract+'\nSynthesize plausible fixed structural equations for ONLY these node IDs: '+json.dumps([n['id'] for n in batch])+'. This is alternative '+str(alternative+1)+' of 3; express a defensible alternative combination (necessity, redundancy, inhibition, interactions) where the source does not identify a rule. Never claim the assumed functional form was observed. Preserve variable definitions and supplied parent sets. Each root uses ONLY its own explicit background {"noise":"U_nodeid"}; each nonroot uses its listed parents and NO new noise/residual. Every declared parent must affect output for some valid domain assignment. Match ALL observed states. Return {"rules":[{"id":"node_id","expr":{...},"assumptions":["explicit unidentified form"],"explanation":"mechanism description"}]} in compact JSON.\nOUTCOME: '+packet['case']['outcome']+'\nVARIABLE SCHEMA:\n'+json.dumps(schema)+'\nEVIDENCE:\n'+packet_for_nodes(packet,batch,6000)
        out=gen.call('application_equations',prompt,2048,2027+alternative)
        for rule in out['rules']:rules[rule['id']]=rule
    background={}
    for n in nodes:
        rule=rules.get(n['id'],{})
        # Preserve the discovered variable contract. Invalid/missing expressions
        # enter the same bounded repair loop as other structural failures.
        for key in ('expr','assumptions','explanation'):
            if key in rule:n[key]=rule[key]
        n.setdefault('expr',None)
        n['noise']=[] if n['parents'] else ['U_'+n['id']]
        for uid in n['noise']:
            background[uid]={k:n[k] for k in ('type','bounds','values') if k in n};background[uid]['observed']=n['observed']
    model={'id':packet['case']['id']+'_alt%d'%alternative,'outcome':bp['outcome'],'nodes':nodes,'background':background,
           'outcome_definition':packet['case']['outcome'],'packet_sha256':packet['packet_sha256'],'alternative':alternative,
           'background_interpretation':'fixed factual context, no identified probability measure','assumptions':bp.get('assumptions',[])}
    for repair in range(3):
        try:
            scm=SCM(model)
            if any(n['parents'] and n.get('noise') for n in model['nodes']):raise InvalidModel('Internal residual')
            return model,scm.diagnostics,failures
        except Exception as e:
            failures.append({'attempt':repair,'error':str(e),'model':copy.deepcopy(model)})
            if repair==2:break
            compact=[{k:n[k] for k in ['id','type','bounds','values','parents','noise','expr','observed','time'] if k in n} for n in model['nodes']]
            prompt=contract+'\nRepair these equations using the diagnostic; keep variable definitions, parents, observations, and relative story times. Do not drop active inputs or add residual noise. Return {"rules":[{"id":"id","expr":{...}}]} for ALL nodes. Root background is U_nodeid.\nDIAGNOSTIC: '+str(e)+'\nMODEL: '+json.dumps(compact)+'\nOUTCOME: '+packet['case']['outcome']+'\nWhen evidence does not identify a function, it stays a modeling assumption.'
            out=gen.call('application_equation_repair',prompt,4096,2027+alternative+repair)
            mapping={x['id']:x for x in out['rules']}
            for n in model['nodes']:
                if n['id'] in mapping:
                    n['expr']=mapping[n['id']]['expr']
                    n.setdefault('pre_repair_explanation',n.get('explanation'))
                    n['explanation']=equation(n['expr'])
                    n['description_status']='Equation rendered from repaired AST; original synthesis explanation retained separately.'
    raise InvalidModel(json.dumps({'error':'No admissible mechanism after two repairs','failures':failures}))


def assess(gen,packet,model):
    nodes={n['id']:n for n in model['nodes']};edges={}
    all_edges=[(p,n['id']) for n in model['nodes'] for p in n['parents']]
    for start in range(0,len(all_edges),6):
        batch=all_edges[start:start+6]
        claims=[{'edge_id':a+'>'+b,'parent':nodes[a]['definition'],'child':nodes[b]['definition'],'equation':equation(nodes[b]['expr'])} for a,b in batch]
        relevant=[nodes[n] for n in {x for pair in batch for x in pair}]
        prompt='Assess evidence for the following causal mechanisms using only this source packet. Event occurrence alone does NOT identify a functional form. Score in [0,1] is heuristic support, not probability. Be conservative. Return {"edges":[{"edge_id":"a>b","score":0.0,"event_support":0.0,"mechanism_explicitness":0.0,"temporal_compatibility":0.0,"independent_corroboration":0,"contradiction":"none found or explanation","status":"explicit OR inferred OR unsupported","segments":["exact supporting segment IDs"],"reason":"brief support/assumption distinction"}]}. These summaries come from one dependent editorial source family, so independent corroboration cannot be assumed.\nCLAIMS:\n'+json.dumps(claims)+'\nPACKET:\n'+packet_for_nodes(packet,relevant,10500)
        out=gen.call('application_evidence',prompt,2048,2027)
        valid_ids={s['id'] for s in packet['segments']}
        for entry in out['edges']:
            if entry.get('edge_id') not in [a+'>'+b for a,b in batch]:continue
            entry['score']=max(0,min(1,float(entry['score'])))
            entry['invalid_source_ids']=[x for x in entry.get('segments',[]) if x not in valid_ids]
            entry['segments']=[x for x in entry.get('segments',[]) if x in valid_ids]
            entry['independent_corroboration']=0
            if not entry['segments']:entry['score']=0;entry['status']='unsupported'
            edges[entry['edge_id']]=entry
    for a,b in all_edges:edges.setdefault(a+'>'+b,{'score':0,'segments':[],'status':'unassessed'})
    return edges


def run_application(root,case_ids=None,alternatives=None):
    gen=Generator(root);config=json.loads((gen.root/'configs/experiment.json').read_text())
    for case in config['cases']:
        if case_ids is not None and case['id'] not in case_ids:continue
        folder=gen.run/'application'/case['id'];folder.mkdir(parents=True,exist_ok=True)
        packet=json.loads((gen.root/'.private/packets'/(case['id']+'.json')).read_text())
        print('APPLICATION',case['id'],flush=True)
        try:bp=blueprint(gen,packet)
        except Exception as e:
            atomic_json(folder/'failure.json',{'stage':'blueprint','error':str(e)});continue
        for alternative in (range(3) if alternatives is None else alternatives):
            dest=folder/('alternative_%d.json'%alternative)
            if dest.exists():continue
            try:
                from .local_equations import synthesize_local
                model,diagnostics,failures=synthesize_local(gen,packet,bp,alternative);scm=SCM(model)
                edges=assess(gen,packet,model);selection=select_paths(scm)
                paths=selection['paths'];attr=coalitions(scm,paths)
                # Alternate reference: factual parent value; a documented null contrast.
                factual=scm.solve();factual_refs={(a,b):factual[a] for a,b in scm.graph.edges}
                null=coalitions(scm,paths,references=factual_refs)
                # A second nonzero/reference alternative uses the far endpoint of each domain.
                flipped={(a,b):domain(scm.nodes[a])[-1] if scm.nodes[a]['reference']!=domain(scm.nodes[a])[-1] else domain(scm.nodes[a])[0] for a,b in scm.graph.edges}
                alternate_refs=coalitions(scm,paths,references=flipped)
                groups=disjoint_mechanism_groups(paths)
                grouped=coalitions(scm,paths,groups=groups)
                clusters={s['id']:s['cluster_id'] for s in packet['segments']}
                weighted=evidence_priority(paths,attr,edges,clusters)
                uniform=evidence_priority(paths,attr,edges,clusters,True)
                geometric=evidence_priority(paths,attr,edges,clusters,False,'geometric')
                # Fixed twelve structural queries; automatic execution, no literary gold labels.
                query_nodes=[n for n in scm.order if n!=model['outcome']][:12]
                queries=[]
                for index,n in enumerate(query_nodes):
                    values=scm.solve(interventions={n:scm.nodes[n]['reference']})
                    queries.append({'id':'q%d'%index,'kind':'retrospective_counterfactual','intervention':{n:scm.nodes[n]['reference']},'factual_outcome':factual[model['outcome']],'modeled_outcome':values[model['outcome']],'changed_nodes':{k:{'before':factual[k],'after':v} for k,v in values.items() if v!=factual[k]},'gold_available':False})
                trace={'outcome':model['outcome'],'baseline':attr['baseline'],'full':attr['full'],'paths':weighted['paths'],'queries':queries[:3]}
                explanation=gen.call('application_explanation','Produce a concise explanation strictly from this execution trace. Do not claim historical probability, human verification, or objective responsibility. Return {"text":"explanation","numeric_claims":[{"field":"baseline OR full","value":0}],"path_ids":["p1"]}. Explain assumptions and inhibitory/zero contributions honestly.\n'+json.dumps(trace),2048,2027+alternative)
                numeric_ok=all(c.get('field') in ('baseline','full') and c['value']==trace[c['field']] for c in explanation.get('numeric_claims',[]))
                paths_ok=set(explanation.get('path_ids',[]))<={'p%d'%(i+1) for i in range(len(paths))}
                record={'case':case,'model':model,'diagnostics':diagnostics,'repair_failures':failures,'edge_evidence':edges,'selection':selection,'attribution':attr,
                        'reference_sensitivity':{'factual_reference_null':null,'domain_endpoint_alternative':alternate_refs,'alternative_interpretation':'domain endpoint stress test, not necessarily a plausible historical scenario'},
                        'disjoint_groups':{'groups':groups,'attribution':grouped},'evidence_priority':weighted,'uniform_priority':uniform,'geometric_priority':geometric,
                        'queries':queries,'explanation':explanation,'explanation_checks':{'structured_numeric_claims':numeric_ok,'path_ids':paths_ok,'free_text_semantic_verification':'not independently validated'},'source_audit':bp['source_audit']}
                atomic_json(dest,record);print('ACCEPTED',case['id'],alternative,len(model['nodes']),flush=True)
            except Exception as e:
                failure={'case':case['id'],'alternative':alternative,'error':str(e)}
                atomic_json(folder/('failed_alternative_%d.json'%alternative),failure)
                with open(gen.root/'results/failures.jsonl','a') as f:f.write(json.dumps(failure)+'\n')
                print('FAILED',case['id'],alternative,str(e)[:350],flush=True)
        atomic_json(gen.run/'inference_usage.json',gen.summary())

if __name__=='__main__':
    import sys
    run_application(sys.argv[1] if len(sys.argv)>1 else '.')
