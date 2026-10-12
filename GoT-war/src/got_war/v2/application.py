"""Source-context-first flagship construction; no story-specific causes or rules."""
import collections
import copy
import itertools
import json
from pathlib import Path
import re
import time
import networkx as nx
from ..budget import atomic_json
from ..structural_programs import SCM, InvalidModel, check_spec, valid_value
from ..attribution import select_paths, evidence_priority
from .runtime import paths, V2Generator
from .mechanisms import fingerprint, inspect_mechanism, outcome_sets
from .paths import edge_support, game_report, explain_query
from .explanations import generate as explain, reviewer_controls

PROTOCOL='v2-context-direction-function-1'


def node_view(node):
    """Operational interface without nested previous reviews or full probe logs."""
    keys=('id','label','definition','actor','type','values','bounds','observed','reference','reference_meaning',
          'event_time','statement_time','time','proposition_kind','event_status','segments','parents','mechanism_hint',
          'expr','noise','function_identification','assumptions')
    return {k:node[k] for k in keys if k in node}


def behavior_view(report):
    keys=('equation','coverage','rows','necessary_for_one','sufficient_for_one','joint_enabling','substitution')
    result={k:report[k] for k in keys}
    result['parent_polarities']={r['parent']:r['polarity'] for r in report['parent_changes']}
    return result


