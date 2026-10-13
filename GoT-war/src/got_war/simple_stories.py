"""Small story experiment: adapters around the existing finite SCM engine.

No story names, desired graphs or reference equations enter construction logic.
"""
import copy
from datetime import datetime, timezone
import hashlib
import itertools as it
import json
import lzma
from pathlib import Path
import re
import time

from .budget import atomic_json
from .v3.core import (build_family, fingerprint, local_family, predicate, query, solve,
                      validate_representation, verify_reported_result)
from .v4.application import expression, value

FROZEN_SHA = '12d1e7c00fd59dd570d94edf83d7b707c3975678f5b30367c4c657152859b302'
FOLDER = 'experiments/simple_stories'
RUN = 'runs/simple_stories_20261013'
MODEL = 'Qwen/Qwen3-14B-AWQ'

INSTRUCTIONS = '''Construct a small evidence-grounded Boolean structural causal model from ONLY the supplied numbered story. Discover your own variables and mechanisms, not remembered story details. Separate initial events, information/beliefs, actions, intermediate effects and final outcome. Distinguish a failed attempt from universal impossibility. Respect temporal scope. No minimum size; at most 9 variables and 3 parents per local function. Use meaningful event/state labels and informative edge phrases (never merely "and", "if", "causes" or "influences"). Every declared parent needs an edge description. Explain multi-parent interaction in the description.
Separate observations, proposed direction and exact-function knowledge. Use a restricted Boolean expression only if all its behavior is explicitly established by this supplied text (including plainly added rules). Otherwise use expression:null and partial rows/constraints; do not complete unknown rows for a definite answer. An observation establishes ONLY its factual row. The compiler adds factual rows from known observations. Fixed context variables have factual 0/1 and no equation; unknown root states may be endogenous with parents:[] and expression:null. Record background conditions and unknown behavior. Added rules are controlled assumptions, not traditional-story discoveries.
Return ONE compact JSON object, with no surrounding prose, exactly this general structure:
{"outcome":"generated variable ID", "scope_assumptions":["bounded context"],
 "variables":[{"id":"short ID", "label":"clear short event name", "meaning":"what 1 means", "actor":"who/what", "time":0, "factual":1, "kind":"narrative_fact", "boundary":"fixed_context", "source":["S1"], "basis":"explicit"}],
 "mechanisms":[{"child":"ID", "parents":["parent ID"], "description":"substantive process and joint conditions", "source":["S2"], "assumptions":[], "unknowns":[], "expression":null, "rows":[{"when":{"parent ID":1}, "allowed":[1], "source":["S2"], "basis":"evidence", "reason":"what is established"}],
 "edges":[{"parent":"parent ID", "label":"specific short causal phrase", "process":"substantive explanation of how this parent changes this child", "source":["S2"], "status":"contextual", "conditions":[], "gaps":[]}],
 "claims":[{"text":"EXACT substring of description", "type":"necessary", "when":{"parent ID":1}, "output":1}]}]}
Use only declared IDs in expressions: and, or, not, parentheses, 0, 1. Roots are fixed_context; other variables are endogenous. Factual may be null if unknown. kind is narrative_fact, reported_claim or character_belief. basis/status is explicit, contextual, hypothetical or unresolved. A mechanism is required for every endogenous variable. rows may be empty; no invented citations. source lists sentence IDs explaining the particular claim, not merely mentioning endpoints. All input domains are {0,1}.
For EVERY necessity/sufficiency/conjunction/inhibition or exact-function assertion in a description, supply a matching claims record that quotes that actual assertion. Claim types: necessary (when conjunction, output); sufficient (when conjunction, output); conjunction (when is ALL jointly required input values, output); inhibits (parent, global:true for universal non-increase plus a strict effect, false for only a possible strict effect); enables (parent, global likewise); exact (rule: a separately stated expression expressing the prose). Use exact for conditional disjunctions/identity rules. A necessity claim tests ALL completions of other inputs; an all-zero row is insufficient. Do not use an exact claim alone to disguise a separate necessity claim. Unknown descriptions can have claims:[] and must not assert universals. Keep descriptions concise and finish JSON.'''


def frozen(root):
    path = Path(root)/FOLDER/'frozen.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != FROZEN_SHA:
        raise ValueError('Frozen experiment changed; preserve original and publish an explicit correction')
    return json.loads(path.read_text())


def packet(story, version):
    segments=[]
    for s in story[version]:
        segments.append(dict(id=s['id'], text=s['text'], source_id=story['id']+'_'+version,
            url='frozen.json#'+story['id']+'/'+version+'/'+s['id'], episode='short narrative',
            start=0, end=len(s['text']), first_line=int(s['id'][1:]), last_line=int(s['id'][1:]),
            origin=s['origin']))
    return {'segments':segments,'packet_sha256':fingerprint(segments)}