class Construction:
    def __init__(self, root, case_id='five_kings'):
        self.root,self.run,self.results=paths(root)
        self.gen=V2Generator(root)
        self.packet=json.loads((self.root/('.private/v2/'+case_id+'_packet.json')).read_text())
        self.segments={s['id']:s for s in self.packet['segments']}
        self.case=next(c for c in json.loads((self.root/'configs/application_v2.json').read_text())['cases'] if c['id']==case_id)
        self.folder=self.run/'application'/case_id;self.folder.mkdir(parents=True,exist_ok=True)

    def artifact(self, name, prompt, validator=lambda x:x, tokens=2048, schema=None):
        specification={'protocol':PROTOCOL,'prompt':prompt,'tokens':tokens}
        if schema is not None:specification['schema']=schema
        contract=fingerprint(specification)
        destination=self.folder/(name+'_'+contract[:12]+'.json')
        if destination.exists():return json.loads(destination.read_text())['accepted']
        failures=[];base=prompt
        for attempt in range(3):
            response=None
            try:
                response=self.gen.call('v2_app_'+name.split('_')[0]+('_repair' if attempt else ''),prompt,tokens,2801+attempt,schema=schema)
                accepted=validator(response)
                atomic_json(destination,{'contract':contract,'accepted':accepted,'response':response,'failed_attempts':failures})
                return accepted
            except Exception as error:
                failure={'attempt':attempt,'response':response,'error':type(error).__name__+': '+str(error)}
                failures.append(failure);atomic_json(self.folder/(name+'_'+contract[:12]+'_failed_'+str(attempt)+'.json'),failure)
                prompt=base+'\nVALIDATION DIAGNOSTIC: '+str(error)+'\nCorrect only using the supplied evidence and schema. Do not invent a causal connection or residual to satisfy validation.'
        raise RuntimeError(name+' exhausted two targeted repairs: '+failures[-1]['error'])

    def context(self, ids=(), query='', limit=14500):
        chosen=list(dict.fromkeys(i for i in ids if i in self.segments))
        words={w.lower() for w in re.findall(r'[A-Za-z]{4,}',query)}
        ranked=sorted(self.segments, key=lambda k:(-sum(w in self.segments[k]['text'].lower() for w in words),k))
        chunks=[];used=0;selected=[]
        for ident in chosen+ranked:
            if ident in selected:continue
            segment=self.segments[ident]
            text='['+ident+'] '+segment['episode']+' '+segment['source_type']+'\n'+segment['text']
            if used+len(text)>limit:
                if ident in chosen and not chunks:
                    text=text[:limit]+'\n[context truncated at declared character budget]'
                else:continue
            chunks.append(text);selected.append(ident);used+=len(text)+2
            if used>limit*.9:break
        return '\n\n'.join(chunks),selected

    def inventory(self):
        final=self.folder/'inventory.json'
        if final.exists():return json.loads(final.read_text())
        batches=[];current=[];length=0
        for segment in self.packet['segments']:
            if current and length+len(segment['text'])>8000:
                batches.append(current);current=[];length=0
            current.append(segment);length+=len(segment['text'])
        if current:batches.append(current)
        facts=[];rejected=[]
        for index,batch in enumerate(batches):
            allowed={s['id'] for s in batch}
            source='\n\n'.join('['+s['id']+'] '+s['episode']+'\n'+s['text'] for s in batch)
            prompt=('Read these contextual television transcript passages. Discover up to SIX substantive events, states, reports or beliefs relevant to explaining the supplied outcome, including plausible enabling, inhibiting or contextual influences. '
                'Do not fill gaps from model memory. Do not infer the truth of a character statement merely because it was uttered. Return {"facts":[{"label":"short event",'
                '"definition":"precise claim, at most 30 words","actor":"actor","event_time":"episode or unknown",'
                '"statement_time":"episode","proposition_kind":"narrative_fact|reported_claim|character_belief",'
                '"segments":["exact supplied ID"],"relevance":"short reason", "influence_clue":"contextual causal claim or unresolved"}]}. '
                'An empty facts array is valid. Do not pad. No equations yet.\nOUTCOME: '+self.case['outcome']+'\nPASSAGES:\n'+source)
            def validate(response):
                if not isinstance(response.get('facts'),list):raise ValueError('facts must be an array')
                return response['facts'][:6]
            output=self.artifact('inventory_%03d'%index,prompt,validate,2048)
            for row in output:
                if (not isinstance(row,dict) or not row.get('definition') or not row.get('segments') or set(row['segments'])-allowed
                        or row.get('proposition_kind') not in ('narrative_fact','reported_claim','character_belief')):
                    rejected.append({'batch':index,'row':row,'reason':'invalid source/claim contract'});continue
                facts.append(dict(row,id='f%04d'%len(facts)))
            atomic_json(self.folder/'inventory_checkpoint.json',{'batches_completed':index+1,'batches':len(batches),'facts':facts,'rejections':rejected})
            print('V2_APP_INVENTORY',index+1,len(batches),len(facts),flush=True)
        record={'protocol':PROTOCOL,'packet_sha256':self.packet['packet_sha256'],'facts':facts,'rejections':rejected}
        atomic_json(final,record);return record

    def select_variables(self, inventory):
        facts=inventory['facts'];shortlist=[]
        for start in range(0,len(facts),30):
            batch=facts[start:start+30];known={r['id']:r for r in batch}
            prompt=('Select up to TEN nonduplicate, causally relevant documented claims from this inventory. Preserve a range of potentially enabling, inhibiting and background events; do not select merely by chronology or word overlap. '
                'Return {"selected_ids":["f0000"],"limitations":["unresolved issue"]}. Selection is provisional; equations and source support will be reviewed later. '
                'Use only the supplied IDs.\nOUTCOME: '+self.case['outcome']+'\nINVENTORY:\n'+json.dumps(batch))
            def check(response):
                ids=response.get('selected_ids',[])
                if not isinstance(ids,list) or set(ids)-set(known):raise ValueError('Use only supplied fact IDs')
                return list(dict.fromkeys(ids))[:10]
            chosen=self.artifact('shortlist_%03d'%start,prompt,check,1536)
            shortlist.extend(known[i] for i in chosen)
        # Hierarchical selection keeps long inventories within the cached model's
        # context window; the LLM, not an analyst-specified cause list, selects.
        if len(shortlist)>45:
            reduced=[]
            for start in range(0,len(shortlist),30):
                batch=shortlist[start:start+30];known={r['id']:r for r in batch}
                prompt=('Select up to TEN distinct documented claims most useful for constructing an explanatory variable schema for the stated outcome. '
                    'Preserve enabling, inhibiting and contextual possibilities; do not fabricate missing mechanisms. Return {"selected_ids":["fact ID"]}. '
                    'Only supplied IDs are allowed.\nOUTCOME: '+self.case['outcome']+'\nINVENTORY:\n'+json.dumps(batch))
                def check(response):
                    ids=response.get('selected_ids',[])
                    if not isinstance(ids,list) or set(ids)-set(known):raise ValueError('Use only supplied fact IDs')
                    return list(dict.fromkeys(ids))[:10]
                reduced.extend(known[i] for i in self.artifact('shortlist_reduce_%03d'%start,prompt,check,1536))
            shortlist=reduced
        compact=[{k:r[k] for k in ('id','label','definition','actor','event_time','proposition_kind','segments','influence_clue') if k in r} for r in shortlist]
        known_facts={r['id']:r for r in shortlist}
        prompt=('Select and synthesize a compact set of 8-16 substantive explanatory concepts if supported; fewer is valid. Do not copy the entire inventory. '
            'Return {"concepts":[{"label":"short readable event label","source_facts":["supplied fact ID"],"scope_note":"brief operational distinction"}],'
            '"outcome":{"label":"short label for the specified conflict outcome","source_facts":["evidence fact IDs"],"scope_note":"operational distinction"},"assumptions":[]}. '
            'The outcome is separately specified by the research question; choose its supporting factual evidence rather than searching for a preexisting W identifier. '
            'Software assigns identifiers after your content is generated. Do not invent causes, equations or edges. Preserve fact/report/belief distinctions. '
            'Do not select only a chronological prefix; consider the full supplied horizon. Every concept and the outcome need supplied fact references.\nOUTCOME: '+self.case['outcome']+'\nINVENTORY:\n'+json.dumps(compact))
        concept_schema={'type':'object','properties':{'label':{'type':'string','maxLength':100},'source_facts':{'type':'array','items':{'type':'string','enum':list(known_facts)},'minItems':1,'maxItems':5},'scope_note':{'type':'string','maxLength':240}},'required':['label','source_facts','scope_note'],'additionalProperties':False}
        schema={'type':'object','properties':{'concepts':{'type':'array','items':concept_schema,'minItems':2,'maxItems':16},'outcome':concept_schema,'assumptions':{'type':'array','items':{'type':'string'},'maxItems':6}},'required':['concepts','outcome','assumptions'],'additionalProperties':False}
        def check_plan(response):
            concepts=response.get('concepts',[])
            if not 2<=len(concepts)<=16:raise ValueError('Need 2-16 explanatory concepts plus the specified outcome')
            concepts=[dict(n,id='X%02d'%(i+1)) for i,n in enumerate(concepts)]+[dict(response['outcome'],id='W')]
            if any(not n.get('source_facts') or set(n['source_facts'])-set(known_facts) for n in concepts):raise ValueError('Concepts must cite supplied fact IDs')
            return {'outcome':'W','concepts':concepts,'assumptions':response.get('assumptions',[])}
        plan=self.artifact('concept_plan',prompt,check_plan,3072,schema=schema);nodes=[]
        for concept in plan['concepts']:
            facts=[known_facts[i] for i in concept['source_facts']]
            context,ids=self.context([s for r in facts for s in r['segments']],concept['label']+' '+concept.get('scope_note',''),11000)
            prompt=('Operationalize ONE source-derived concept, using the actual passage context. Do not invent its factual state. '
                'A report/belief denotes the report/belief, not unverified truth of its content. '
                'Return {"node":{"id":"'+concept['id']+'","label":"readable event label","definition":"precise operational state",'
                '"actor":"actor","type":"bool|category|int|float","values":["only if categorical"],"bounds":[0,1],'
                '"observed":1,"reference":0,"reference_meaning":"explicit meaningful comparison",'
                '"event_time":"episode code or unknown","statement_time":"episode code or unknown",'
                '"proposition_kind":"narrative_fact|reported_claim|character_belief","segments":["supplied source ID"]}}. '
                'No parents or equation yet. The designated outcome '+plan['outcome']+' must be Boolean and mean exactly the specified conflict outcome. '
                'Other domains are free when justified. Categorical states must be mutually exclusive, and observed/reference must be members of values. '
                'Boolean states use integer 0/1. Select exactly ONE proposition_kind value, never the literal pipe-separated list. '
                'The segments field uses scene IDs from PASSAGES, never inventory fact IDs. Do not conflate distinct concepts or move the target event later.\nOUTCOME: '+self.case['outcome']+
                '\nCONCEPT:\n'+json.dumps(concept)+'\nEXTRACTED FACTS:\n'+json.dumps(facts)+
                '\nOTHER CONCEPTS:\n'+json.dumps([{'id':c['id'],'label':c['label']} for c in plan['concepts']])+'\nPASSAGES:\n'+context)
            def check_node(response):
                node=response['node'];check_spec(node)
                if node['id']!=concept['id']:raise ValueError('Keep the specified concept ID')
                if not valid_value(node['observed'],node) or not valid_value(node['reference'],node):raise ValueError('Invalid factual/reference domain: '+json.dumps({k:node.get(k) for k in ('type','values','bounds','observed','reference')})+'. Generate a coherent domain and states using only the passage evidence.')
                if not node.get('definition') or not node.get('reference_meaning'):raise ValueError('Definition and meaningful reference required')
                if not node.get('segments') or set(node['segments'])-set(ids):raise ValueError('Cite only supplied passage IDs')
                if node['id']==plan['outcome'] and node['type']!='bool':raise ValueError('The active-conflict outcome requires a Boolean indicator')
                match=re.fullmatch(r's(\d+)e(\d+)',node.get('event_time','').lower())
                node['time']=int(match[1])*100+int(match[2]) if match else None
                if node['time'] and node['time']>self.case['endpoint_code']:raise ValueError('A later event cannot cause this outcome')
                node['source_facts']=concept['source_facts'];return node
            properties={k:{'type':'string','maxLength':350 if k=='definition' else 200} for k in ('id','label','definition','actor','reference_meaning','event_time','statement_time')}
            properties['id']={'const':concept['id']}
            properties.update(type={'enum':['bool','category','int','float']},
                values={'type':'array','items':{'type':'string'},'maxItems':12},bounds={'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2},
                observed={},reference={},proposition_kind={'enum':['narrative_fact','reported_claim','character_belief']},
                segments={'type':'array','items':{'type':'string','enum':ids},'minItems':1,'maxItems':8})
            variants=[]
            for dtype,state in [('bool',{'type':'integer','enum':[0,1]}),('category',{'type':'string'}),('int',{'type':'integer'}),('float',{'type':'number'})]:
                spec={'type':'object','properties':dict(properties,type={'const':dtype},observed=state,reference=state),
                    'required':['id','label','definition','actor','type','observed','reference','reference_meaning','event_time','statement_time','proposition_kind','segments']+(['values'] if dtype=='category' else ['bounds'] if dtype in ('int','float') else []),'additionalProperties':False}
                variants.append(spec)
            variable_schema={'type':'object','properties':{'node':{'anyOf':variants}},'required':['node'],'additionalProperties':False}
            nodes.append(self.artifact('variable_'+concept['id'],prompt,check_node,1536,schema=variable_schema))
            atomic_json(self.folder/'variables_checkpoint.json',{'outcome':plan['outcome'],'nodes':nodes,'assumptions':plan.get('assumptions',[])})
        response={'outcome':plan['outcome'],'nodes':nodes,'assumptions':plan.get('assumptions',[])}
        atomic_json(self.folder/'variables.json',response);return response

    def audit_events(self, blueprint):
        nodes=copy.deepcopy(blueprint['nodes']);audits=[]
        for node in nodes:
            context,ids=self.context(node['segments'],node['definition'])
            prompt=('Assess this operational variable against the full passage context supplied. Separately check actor/action, factual state, reference semantics, event time, statement time and whether a reported claim/belief has been mistaken for narrative truth. '
                'Return {"event_supported":true,"factual_state_supported":true,"status_matches_definition":true,"reference_meaning_clear":true,'
                '"event_time":"consistent|unresolved|contradicted","information_time":"consistent|unresolved|contradicted","contradictions":[],"questions":[],"reason":"brief"}. '
                'Be strict. A citation match is not entailment; unsupported stays unsupported. No independent human review is implied.\nVARIABLE:\n'+json.dumps(node)+'\nPASSAGES:\n'+context)
            audit=self.artifact('eventaudit_'+node['id'],prompt,tokens=1536)
            passed=all(audit.get(k) is True for k in ('event_supported','factual_state_supported','status_matches_definition','reference_meaning_clear')) and not audit.get('contradictions')
            status={'narrative_fact':'established','reported_claim':'reported_claim','character_belief':'character_belief'}.get(node.get('proposition_kind'),'unassessed')
            node['event_status']=status if passed else 'unsupported'
            node['event_audit']=audit;audits.append({'node':node['id'],'passages':ids,**audit})
        result=dict(blueprint,nodes=nodes,event_audits=audits)
        atomic_json(self.folder/'event_audit.json',result)
        return result

    def discover_graph(self, blueprint, revision_note=''):
        nodes=blueprint['nodes'];ids={n['id'] for n in nodes}
        source_ids=[s for n in nodes for s in n['segments']]
        context,_=self.context(source_ids,self.case['outcome'],12000)
        schema=[{k:n.get(k) for k in ('id','label','definition','actor','type','observed','reference','event_time','statement_time','event_status','segments')} for n in nodes]
        prompt=('Discover direct directional influences for these variables from the evidence, not their mere chronology. '
            'Return {"parents":{"node_ID":["parent_ID"]},"mechanism_hints":{"node_ID":"brief source/assumption distinction"},'
            '"unresolved_backgrounds":[],"assumptions":[],"representation_questions":[]}. '
            'Return a DAG and a parents entry for every node, using only these IDs. At most four direct parents per node is an inspection budget, not a demand for four. '
            'Roots are declared scope boundaries. Do not make outcome manifestations necessary causes of the outcome by definition. '
            'A supported causal direction need not identify a function; explicitly state missing context. Unsupported proposals stay hypotheses. '
            'You may leave unrelated variables outside the outcome ancestry rather than invent links.\nOUTCOME: '+self.case['outcome']+
            '\nVARIABLES:\n'+json.dumps(schema)+'\nPASSAGES:\n'+context+'\nPRIOR REPRESENTATION DIAGNOSTIC: '+revision_note)
        def validate(response):
            parents=response.get('parents',{})
            if set(parents)!=ids:raise ValueError('Provide one parents entry for every supplied variable ID')
            graph=nx.DiGraph();graph.add_nodes_from(ids)
            for child,ps in parents.items():
                if not isinstance(ps,list) or len(ps)>4 or len(set(ps))!=len(ps) or set(ps)-ids or child in ps:raise ValueError('Invalid parent set for '+child)
                graph.add_edges_from((p,child) for p in ps)
            if not nx.is_directed_acyclic_graph(graph):raise ValueError('Dependencies contain a cycle; reconsider the representation using evidence')
            mapping={n['id']:n for n in nodes}
            for a,b in graph.edges:
                if mapping[a]['time'] is not None and mapping[b]['time'] is not None and mapping[a]['time']>mapping[b]['time']:raise ValueError('Future event cannot cause earlier event: '+a+'>'+b)
            return response
        graph=self.artifact('graph',prompt,validate,3072)
        relation=nx.DiGraph();relation.add_nodes_from(ids);relation.add_edges_from((p,c) for c,ps in graph['parents'].items() for p in ps)
        ancestors=nx.ancestors(relation,blueprint['outcome'])|{blueprint['outcome']}
        retained=[dict(n,parents=graph['parents'][n['id']],mechanism_hint=graph.get('mechanism_hints',{}).get(n['id'],'')) for n in nodes if n['id'] in ancestors]
        if len(retained)<2:raise ValueError('No explanatory outcome ancestry; preserve the failed graph instead of padding')
        result=dict(blueprint,nodes=retained,graph_proposal=graph,pruned_unrelated=sorted(ids-ancestors))
        atomic_json(self.folder/'graph.json',result);return result

    def local_models(self, blueprint):
        mapping={n['id']:n for n in blueprint['nodes']};options={};audits=[]
        contract=(self.root/'prompts/ast_contract.txt').read_text()
        for node in blueprint['nodes']:
            parents=[mapping[p] for p in node['parents']]
            context,source_ids=self.context(node['segments']+[s for p in parents for s in p['segments']],node['definition']+' '+node.get('mechanism_hint',''))
            prompt=(contract+'\nGenerate one to THREE defensible fixed mechanisms for this target using exactly the declared parent inputs. '
                'Alternatives must differ in behavior, not wording; one is valid if the representation/evidence permits no defensible alternative. '
                'Do not manufacture unequal path shares or diversity. Every declared parent must matter in some valid context. '
                'Unknown exact functional form is an explicit assumption even when a causal influence is supported. '
                'A root uses its own declared external identity input U_'+node['id']+'. '
                'Nonroot background inputs are allowed ONLY if independently operationalized, source-referenced and justified as a substantive fixed context, never a residual to force factual fit. '
                'Return {"variants":[{"expr":{},"background":{},"description":"precise behavior of this expression","short_mechanism":"at most eight words",'
                '"assumptions":[],"function_identification":"identified|partially_constrained|unidentified"}],"representation_questions":[]}. '
                'Each added background specification needs type/domain, observed, definition, source_segments and substantive_justification. '
                'Do not claim an AND rule makes either input sufficient. If the story proceeded despite an event, do not silently make that event necessary. '
                'You may explicitly flag an inadequate representation instead of inventing a rule.\nTARGET:\n'+json.dumps(node_view(node))+
                '\nPARENTS:\n'+json.dumps([node_view(p) for p in parents])+'\nPASSAGES:\n'+context)
            def validate(response):
                variants=response.get('variants',[]);accepted=[];rejections=[]
                for index,variant in enumerate(variants[:3]):
                    try:
                        bg=copy.deepcopy(variant.get('background',{}));local_nodes=[]
                        for p in parents:
                            uid='CONTEXT_'+p['id'];bg[uid]={k:p[k] for k in ('type','values','bounds','observed') if k in p}
                            local_nodes.append(dict(p,parents=[],noise=[uid],expr={'noise':uid}))
                        if not parents:
                            uid='U_'+node['id'];bg[uid]={k:node[k] for k in ('type','values','bounds','observed') if k in node}
                            noise=[uid]
                        else:
                            noise=[key for key in variant.get('background',{})]
                            for key in noise:
                                spec=bg[key]
                                if not all(spec.get(k) for k in ('definition','source_segments','substantive_justification')) or set(spec['source_segments'])-set(self.segments):raise ValueError('Unjustified nonroot background '+key)
                        target=dict(node,expr=variant['expr'],noise=noise);local_nodes.append(target)
                        local=SCM({'nodes':local_nodes,'background':bg,'outcome':node['id']})
                        behavior=inspect_mechanism(local,node['id'])
                        if behavior['signature'] not in {a['behavior']['signature'] for a in accepted}:
                            accepted.append(dict(variant,noise=noise,behavior=behavior,original_index=index))
                    except Exception as error:rejections.append({'index':index,'error':str(error),'variant':variant})
                if not accepted:raise ValueError('No admissible local function: '+json.dumps(rejections)[:1400]+'; representation questions: '+str(response.get('representation_questions')))
                return {'variants':accepted,'rejections':rejections,'representation_questions':response.get('representation_questions',[])}
            accepted=self.artifact('mechanism_'+node['id'],prompt,validate,3072)
            # Inspect descriptions against actual behavior, not just the factual row.
            compact=[{'index':i,'description':v.get('description'),'short_mechanism':v.get('short_mechanism'),
                'assumptions':v.get('assumptions',[]),'background':v.get('background',{}),'behavior':behavior_view(v['behavior'])} for i,v in enumerate(accepted['variants'])]
            audit_context,audit_ids=self.context(source_ids,node['definition'],10500)
            review_prompt=('Audit these generated local mechanisms using their actual truth tables/probes and the passage context. '
                'Separate source support for direction from identification of the exact function. '
                'Return {"variants":[{"index":0,"description_matches_behavior":true,"short_label_matches_behavior":true,'
                '"source_compatibility":"compatible_hypothesis|contradicted|unresolved","background_is_factual_patch":false,"questions":[],"reason":"brief"}]}. '
                'Compatible hypothesis does not mean identified. An AND requires all conjuncts for output 1; OR may provide substitutes. '
                'Reject claims of sufficiency/necessity that the table contradicts. Unrestricted residuals are not admissible.\nTARGET:\n'+json.dumps(node_view(node))+
                '\nMECHANISMS:\n'+json.dumps(compact)+'\nPASSAGES:\n'+audit_context)
            review=self.artifact('functionaudit_'+node['id'],review_prompt,tokens=2048)
            by_index={r.get('index'):r for r in review.get('variants',[]) if isinstance(r,dict)}
            retained=[]
            for i,variant in enumerate(accepted['variants']):
                audit=by_index.get(i,{'source_compatibility':'unresolved','questions':['Missing reviewer item']})
                if audit.get('source_compatibility')=='contradicted' or audit.get('background_is_factual_patch') is True:continue
                variant['semantic_review']=audit
                variant.setdefault('short_mechanism','Assumed rule; inspect behavior table')
                variant['generated_description']=variant.get('description','')
                variant['description']=variant['behavior']['derived_description']
                if audit.get('short_label_matches_behavior') is not True:variant['short_mechanism']='Assumed rule; inspect behavior table'
                retained.append(variant)
            if not retained:raise ValueError('All local alternatives contradicted or use factual-patch backgrounds: '+node['id'])
            options[node['id']]=retained;audits.append({'node':node['id'],'source_ids':source_ids,'review_source_ids':audit_ids,'review':review,'formal_rejections':accepted['rejections']})
            atomic_json(self.folder/'local_options_checkpoint.json',{'options':options,'audits':audits})
        atomic_json(self.folder/'local_options.json',{'options':options,'audits':audits});return options

    def evidence(self, model):
        nodes={n['id']:n for n in model['nodes']}
        for node in model['nodes']:
            node['influences']=[]
            if not node['parents']:continue
            parents=[nodes[p] for p in node['parents']]
            context,ids=self.context(node['segments']+[s for p in parents for s in p['segments']],node['definition'])
            prompt=('Assess EACH proposed parent-to-child influence from the contextual passages. Do not judge the exact equation as if it were the directional claim. '
                'Mere chronology/co-occurrence is unsupported. Never raise a score to make a ranking nonzero. '
                'Return {"influences":[{"parent":"ID","direction_status":"explicit|contextually_supported|unsupported|unassessed",'
                '"segments":["supporting passage ID"],"direction_reason":"specific causal language/context, or precise gap",'
                '"contradictions":[],"temporal_status":"consistent|unresolved|contradicted","information_status":"consistent|unresolved|contradicted",'
                '"exact_function_identification":"identified|partially_constrained|unidentified","function_assumptions":[],"review_questions":[]}]}. '
                'A reported claim or belief can be causally relevant as such, but not automatically as a true external event. '
                'Source dependence precludes treating multiple accounts of one episode as independent corroboration.\nCHILD:\n'+json.dumps(node_view(node))+
                '\nPARENTS:\n'+json.dumps([node_view(p) for p in parents])+'\nPASSAGES:\n'+context)
            def validate(response):
                edges=response.get('influences',[])
                if sorted(e.get('parent') for e in edges)!=sorted(node['parents']):raise ValueError('Assess each supplied parent exactly once')
                for edge in edges:
                    if set(edge.get('segments',[]))-set(ids):raise ValueError('Use references from the supplied context only')
                    if edge.get('direction_status') not in ('explicit','contextually_supported','unsupported','unassessed'):raise ValueError('Invalid directional status')
                return edges
            node['influences']=self.artifact('direction_'+node['id'],prompt,validate,2048)
        return model

    def build(self):
        inventory=self.inventory();variables=self.audit_events(self.select_variables(inventory));last_error=None
        for representation_attempt in range(2):
            try:
                blueprint=self.discover_graph(variables,str(last_error or ''))
                options=self.local_models(blueprint)
                break
            except (RuntimeError,ValueError) as error:
                last_error=error;atomic_json(self.folder/('representation_failure_%d.json'%representation_attempt),{'error':str(error),'variables':variables})
                if representation_attempt:raise
                context,_=self.context([s for n in variables['nodes'] for s in n['segments']],self.case['outcome'],16000)
                prompt=('Revise this inadequate variable representation using ONLY the contextual evidence. You may alter definitions, domains, references or replace/drop unsupported variables; do not supply a desired outcome mechanism or residual merely to force agreement. '
                    'Return {"outcome":"ID","nodes":[same variable schema, with time numeric episode code or null],"assumptions":[]}. '
                    'Keep the supplied outcome meaning/time fixed. Every factual state needs source references.\nOUTCOME: '+self.case['outcome']+'\nDIAGNOSTIC: '+str(error)+
                    '\nCURRENT VARIABLES:\n'+json.dumps(variables['nodes'])+'\nPASSAGES:\n'+context)
                def check(response):
                    for n in response['nodes']:
                        check_spec(n)
                        if not valid_value(n['observed'],n) or not valid_value(n['reference'],n) or not n.get('segments') or set(n['segments'])-set(self.segments):raise ValueError('Invalid revised variable')
                    return response
                variables=self.audit_events(self.artifact('representation_revision',prompt,check,4096))
        identifiers=[n['id'] for n in blueprint['nodes']]
        choices=[dict.fromkeys(identifiers,0)]
        for ident in identifiers:
            for index in range(1,len(options[ident])):
                choice=dict.fromkeys(identifiers,0);choice[ident]=index;choices.append(choice)
        choices=choices[:12]  # deterministic local perturbations, not selected by allocation values
        models=[];seen=set()
        for choice in choices:
            nodes=[];background={}
            for original in blueprint['nodes']:
                variant=options[original['id']][choice[original['id']]]
                node=dict(original,**{k:variant[k] for k in ('expr','noise','description','short_mechanism')})
                node.update(assumptions=variant.get('assumptions',[]),function_identification=variant.get('function_identification','unidentified'),behavior=variant['behavior'])
                background.update(variant.get('background',{}))
                if not node['parents']:
                    background['U_'+node['id']]={k:node[k] for k in ('type','values','bounds','observed') if k in node}
                nodes.append(node)
            model={'id':self.case['id']+'_v2_m%02d'%len(models),'outcome':blueprint['outcome'],'nodes':nodes,'background':background,
                'assumptions':blueprint.get('assumptions',[])+blueprint.get('graph_proposal',{}).get('assumptions',[]),
                'outcome_definition':self.case['outcome'],'protocol':PROTOCOL,'local_choice':choice}
            scm=SCM(model);signature=fingerprint([inspect_mechanism(scm,n)['signature'] for n in scm.order])
            if signature not in seen:models.append(model);seen.add(signature)
        principal=self.evidence(models[0])
        for model in models[1:]:
            for node in model['nodes']:node['influences']=copy.deepcopy(next(n for n in principal['nodes'] if n['id']==node['id'])['influences'])
        scm=SCM(principal);selection=select_paths(scm,maximum=8);questions=[]
        for node in principal['nodes']:
            if node['id']!=principal['outcome']:questions.append({'id':'q%02d'%len(questions),'do':{node['id']:node['reference']},'target':principal['outcome']})
        boundary=selection['source_boundary']
        for a,b in list(itertools.combinations(sorted(boundary),2))[:3]:questions.append({'id':'q%02d'%len(questions),'do':{a:scm.nodes[a]['reference'],b:scm.nodes[b]['reference']},'target':principal['outcome']})
        answers=outcome_sets(models,questions);records=[]
        for model in models:
            current=SCM(model);game=game_report(current,selection['paths']);support=edge_support(model)
            weighted=evidence_priority(selection['paths'],game,support,{s['id']:s['dependence_cluster'] for s in self.packet['segments']})
            factual_refs={(a,b):current.nodes[a]['observed'] for a,b in current.graph.edges}
            endpoint_refs={(a,b):(1-current.nodes[a]['reference'] if current.nodes[a]['type']=='bool' else current.nodes[a]['observed']) for a,b in current.graph.edges}
            record={'model':model,'selection':selection,'attribution':game,'edge_evidence':support,'evidence_priority':weighted,
                'ranking_available':any(s['priority']>0 for s in weighted['segments']),
                'reference_sensitivity':{'factual_null':game_report(current,selection['paths'],factual_refs),'domain_endpoint_stress':game_report(current,selection['paths'],endpoint_refs)},
                'path_selection_sensitivity':{'four_paths':game_report(current,select_paths(current,maximum=4)['paths'])},
                'queries':[{**q,'modeled_outcome':current.solve(interventions=q['do'])[q['target']]} for q in questions]}
            records.append(record)
        principal_root=max(boundary,key=lambda n:(scm.graph.out_degree(n),n)) if boundary else principal['nodes'][0]['id']
        query=next((q for q in questions if list(q['do'])==[principal_root]),questions[0])
        trace=explain_query(principal,query,models)
        prose_ids=[s for path in trace['paths']['paths'] for ident in path for s in scm.nodes[ident]['segments']]
        prose_context,prose_sources=self.context(prose_ids,self.case['outcome'],8000)
        trace['source_context']=prose_context
        trace['source_context_private']=True
        trace['source_review_scope']='Bounded actual passage context for selected paths; missing support remains unverifiable. Same-model review; researcher adjudication pending.'
        explanation=explain(self.gen,trace,2801)
        control=reviewer_controls(self.gen,trace,2801)
        atomic_json(self.folder/'explanation_context.private.json',{'source_context':prose_context,'source_ids':prose_sources})
        trace['source_context_sha256']=__import__('hashlib').sha256(trace.pop('source_context').encode()).hexdigest()
        output={'case':self.case,'protocol':PROTOCOL,'packet_sha256':self.packet['packet_sha256'],'records':records,'queries':questions,'outcome_sets':answers,
            'explanation_query_policy':'Largest out-degree source boundary node; lexical tie, before observing intervention results.',
            'explanation':explanation,'reviewer_controls':control,'trace':trace,'prose_review_source_ids':prose_sources,
            'alternatives':{'retained_functionally_distinct':len(models),'distinct_query_vectors':len({tuple(q['modeled_outcome'] for q in r['queries']) for r in records}),
                'local_options':{n:len(v) for n,v in options.items()},'cartesian_options':__import__('math').prod(len(v) for v in options.values()),
                'coverage':'Baseline plus single-local-function changes, at most 12, deterministic order; not exhaustive across combined changes or alternative graphs. No frequency interpretation.'},
            'source_review':'Automated same-model contextual assessment; independent researcher adjudication pending.'}
        atomic_json(self.folder/'final.json',output);return output


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--case',default='five_kings');p.add_argument('--inventory-only',action='store_true');a=p.parse_args()
    construction=Construction(a.root,a.case)
    try:
        output=construction.inventory() if a.inventory_only else construction.build()
        print('V2_FLAGSHIP_DONE',len(output.get('facts',[])),len(output.get('records',[])),flush=True)
    except Exception as error:
        atomic_json(construction.folder/'failure.json',{'error':type(error).__name__+': '+str(error),'at':time.time(),'protocol':PROTOCOL})
        raise