def compile_model(draft, story, version, max_models=512):
    """Expand only schema/provenance metadata; never add narrative mechanisms."""
    diagnostics=schema_diagnostics(draft)
    if diagnostics:raise ValueError('Representation diagnostics: '+json.dumps(diagnostics))
    pack=packet(story,version);ps={s['id']:s for s in pack['segments']}
    def refs(ids, support):
        return [{'passage_id':ident,'quote':ps[ident]['text'],'supports':support} for ident in ids]
    variables=[];edges=[];mechanisms=[];functions=[]
    for v in draft['variables']:
        variables.append(dict(id=v['id'],label=v['label'],definition=v['meaning'],actor=v['actor'],
            domain=[0,1],factual=v['factual'],kind=v['kind'],event_time=v['time'],statement_time=v['time'],
            time_note='Generated ordinal narrative stage',event_status=v['basis'],boundary=v['boundary'],
            boundary_reason='Generated scope: '+ '; '.join(draft['scope_assumptions']),
            evidence=refs(v['source'],v['meaning'])))
    if len(variables)>9:raise ValueError('Small experiment allows at most nine variables')
    nodes={v['id']:v for v in variables};typed={}
    for m in draft['mechanisms']:
        child=m['child'];parents=m['parents']
        if len(parents)>3:raise ValueError('At most three declared local parents')
        for e in m['edges']:
            edges.append(dict(id=e['parent']+'__'+child,parent=e['parent'],child=child,label=e['label'],
                process=e['process'],participants=[nodes[e['parent']]['actor'],nodes[child]['actor']],
                conditions=e['conditions'],qualifications=m['unknowns'],gaps=e['gaps'],alternatives=[],
                structural_implications=[m['description']],evidence=refs(e['source'],e['process']),contradictions=[],
                status=e['status'],endpoint_support={'parent':nodes[e['parent']]['event_status'],'child':nodes[child]['event_status']},
                temporal_status='consistent',information_status='consistent'))
        mechanisms.append(dict(id='M_'+child,child=child,parents=parents,description=m['description'],
            joint_description=m['description'] if len(parents)>1 else '',assumptions=m['assumptions'],
            gaps=m['unknowns'],evidence=refs(m['source'],m['description'])))
        constraints=[]
        # Empirical configuration only; unknown input configurations survive.
        if nodes[child]['factual'] is not None and all(nodes[p]['factual'] is not None for p in parents):
            ev=nodes[child]['evidence']+sum([nodes[p]['evidence'] for p in parents],[])
            constraints.append(dict(id='observed_'+child,kind='row',when={p:nodes[p]['factual'] for p in parents},
                allowed=[nodes[child]['factual']],basis='evidence',rationale='Observed local configuration only.',evidence=ev))
        for i,c in enumerate(m['rows']):
            constraints.append(dict(id='row_'+child+'_'+str(i),kind='row',when=c['when'],allowed=c['allowed'],
                basis=c['basis'],rationale=c['reason'],evidence=refs(c['source'],c['reason'])))
        if m['expression'] is not None:
            expr=expression(m['expression'],parents);typed[child]=expr
            if not m['source']:raise ValueError('Complete equation requires explicit source attribution')
            added=any(ps[x]['origin']=='added_rule' for x in m['source'])
            for i,row in enumerate(it.product([0,1],repeat=len(parents))):
                state=dict(zip(parents,row))
                constraints.append(dict(id='equation_'+child+'_'+str(i),kind='row',when=state,
                    allowed=[value(expr,state)],basis='assumption' if added else 'evidence',
                    rationale=('Controlled adaptation rule: ' if added else 'Generated exact-rule interpretation: ')+m['description'],
                    evidence=refs(m['source'],m['description'])))
        functions.append(dict(child=child,background=[],scope_status='declared_family',
            scope_assumptions=draft['scope_assumptions'],constraints=constraints))
    rep=validate_representation({'variables':variables,'edges':edges,'mechanisms':mechanisms,
        'outcome':draft['outcome'],'gaps':sum([m['unknowns'] for m in draft['mechanisms']],[])},pack)
    family=build_family(rep,{'functions':functions},pack,max_models=max_models)
    if not family['models']:raise ValueError('Empty compatible family: '+family['coverage'])
    claims=check_propositions(draft,family)
    return {'representation':rep,'family':family,'typed':typed,'claims':claims,
            'formal_consistent':not any(c['status']=='contradicted' for c in claims)}


def schema_diagnostics(draft):
    """Aggregate actionable errors. Do not guess the targets of flat edges."""
    errors=[];nodes={v['id']:v for v in draft.get('variables',[])}
    if draft.get('outcome') not in nodes:errors.append('outcome must name an existing variable')
    for m in draft.get('mechanisms',[]):
        child=m.get('child')
        if child not in nodes:errors.append('Unknown mechanism child '+str(child));continue
        if nodes[child].get('boundary')=='fixed_context':errors.append(child+': child has a mechanism but is labelled fixed_context; explicitly resolve this contradiction')
        for field in ['edges','claims']:
            if field not in m:errors.append(child+': missing nested '+field+'; flat edges without child IDs cannot be assigned safely')
        for claim in m.get('claims',[]):
            if claim.get('type')=='exact' and 'rule' not in claim:errors.append(child+': exact claim needs a separately stated rule implementing the quoted prose, not one when-row')
    endogenous={v['id'] for v in nodes.values() if v.get('boundary')!='fixed_context'}
    declared={m.get('child') for m in draft.get('mechanisms',[])}
    for ident in sorted(endogenous-declared):errors.append(ident+': endogenous variable missing mechanism')
    for v in nodes.values():
        if v.get('boundary')=='fixed_context' and v.get('factual') is None:errors.append(v['id']+': fixed context cannot have an unknown factual value')
    return errors


def proposition(claim,names,rows,values):
    """Check the named logical proposition, never an arbitrarily convenient row."""
    rows=[tuple(row) for row in rows]
    typ=claim['type'];when=claim.get('when',{});output=claim.get('output',1)
    maps=[dict(zip(names,row)) for row in rows]
    if set(when)-set(names) or any(v not in (0,1) for v in when.values()):raise ValueError('Unknown claim input/value')
    if typ in ('necessary','sufficient','conjunction'):
        if not when or output not in (0,1):raise ValueError('Claim needs an antecedent and Boolean output')
        tests=[]
        if typ in ('necessary','conjunction'):
            # Crucially: one full quantified test PER claimed required input.
            tests += [{'kind':'necessary','when':{p:v},'output':output} for p,v in when.items()]
        if typ in ('sufficient','conjunction'):
            tests.append({'kind':'row','when':when,'allowed':[output]})
        for c in tests:
            ok,witness=predicate(c,names,rows,values)
            if not ok:return False,dict(proposition=c,counterexample=witness)
        vacuous= output not in values if typ=='necessary' else not any(all(x[k]==v for k,v in when.items()) for x in maps)
        return True,{'vacuous':vacuous}
    if typ in ('inhibits','enables'):
        p=claim['parent']
        if p not in names:raise ValueError('Unknown directional claim input')
        c={'parent':p,'low':0,'high':1,'when':when,'sign':'negative' if typ=='inhibits' else 'positive'}
        if claim.get('global',False):
            ok,w=predicate(dict(c,kind='monotone'),names,rows,values)
            if not ok:return False,w
        return predicate(dict(c,kind='changes'),names,rows,values)
    if typ=='exact':
        expr=expression(claim['rule'],names)
        for x,y in zip(maps,values):
            expected=value(expr,x)
            if y!=expected:return False,{'inputs':x,'output':y,'prose_requires':expected}
        return True,None
    raise ValueError('Unknown semantic proposition '+str(typ))


def check_propositions(draft,family):
    checks=[]
    for m in draft['mechanisms']:
        local=family['local'][m['child']]
        for c in m['claims']:
            if not c.get('text') or c['text'] not in m['description']:
                raise ValueError('Claim must quote the actual mechanism description')
            violations=[];pass_count=0;vacuous=0
            for table in local['tables']:
                passed,w=proposition(c,local['inputs'],local['rows'],table)
                if passed:
                    pass_count+=1;vacuous+=int(bool(w and w.get('vacuous')))
                elif len(violations)<2:violations.append(w)
            checks.append({'child':m['child'],'claim':c,'status':'contradicted' if violations else
                'entailed' if local['coverage']=='exhaustive' else 'unresolved',
                'counterexamples':violations,'passing_tables':pass_count,'tables_checked':len(local['tables']),
                'rows_per_table':len(local['rows']),'vacuous_tables':vacuous,'coverage':local['coverage']})
    return checks


def construction_request(story,version,index):
    text='\n'.join('['+s['id']+'] ['+s['origin']+'] '+s['text'] for s in story[version])
    return {'model':MODEL,'messages':[{'role':'system','content':'Use supplied evidence only. Return valid JSON.'},
        {'role':'user','content':INSTRUCTIONS+'\nOUTCOME SCOPE: '+story['outcome']+'\nSTORY:\n'+text}],
        'max_tokens':4000,'temperature':.2,'seed':7710+index,
        'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}}


def direct_request(story,index):
    # Intentionally whitelist wording; no reference variable or gold answer enters.
    text='\n'.join('['+s['id']+'] ['+s['origin']+'] '+s['text'] for s in story['controlled'])
    questions=[{'id':q['id'],'question':q['text']} for q in story['reference']['questions']]
    prompt='Answer the intervention questions directly from ONLY the supplied story, without constructing a graph or executable model. Apply the explicitly added rules. Keep all nontargeted mechanisms/background fixed. Return JSON {"answers":[{"id":"question ID","value":0,"explanation":"brief reasoning","sentences":["S1"]}]}. value is 1 for yes, 0 for no, null if not determined.\nSTORY:\n'+text+'\nQUESTIONS:\n'+json.dumps(questions)
    return {'model':MODEL,'messages':[{'role':'system','content':'Use supplied evidence only. Return valid JSON.'},
        {'role':'user','content':prompt}], 'max_tokens':900,'temperature':.2,'seed':7810+index,
        'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}}


def request_once(root,ident,body):
    import requests
    folder=Path(root)/RUN;path=folder/(ident+'.json')
    if path.exists():return json.loads(path.read_text())
    window=json.loads((folder/'service_window.json').read_text())
    if (folder/'COMPLETE').exists() or datetime.now(timezone.utc)>=datetime.fromisoformat(window['deadline']):
        raise RuntimeError('Small experiment service window closed')
    previous=[json.loads(p.read_text()) for p in folder.glob('*_attempt[01].json')]
    # On a transport failure, conservatively charge the whole reserved output.
    used=sum(r.get('raw',{}).get('usage',{}).get('completion_tokens',r['request']['max_tokens']) for r in previous)
    if used+body['max_tokens']>40000:raise RuntimeError('Generated token reserve would exceed 40,000')
    atomic_json(folder/(ident+'_request.json'),body)
    started=time.monotonic();record={'id':ident,'request':body,'request_sha256':fingerprint(body),
        'started_at':datetime.now(timezone.utc).isoformat(),'route':'Qwen3-14B-AWQ, authorized RunPod RTX 4090',
        'reference_supplied':False,'frozen_sha256':FROZEN_SHA}
    try:
        r=requests.post('http://127.0.0.1:8765/v1/chat/completions',json=body,timeout=210);r.raise_for_status()
        record['raw']=r.json()
        content=record['raw']['choices'][0]['message']['content']
        try:record['parsed']=json.loads(content)
        except (TypeError,ValueError) as e:record['parse_error']=str(e)
    except Exception as e:record['error']=type(e).__name__+': '+str(e)
    record['elapsed_seconds']=time.monotonic()-started
    atomic_json(path,record)
    print(ident,record.get('raw',{}).get('usage'),record.get('error','saved'),flush=True)
    return record


def generate(root):
    data=frozen(root);folder=Path(root)/RUN
    if (folder/'INFERENCE_DONE').exists() or (folder/'COMPLETE').exists():
        raise RuntimeError('Closed experiment; a new attempt series requires a new explicitly recorded budget')
    for i,s in enumerate(data['stories']):
        for j,version in enumerate(['natural','controlled']):
            ident=s['id']+'_'+version+'_attempt0'
            first=request_once(root,ident,construction_request(s,version,2*i+j))
            # Primary output is immutable before even invoking validation.
            try:
                if 'parsed' not in first:raise ValueError(first.get('parse_error',first.get('error','No parsed object')))
                compiled=compile_model(first['parsed'],s,version)
                bad=[c for c in compiled['claims'] if c['status']=='contradicted']
                if bad:raise ValueError('Description/function counterexamples: '+json.dumps(bad))
                status={'compiled':True,'formal_consistent':compiled['formal_consistent']}
            except Exception as e:
                status={'compiled':False,'error':type(e).__name__+': '+str(e)}
                if version=='controlled':
                    body=copy.deepcopy(first['request'])
                    body['messages'] += [{'role':'assistant','content':first.get('raw',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content']},
                        {'role':'user','content':'One bounded repair: '+status['error']+'\nReturn the complete corrected JSON. Repair only diagnosed issues, preserve established observations, and do not add outside facts.'}]
                    request_once(root,s['id']+'_'+version+'_attempt1',body)
            atomic_json(folder/(ident+'_validation.json'),status)
        request_once(root,s['id']+'_direct_attempt0',direct_request(s,i))
    (folder/'INFERENCE_DONE').write_text(datetime.now(timezone.utc).isoformat()+'\n')


def reference_world(ref,do=None):
    do=do or {};state={}
    # References are authored in topological order, verified here explicitly.
    for v in ref['variables']:
        if v['id'] in do:state[v['id']]=do[v['id']]
        elif v['equation'] is None:state[v['id']]=v['factual']
        else:state[v['id']]=value(expression(v['equation'],v['parents']),state)
    return state


def verify_references(data):
    rows=[]
    for s in data['stories']:
        ref=s['reference'];factual=reference_world(ref)
        assert factual=={v['id']:v['factual'] for v in ref['variables']}
        for q in ref['questions']:
            got=reference_world(ref,q['do'])[ref['outcome']]
            if got!=q['expected']:raise ValueError('Frozen reference answer conflict '+q['id'])
            rows.append({'story':s['id'],'question':q['id'],'expected':q['expected'],'computed':got})
    return rows


def mutation_checks():
    rows=list(it.product([0,1],repeat=2));names=['A','B']
    cases=[('AND replaced by OR','A or B',{'text':'A is necessary for the outcome.','type':'necessary','when':{'A':1},'output':1}),
        ('Claimed necessary input removed','B',{'text':'A and B are jointly required and together sufficient.','type':'conjunction','when':{'A':1,'B':1},'output':1}),
        ('Inhibitory relationship reversed','A and B',{'text':'B can inhibit the outcome and never increases it.','type':'inhibits','parent':'B','global':True}),
        ('One conjunct is insufficient alone','A and B',{'text':'A alone is sufficient.','type':'sufficient','when':{'A':1},'output':1})]
    results=[]
    for label,eq,c in cases:
        vals=[value(expression(eq,names),dict(zip(names,row))) for row in rows]
        ok,w=proposition(c,names,rows,vals)
        results.append({'mutation':label,'equation':eq,'claim':c,'detected':not ok,'counterexample':w,
            'obsolete_all_zero_failure_check_passes':vals[0]==0})
    assert all(r['detected'] for r in results)
    return results


def load_records(root):
    path=Path(root)/FOLDER/'records.json.xz'
    return json.loads(lzma.decompress(path.read_bytes()))


def reference_draft(story):
    """Author reference adapter, solely for solver cross-checks; never inference."""
    ref=story['reference'];nodes={v['id']:v for v in ref['variables']};sent={s['id']:s for s in story['controlled']}
    d={'outcome':ref['outcome'],'scope_assumptions':ref['background'],'variables':[],'mechanisms':[]}
    for v in ref['variables']:
        d['variables'].append(dict(id=v['id'],label=v['label'],meaning=v['definition'],actor='Story participant or object',
            time=v['time'],factual=v['factual'],kind='narrative_fact',boundary='endogenous' if v['equation'] else 'fixed_context',
            source=v['sentences'],basis='explicit'))
        if v['equation']:
            desc=' '.join(sent[x]['text'] for x in v['sentences'] if sent[x]['origin']=='added_rule')
            d['mechanisms'].append(dict(child=v['id'],parents=v['parents'],description=desc,source=v['sentences'],
                assumptions=['Experiment-author controlled rule, not a traditional-story identification.'],unknowns=[],
                expression=v['equation'],rows=[],claims=[],edges=[dict(parent=p,label='Enters specified rule',
                    process='The controlled rule explicitly includes this factor in the child mechanism.',source=v['sentences'],
                    status='explicit',conditions=[],gaps=[]) for p in v['parents']]))
    return d


def semantic_checks(draft,compiled,audit):
    """Audit translations supplement, never rewrite, the first generated prose."""
    checks=[]
    for c in audit.get('additional_claims',[]):
        child=c['child'];m=next(m for m in draft['mechanisms'] if m['child']==child)
        prose=m['description']+' '+' '.join(e['process'] for e in m['edges'])
        if c['text'] not in prose:raise ValueError('Audit claim must quote existing prose')
        tmp=copy.deepcopy(draft)
        for mm in tmp['mechanisms']:
            mm['claims']=[]
            if mm['child']==child:mm['description']=prose;mm['claims']=[c]
        checks+=check_propositions(tmp,compiled['family'])
    return checks


def compare_all_interventions(story,compiled,alignment):
    ref=story['reference'];rids={v['id'] for v in ref['variables']};gids={v['id'] for v in compiled['representation']['variables']}
    if set(alignment)!=rids or any(x not in gids for x in alignment.values()) or len(set(alignment.values()))!=len(alignment):
        return {'status':'unavailable','reason':'Incomplete, non-injective or missing semantic alignment'}
    # Do not get credit for trivially replacing the outcome itself.
    targets=[v['id'] for v in ref['variables'] if v['id']!=ref['outcome']]
    n=0;outcome_correct=0;all_states_correct=0;counterexamples=[]
    for choices in it.product([None,0,1],repeat=len(targets)):
        do={p:x for p,x in zip(targets,choices) if x is not None};expect=reference_world(ref,do)
        answer=query(compiled['representation'],compiled['family'],{alignment[p]:x for p,x in do.items()})
        n+=1
        out_ok=answer['identified'] and answer['values']==[expect[ref['outcome']]]
        world_ok=bool(answer['worlds']) and all(all(w['counterfactual'][alignment[p]]==val for p,val in expect.items()) for w in answer['worlds'])
        outcome_correct+=int(out_ok);all_states_correct+=int(world_ok)
        if (not out_ok or not world_ok) and len(counterexamples)<3:
            counterexamples.append({'do':do,'expected':expect,'outcome_values':answer['values'],
                                   'example_world':answer['worlds'][0]['counterfactual'] if answer['worlds'] else None})
    return {'status':'evaluated','interventions':n,'outcome_agreement':outcome_correct,'all_mapped_states_agreement':all_states_correct,
        'all_equivalent':n==outcome_correct==all_states_correct,'counterexamples':counterexamples,
        'interpretation':'Exhaustive mapped intervention settings within these small fixed representations; not general story validity.'}


def small_answer(answer):
    return {k:v for k,v in answer.items() if k!='worlds'}


def analyze(root,records):
    data=frozen(root);verify_references(data);byid={r['id']:r for r in records['requests']}
    results={'frozen_sha256':FROZEN_SHA,'model':MODEL,'independent_researcher_review':'pending',
             'reference_checks':verify_references(data),'mutations':mutation_checks(),'constructions':[],'comparisons':[]}
    compiled_by={}
    for s in data['stories']:
        # The author references also execute through the same existing SCM engine.
        rc=compile_model(reference_draft(s),s,'controlled')
        for q in s['reference']['questions']:
            assert query(rc['representation'],rc['family'],q['do'])['values']==[q['expected']]
        for version in ['natural','controlled']:
            attempts=[0,1] if s['id']+'_'+version+'_attempt1' in byid else [0]
            for attempt in attempts:
                ident=s['id']+'_'+version+'_attempt'+str(attempt);r=byid.get(ident);audit=records['audits'].get(ident,{})
                row={'id':ident,'story':s['id'],'version':version,'attempt':attempt,'status':'unrun','audit':audit}
                if r is not None:
                    if 'parsed' in r:
                        row['local_diagnostics']=local_diagnostics(r['parsed'],audit)
                    try:
                        if 'parsed' not in r:raise ValueError(r.get('parse_error',r.get('error','No parsed output')))
                        c=compile_model(r['parsed'],s,version);compiled_by[ident]=c
                        checks=c['claims']+semantic_checks(r['parsed'],c,audit)
                        bad=[x for x in checks if x['status']=='contradicted']
                        status='contradiction' if bad else 'compiled'
                        row.update(status=status,claim_checks=checks,nodes=len(c['representation']['variables']),edges=len(c['representation']['edges']),
                            family_coverage=c['family']['coverage'],compatible_models=len(c['family']['models']),
                            unknown_local_rows=sum(len(x['unknown_rows']) for x in c['family']['local'].values()),
                            factual=small_answer(query(c['representation'],c['family'],{})),
                            mechanism_tables={k:{'inputs':v['inputs'],'rows':v['rows'],'tables':v['tables'],'coverage':v['coverage']}
                                for k,v in c['family']['local'].items()},
                            accepted_for_display=(not bad and audit.get('description_function_review')=='consistent'))
                        if version=='controlled':
                            row['functional_comparison']=compare_all_interventions(s,c,audit.get('alignment',{}))
                        elif audit.get('natural_query_do') is not None:
                            row['natural_query']=dict(s['natural_checks'][0],result=small_answer(query(c['representation'],c['family'],audit['natural_query_do'])))
                        else:
                            row['natural_query']=dict(s['natural_checks'][0],result={'status':'unavailable','values':[],
                                'reason':audit.get('natural_query_reason','Semantic target not represented or not audited')})
                    except Exception as e:row.update(status='failed',error=type(e).__name__+': '+str(e))
                results['constructions'].append(row)
        direct=byid.get(s['id']+'_direct_attempt0',{}).get('parsed',{}).get('answers',[])
        for q in s['reference']['questions']:
            row={'story':s['id'],'id':q['id'],'question':q['text'],'kind':q['kind'],'expected':q['expected']}
            ds=[x for x in direct if x.get('id')==q['id']]
            d=ds[0] if len(ds)==1 else {};dv=d.get('value')
            row.update(direct=dv,direct_correct=(type(dv) is int and dv==q['expected']),direct_explanation=d.get('explanation'),
                       direct_status='answered' if type(dv) is int and dv in [0,1] else 'abstained_or_failed')
            for attempt in [0,1]:
                ident=s['id']+'_controlled_attempt'+str(attempt);tag='executed' if attempt==0 else 'repair_executed'
                cr=next((x for x in results['constructions'] if x['id']==ident),None)
                if cr is None:continue
                row[tag]=None;row[tag+'_correct']=False
                audit=records['audits'].get(ident,{});align=audit.get('alignment',{})
                if cr['status']=='compiled' and all(align.get(k) for k in q['do']) and ident in compiled_by:
                    c=compiled_by[ident]
                    try:
                        ans=query(c['representation'],c['family'],{align[k]:v for k,v in q['do'].items()})
                        assert verify_reported_result(c['representation'],c['family'],{align[k]:v for k,v in q['do'].items()},ans)['passed']
                        row[tag]=ans['values'][0] if ans['identified'] else None
                        row[tag+'_correct']=ans['identified'] and ans['values']==[q['expected']]
                        row[tag+'_status']=ans['status'];row[tag+'_values']=ans['values']
                    except (KeyError,ValueError) as e:row[tag+'_status']=str(e)
                else:row[tag+'_status']='failed, contradicted or unaligned model'
            results['comparisons'].append(row)
    results['resource_usage']=records['resource_usage']
    results['primary']={'controlled_models_attempted':3,'natural_models_attempted':3,
        'controlled_compiled':sum(r['version']=='controlled' and r['attempt']==0 and r['status']=='compiled' for r in results['constructions']),
        'natural_compiled':sum(r['version']=='natural' and r['attempt']==0 and r['status']=='compiled' for r in results['constructions']),
        'executed_correct':sum(r.get('executed_correct',False) for r in results['comparisons']),
        'direct_correct':sum(r['direct_correct'] for r in results['comparisons']), 'questions':12}
    return results,compiled_by


def local_diagnostics(draft,audit):
    """Inspect partial local functions without claiming the invalid DAG executes.

The diagnostic does NOT move edges, change boundaries, add equations or revise
facts. It reports whether declared rows determine the generated prose's behavior.
"""
    nodes={v['id']:dict(v,domain=[0,1]) for v in draft.get('variables',[])}
    reports=[]
    for m in draft.get('mechanisms',[]):
        try:
            cs=[dict(c,id='row'+str(i),kind='row',rationale=c['reason'],evidence=[{'passage_id':x} for x in c['source']])
                for i,c in enumerate(m['rows'])]
            child=m['child'];parents=m['parents']
            if nodes[child]['factual'] is not None and all(nodes[p]['factual'] is not None for p in parents):
                cs.append(dict(id='observation',kind='row',when={p:nodes[p]['factual'] for p in parents},allowed=[nodes[child]['factual']],
                    basis='assumption',rationale='Diagnostic only: preserve the generator\'s declared factual row, including source errors.',evidence=[]))
            local=local_family(dict(child=child,parents=parents,background=[],constraints=cs),nodes)
            checks=[]
            generated_checks=[]
            generated=m.get('claims',[])+[c for c in draft.get('claims',[]) if c.get('text')==m['description']]
            for c in generated:
                try:
                    bad=[]
                    for table in local['tables']:
                        ok,w=proposition(c,local['inputs'],local['rows'],table)
                        if not ok and len(bad)<2:bad.append({'table':table,'witness':w})
                    generated_checks.append({'claim':c,'status':'not_entailed' if bad else 'entailed',
                        'counterexamples':bad,'tables_checked':len(local['tables']),
                        'warning':'Generated formal type may misstate the prose; inspect the separate reviewer translation.'})
                except (KeyError,ValueError) as e:
                    generated_checks.append({'claim':c,'status':'invalid_formal_claim','error':str(e)})
            # Audit translations implement ACTUAL prose, separate from malformed
            # generated claim records. They never constrain the candidate family.
            for c in audit.get('local_claims',[]):
                if c['child']!=child:continue
                prose=m['description']+' '+' '.join(e.get('process','') for e in draft.get('edges',m.get('edges',[])))
                if c['text'] not in prose:raise ValueError('Audit must quote actual original prose')
                bad=[];passing=0
                for table in local['tables']:
                    ok,w=proposition(c,local['inputs'],local['rows'],table)
                    if ok:passing+=1
                    elif len(bad)<2:bad.append({'table':table,'witness':w})
                checks.append({'claim':c,'status':'not_entailed_by_partial_function' if bad else 'entailed_by_partial_function',
                    'counterexamples':bad,'passing_tables':passing,'tables_checked':len(local['tables'])})
            reports.append({'child':child,'rows':local['rows'],'inputs':local['inputs'],'tables':local['tables'],
                'unknown_rows':local['unknown_rows'],'coverage':local['coverage'],'prose_checks':checks,
                'generated_claim_checks':generated_checks})
        except Exception as e:reports.append({'child':m.get('child'),'error':str(e)})
    return reports


def render_figures(root,records,results):
    """Three reference diagrams: invalid generator records are never redrawn as valid."""
    import shlex,subprocess,textwrap,shutil
    from reportlab.pdfgen.canvas import Canvas
    from .v4.figures import Drawing,lines
    root=Path(root);out=root/FOLDER;work=root/'.private/simple_stories/rendered';work.mkdir(parents=True,exist_ok=True)
    data=frozen(root);portfolio=Canvas(str(out/'FIGURES.pdf'),pageCompression=1,invariant=1);Drawing.portfolio=portfolio
    inventory=[]
    for s in data['stories']:
        ref=s['reference'];ann=records['figure_annotations'][s['id']]
        dref=reference_draft(s);compiled=compile_model(dref,s,'controlled');rep=compiled['representation']
        edgeids={e['id'] for e in rep['edges']}
        if edgeids!=set(ann['edges']):raise ValueError('Figure edge annotations must exactly cover operative model')
        q=lambda x:json.dumps(str(x));layouts=[]
        for nw,ew in [(16,17),(19,20),(14,15)]:
            dot=['digraph G { graph [rankdir=TB, nodesep=.13, ranksep=.24, splines=polyline, margin=0]; node [shape=box,fontname=Helvetica,fontsize=13,margin=".07,.06"]; edge [fontname=Helvetica,fontsize=11.5];']
            for v in ref['variables']:
                dot.append(q(v['id'])+' [label='+q(lines(v['label'],nw)+'\n'+v['id']+' = '+str(v['factual']))+'];')
            for e in rep['edges']:
                child=next(v for v in ref['variables'] if v['id']==e['child'])
                sources=[x for x in child['sentences'] if next(z['origin'] for z in s['controlled'] if z['id']==x)=='added_rule']
                dot.append(q(e['parent'])+' -> '+q(e['child'])+' [label='+q(lines(ann['edges'][e['id']],ew)+'\n'+','.join(sources))+'];')
            dot.append('}')
            parsed=[shlex.split(x) for x in subprocess.check_output(['dot','-Tplain'],input='\n'.join(dot).encode()).decode().splitlines()]
            gw,gh=float(parsed[0][2])*72,float(parsed[0][3])*72
            scale=min(1,409/gw,445/gh);layouts.append((scale,parsed,gw,gh))
        scale,parsed,gw,gh=max(layouts,key=lambda x:x[0]);w,h=612,768;d=Drawing(work/s['id'],w,h)
        d.text(w/2,h-25,s['title'],18,bold=True)
        d.text(w/2,h-45,'Controlled adaptation | Author reference model',12,color='#9a652b',bold=True)
        d.text(w/2,h-62,'Generated first attempt and repair failed validation; this is not a generated SCM.',10.5)
        ox=12+(409-gw*scale)/2;oy=239+(445-gh*scale)/2
        for row in parsed:
            if row[0]=='edge':
                n=int(row[3]);coords=list(map(float,row[4:4+2*n]));pts=[(ox+coords[i]*72*scale,oy+coords[i+1]*72*scale) for i in range(0,len(coords),2)]
                d.path(pts,'#377b7b')
                tail=row[4+2*n:]
                if len(tail)>=5:
                    label,x,y=tail[:3];txt=label.replace('\\n','\n');ls=txt.split('\n');size=11.5*scale
                    d.block(ox+float(x)*72*scale,oy+float(y)*72*scale+(len(ls)-1)*(size+3)/2-3,txt,size,color='#286967')
        for row in parsed:
            if row[0]=='node':
                ident=row[1];x,y,ww,hh=map(float,row[2:6]);v=next(v for v in ref['variables'] if v['id']==ident)
                cx,cy=ox+x*72*scale,oy+y*72*scale
                fill='#e0eeec' if ident==ref['outcome'] else '#fff2d9' if v['equation'] is None else '#f0f5f7'
                if v['factual']==0:fill='#f8e8e6'
                d.box(cx-ww*36*scale,cy-hh*36*scale,ww*72*scale,hh*72*scale,fill)
                txt=row[6].replace('\\n','\n');ls=txt.split('\n');size=13*scale
                d.block(cx,cy+(len(ls)-1)*(size+3)/2-4,txt,size)
        d.box(432,239,168,445,'#f6f8fa','#d9e1e6')
        d.text(444,662,'Assumed rules',13,anchor='start',bold=True)
        d.block(444,642,'Added sentences define\nthese exact functions.',10.5,anchor='start')
        y=603
        for v in ref['variables']:
            if not v['equation']:continue
            eq=v['id']+' = '+v['equation'].replace(' and ',' & ').replace(' or ',' | ').replace('not ','!')
            rule_refs=[x for x in v['sentences'] if next(z['origin'] for z in s['controlled'] if z['id']==x)=='added_rule']
            d.text(444,y,eq,12,anchor='start',bold=True);d.text(444,y-16,', '.join(rule_refs),10,anchor='start',color='#9a652b');y-=48
        d.block(444,y-3,'& together   | either\n! absence / negation\n0 absent   1 present',10.5,anchor='start')
        d.block(444,y-57,'Amber: boundary input\nPink: factual value 0\nTeal: endpoint outcome',9.5,anchor='start')
        d.box(12,107,588,119,'#edf4f5','#bad1d3')
        d.text(25,207,'How the factors work together',13,anchor='start',bold=True)
        d.block(25,188,lines(ann['joint'],91),11.5,anchor='start')
        d.block(25,143,lines(ann['lesson'],99),10.5,anchor='start')
        d.block(16,83,lines(ann['natural_limit'],100),10.5,anchor='start',color='#805239')
        d.text(16,39,'Sentence references point to frozen.json. Rules are author assumptions, not claims about every telling.',9.5,anchor='start')
        d.text(16,24,'Exact reference execution: four frozen questions checked. Generator failures remain in the comparison table.',9.5,anchor='start')
        d.save();shutil.copyfile(work/(s['id']+'.svg'),out/(s['id']+'.svg'))
        inventory.append({'story':s['id'],'svg':s['id']+'.svg','pdf_page':len(inventory)+1,
            'model_origin':'Codex-authored frozen controlled reference, not Qwen output',
            'reference_sha256':fingerprint(ref),'operative_edge_ids':sorted(edgeids),
            'minimum_graph_font_at_7inch':11.5*scale*504/w,
            'caption':ann['lesson'],'joint_description':ann['joint']})
    portfolio.save();Drawing.portfolio=None
    return inventory


def write_report(root,records,results,inventory):
    import csv,io
    root=Path(root);data=frozen(root);out=root/FOLDER
    comparison=io.StringIO();writer=csv.writer(comparison,delimiter='\t',lineterminator='\n')
    writer.writerow(['story','id','question','kind','expected','direct','direct_correct','executed','executed_correct','repair_executed','reference_executed'])
    for row in results['comparisons']:
        writer.writerow([row['story'],row['id'],row['question'],row['kind'],row['expected'],row['direct'],row['direct_correct'],
            row.get('executed') if row.get('executed') is not None else 'FAILED_MODEL',row['executed_correct'],
            row.get('repair_executed') if row.get('repair_executed') is not None else 'FAILED_MODEL',row['expected']])
    (out/'COMPARISON.tsv').write_text(comparison.getvalue())
    first=[r for r in results['constructions'] if r['attempt']==0]
    primary=results['primary'];usage=records['resource_usage']
    parts=['# Three simple stories: results',
        '**The reference solver checks succeed; the autonomous model-construction check fails in this run.** These are three introductory development cases, not evidence of general narrative understanding. All previous Game of Thrones results remain unchanged.',
        '## Outputs and reproduction',
        '[Three-page vector PDF](FIGURES.pdf); individual SVGs: [Humpty Dumpty](humpty.svg), [The Boy Who Cried Wolf](wolf.svg), [The Crow and the Pitcher](crow.svg). These figures show **Codex-authored frozen reference SCMs**, not successful Qwen models. Independent researcher review remains pending.',
        'Run from `GoT-war/`: `python3 scripts/simple_stories.py`. No GPU or network is required. The command verifies hashes, rebuilds reference and available generated families, checks claims/mutations, writes [COMPARISON.tsv](COMPARISON.tsv), and renders the figures. Local individual PDFs, PNG previews, expanded machine-readable results and the source/claim review packet go under `.private/simple_stories/` and are regenerated. `records.json.xz` publishes exact requests, first outputs, repairs, audits, usage and a result snapshot; `frozen.json` contains all six numbered texts and reference specifications.',
        '## Separate measurements',
        '| Check | Result | Interpretation |','|---|---|---|',
        '| Author reference factual reconstruction | 3/3 models | Existing SCM engine agrees with all 19 reference variable values. |',
        '| Author reference interventions | 12/12 | Four frozen questions per story; rules are controlled author specifications. |',
        '| Qwen first constructions | %d/3 natural; %d/3 controlled valid | Failures remain in the primary denominator. |'%(primary['natural_compiled'],primary['controlled_compiled']),
        '| Qwen direct answers | %d/12 correct | 4/4 in each story, including joint and unchanged outcomes. |'%primary['direct_correct'],
        '| Qwen executed answers | %d/12 obtained correctly | All 12 unavailable because construction failed; no wrong computed answers are fabricated. |'%primary['executed_correct'],
        '| Bounded repairs | 0/3 valid | Every repaired parsed object exactly repeats its first attempt. |',
        '| Qwen executable factual reconstruction | 0/3 controlled, 0/3 natural | No accepted full generated model exists. |',
        '| Natural-story uncertainty answers | 0/3 valid answers; 3 unavailable | Compiler failure is not credited as appropriate epistemic abstention. |',
        '| Targeted mutation checks | 4/4 detected | AND→OR, dropped necessary input, reversed inhibition, false sufficiency. |',
        '\nQuestions are clustered within three stories. No hypothesis test, question-level confidence interval or composite score is appropriate. Successful-synthesis-only accuracy and full generated behavioral equivalence are undefined because there are no successful syntheses.',
        '## Source and factual audit',
        'Codex reviewed the complete short passages and each output, without correcting the generator. The counts below concern **asserted event/state values**, not executable reconstruction. Null states and statements about what the narrator omits are excluded. Detailed item IDs, exclusions, citations and prose translations are in the archived audit and the reproducible local review packet. Literal citation existence alone is not source entailment.',
        '| Story/version | Supported factual assertions | Confirmed source-support issues | Important finding |','|---|---|---|---|']
    findings={
        'humpty_natural_attempt0':'Invents permanent irreparability and makes missing information its cause; reverses two temporal edges.',
        'humpty_controlled_attempt0':'Correct facts, but an edge confuses damage needed for repair success with damage needed to attempt repair.',
        'wolf_natural_attempt0':'Preserves a null prevention possibility but overstates three factual descriptions as necessity claims.',
        'wolf_controlled_attempt0':'Incorrectly says villagers responded in time; exact prose is represented only by partial positive rows.',
        'crow_natural_attempt0':'Useful event sequence, but undefined outcome ID, missing mechanisms and unjustified necessity claims.',
        'crow_controlled_attempt0':'Adds an unsupported intact-pitcher prerequisite for adding stones; some edges omit required qualifiers.'}
    for r in first:
        f=r['audit']['factual_assertions'];good=len(f['supported']);bad=len(f['unsupported'])
        parts.append('| %s / %s | %d/%d | %d | %s |'%(r['story'],r['version'],good,good+bad,len(r['audit']['source_errors']),findings[r['id']]))
    parts+=['\nThese are fallible assistant judgments, not human adjudication. Source issues count explicitly listed claim/variable/mechanism records, sometimes sharing one underlying mistake; they are not independent observations. The generator did not invent an egg or the boy\'s death. Natural Humpty nevertheless asserts irreparability twice. Added-rule origins are visible in our frozen packet and figures, while the generated models leave their assumption arrays empty.',
        '## Why construction failed',
        'All six first outputs parse as JSON, but put edge and claim arrays at the top level instead of inside mechanisms. The flat edges lack child IDs, so assignment cannot safely be guessed. Humpty and Wolf also label mechanism-dependent variables as fixed context. Natural Crow names a nonexistent outcome (`drank`) and omits mechanisms for several endogenous variables. An automatic schema repair would require substantive choices; none were silently made.',
        'The original repair feedback was only `KeyError: edges`, an insufficiently actionable diagnostic. Three bounded repair responses repeated their originals. The implementation now collects missing nesting, contradictory boundary declarations, unknown outcome IDs and absent mechanisms into one diagnostic, but this improvement has **not** been evaluated in a fresh generation run. No prompts or reference answers were changed to obtain a better score.',
        '## Description/function agreement and uncertainty',
        'Local diagnostics inspect the generated row constraints even when the full record is invalid; they do not silently repair or execute the graph. All 11 controlled mechanism descriptions state exact rules, yet all 11 leave incompatible behavior in their partial families. Every complete expression is null. This is not responsible uncertainty about these explicitly stated rules: it is incomplete encoding. The Wolf response and harm descriptions additionally conflict with its wrong factual response value.',
        'Conversely, natural rows leave 13, 7 and 13 local input rows variable for Humpty, Wolf and Crow respectively. The software preserves them. This is useful partial data, but invalid representations and unsupported prose prevent credit for an end-to-end uncertainty answer. Humpty loses uncertainty through irreparability claims; Wolf and Crow mention missing information but do not produce valid models.',
        'All nine generated natural-story necessity predicates admit counterexamples in the local families; the prose usually describes a factual sequence or a sufficient condition instead of necessity. All eleven controlled exact-claim records omit the required rule field. The audit therefore distinguishes a malformed formal record from the actual proposition expressed by the prose. These checks update the simple-stories validation without silently rescoring archived v4 results.',
        'The new necessity check quantifies over **every completion of the other inputs**. For example, under `Y = A OR B`, `(A=0, B=1, Y=1)` refutes “A is necessary,” even though `(0,0)` produces zero. A conjunction test checks each factor\'s necessity and their joint sufficiency. Inhibition checks paired contexts and a strict effect; an existential effect is distinct from universal monotonicity. Reference equations are exhaustively finite, with at most eight local rows. Mutation counterexamples and every inspected prose claim are retained. Formal checks establish agreement with a translated proposition; Codex\'s translation of prose remains reviewable, not independently validated.',
        '## Figures and comparison',
        'All operative reference edges are shown, labelled with specific phrases and sentence IDs. Rules are explicitly identified as assumptions introduced by the controlled adaptations. No failed generated graph is presented as accepted. The [comparison table](COMPARISON.tsv) lists every frozen question, expected answer, direct answer, failed executable answer, correctness and separate reference execution.',
        '**Best introductory figure: [The Crow and the Pitcher](crow.svg)** (PDF page 3). Its short stone → rise → reach → drink sequence also reveals a useful distinction: adding stones is not universally necessary when the water is initially reachable. It shows a joint requirement, substitution, and an unchanged-outcome intervention without numerical fluid mechanics. The figure illustrates the author-specified method, not autonomous causal discovery.',
        '## Resources, failures and limits',
        '%s, revision `%s`, AWQ, vLLM %s, thinking disabled, temperature 0.2, recorded seeds, on the existing RTX 4090. %d requests (%d first, %d repairs), **%s generated tokens**, %s prompt tokens; %.1f seconds in requests and **%.2f minutes of service runtime**, including startup and a missing-module launch failure. Peak sampled GPU allocation: %s MiB. The project watchdog stopped only its registered model service after completion. Budget: 40,000 generated tokens or one hour, whichever first. No new pod or paid API was used.'%(usage['model'],usage['revision'],usage['vllm'],usage['requests'],usage['first_requests'],usage['repair_requests'],format(usage['generated_tokens'],','),format(usage['prompt_tokens'],','),usage['request_seconds'],usage['service_seconds']/60,format(int(usage['max_memory_mib']),',')),
        'Verification: 98 software tests passed, including 15 new targeted tests. A public-only staged export reproduced all three SVGs, the three-page PDF, the comparison table and this report byte-for-byte. These software checks do not establish source validity.',
        'The first runner failed before inference because existing solver modules were absent remotely. Synchronizing project code resolved it within the same budget. There were no request transport failures or JSON parse failures. The archived original runner/validation logs distinguish execution-time behavior from later diagnostic improvements. Codex authoring/review token usage is unavailable; it is not included in Qwen usage.',
        'These checks establish that the supplied controlled reference SCMs execute correctly and that stronger quantified checks expose false causal claims. They do **not** demonstrate reliable autonomous construction from these narratives; direct answers succeed where the structured pipeline fails. Nor do they validate the traditional tales\' counterfactuals, general narrative understanding, reader comprehension, or the Game of Thrones interpretations.',
        'A bounded next experiment should test schema-constrained output with aggregate compiler feedback on these already-development cases, keeping the same references and reporting it as a new attempt series. Its central question is whether it yields a valid model **without** fixing factual/prose mistakes by hand. Independent review should adjudicate the claimed irreparability, the Wolf factual-response error and the extra crow prerequisite before using any generated narrative claim in a paper.'
    ]
    report='\n\n'.join(parts)+'\n'
    report=re.sub(r'(?<=\|)\n\n(?=\|)', '\n', report)
    (out/'RESULTS.md').write_text(report)


def review_packet(root,records,results):
    """Readable expanded audit; exact underlying records remain in compact release."""
    root=Path(root);data=frozen(root);parts=['# Simple stories: independent review pending',
        'Assistant audit only. Read the numbered texts, raw outputs and local counterexamples. No corrected graph is scored as generated.']
    for s in data['stories']:
        for version in ['natural','controlled']:
            ident=s['id']+'_'+version+'_attempt0';r=next(x for x in records['requests'] if x['id']==ident)
            result=next(x for x in results['constructions'] if x['id']==ident)
            parts+=['## '+s['title']+' / '+version]+['**'+x['id']+' ('+x['origin']+')** '+x['text'] for x in s[version]]
            parts+=['### First output\n```json\n'+json.dumps(r.get('parsed'),indent=2)+'\n```',
                    '### Assistant audit\n```json\n'+json.dumps(result['audit'],indent=2)+'\n```',
                    '### Local function diagnostics (not an executable graph)\n```json\n'+json.dumps(result.get('local_diagnostics',[]),indent=2)+'\n```',
                    'Review questions: Which event, directional and exact-function claims does the text support? Does each translated formal claim express the actual prose? Which missing behaviors must remain unknown?']
    path=root/'.private/simple_stories/REVIEW_PACKET.md';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n\n'.join(parts)+'\n')


def reproduce(root):
    import shutil,subprocess
    root=Path(root);records=load_records(root);data=frozen(root)
    if records['frozen_sha256']!=FROZEN_SHA:raise ValueError('Archive belongs to another freeze')
    for r in records['requests']:
        if fingerprint(r['request'])!=r['request_sha256']:raise ValueError('Request altered '+r['id'])
        if 'raw' in r and 'parsed' in r and json.loads(r['raw']['choices'][0]['message']['content'])!=r['parsed']:
            raise ValueError('Parsed output altered '+r['id'])
        if r['started_at']<=data['frozen_at']:raise ValueError('Generation preceded freeze')
    byid={r['id']:r for r in records['requests']}
    for i,story in enumerate(data['stories']):
        for j,version in enumerate(['natural','controlled']):
            ident=story['id']+'_'+version+'_attempt0'
            if ident in byid and byid[ident]['request']!=construction_request(story,version,2*i+j):
                raise ValueError('First construction request changed '+ident)
        ident=story['id']+'_direct_attempt0'
        if ident in byid and byid[ident]['request']!=direct_request(story,i):
            raise ValueError('Direct baseline request changed '+ident)
    results,compiled=analyze(root,records)
    inventory=render_figures(root,records,results);results['figures']=inventory
    if 'result_snapshot' in records and records['result_snapshot']!=results:
        raise ValueError('Offline results differ from archived snapshot; inspect and preserve the discrepancy')
    write_report(root,records,results,inventory);review_packet(root,records,results)
    atomic_json(root/'.private/simple_stories/results.json',results)
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm','-scale-to-x','1050','-scale-to-y','-1','-png',
            str(root/FOLDER/'FIGURES.pdf'),str(root/'.private/simple_stories/preview')],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    print(json.dumps({'primary':results['primary'],'reference_checks':len(results['reference_checks']),
        'mutations_detected':sum(x['detected'] for x in results['mutations']), 'figures':inventory,
        'generated_tokens':results['resource_usage']['generated_tokens']},indent=2))
    return results
