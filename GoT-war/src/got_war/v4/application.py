"""Finite application compiler. Case interpretations are data, never code rules."""
import ast
import copy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path

from ..budget import atomic_json
from ..v3.core import (build_family, check_claims, fingerprint, query,
                      validate_representation, verify_reported_result)


def expression(text, inputs):
    """Small Boolean notation -> restricted typed expression; never Python eval."""
    def convert(n):
        if isinstance(n, ast.Name) and n.id in inputs:
            return {'op':'var','name':n.id}
        if isinstance(n, ast.Constant) and type(n.value) is int and n.value in (0,1):
            return {'op':'const','value':n.value}
        if isinstance(n, ast.BoolOp) and isinstance(n.op,(ast.And,ast.Or)):
            return {'op':'and' if isinstance(n.op,ast.And) else 'or','args':[convert(v) for v in n.values]}
        if isinstance(n, ast.UnaryOp) and isinstance(n.op,ast.Not):
            return {'op':'not','args':[convert(n.operand)]}
        raise ValueError('Restricted Boolean expression only; undeclared inputs rejected')
    return convert(ast.parse(text,mode='eval').body)


def value(expr, state):
    op=expr['op']
    if op=='const':return expr['value']
    if op=='var':return state[expr['name']]
    values=[value(x,state) for x in expr['args']]
    if op=='not':return int(not values[0])
    if op=='and':return int(all(values))
    if op=='or':return int(any(values))
    raise ValueError('Invalid typed operator')


def expand(draft, packet, case):
    """Resolve generated reference IDs; add only schema metadata, never causal prose."""
    refs={r['id']:{k:v for k,v in r.items() if k!='id'} for r in draft['evidence']}
    rep=copy.deepcopy(draft['representation'])
    for v in rep['variables']:
        v.setdefault('domain',[0,1])
        v['evidence']=[refs[r] for r in v['evidence']]
    for e in rep['edges']:
        e['evidence']=[refs[r] for r in e['evidence']]
        e['contradictions']=[refs[r] for r in e.get('contradictions',[])]
    for m in rep['mechanisms']:
        m['evidence']=[refs[r] for r in m['evidence']]
    rep=validate_representation(rep,packet)
    target=next(v for v in rep['variables'] if v['id']==rep['outcome'])
    if target['definition']!=case['outcome'] or target['event_time']!=case['endpoint_code']:
        raise ValueError('Outcome scope/time changed')
    if len(rep['variables'])>case['max_variables'] or len(rep['edges'])>case['max_edges']:
        raise ValueError('Declared case-specific representation budget exceeded')
    if any(len(m['parents'])>case['max_parents'] for m in rep['mechanisms']):
        raise ValueError('Local parent bound exceeded; use justified decomposition or retain partial scope')
    return rep


def compile_families(rep, draft, packet):
    nodes={v['id']:v for v in rep['variables']}
    observed=[]
    for m in rep['mechanisms']:
        child=m['child'];v=nodes[child]
        constraints=[]
        if v['factual'] is not None and all(nodes[p]['factual'] is not None for p in m['parents']):
            constraints=[{'id':child+'_observed','kind':'row','when':{p:nodes[p]['factual'] for p in m['parents']},
                'allowed':[v['factual']],'basis':'evidence','rationale':'Observed configuration only; no unobserved row is filled.',
                'evidence':v['evidence']+sum([nodes[p]['evidence'] for p in m['parents']],[])}]
        observed.append({'child':child,'background':[],'scope_status':draft.get('scope_status','declared_family'),
            'scope_assumptions':draft['scope_assumptions'],'constraints':constraints})
    partial=build_family(rep,{'functions':observed},packet)
    scenarios=[]
    for spec in draft.get('scenarios',[]):
        functions=copy.deepcopy(observed)
        if set(spec['equations'])!={m['child'] for m in rep['mechanisms']}:
            raise ValueError('Scenario must declare every fixed structural mechanism')
        typed={}
        for f in functions:
            m=next(m for m in rep['mechanisms'] if m['child']==f['child'])
            expr=expression(spec['equations'][f['child']],m['parents']);typed[f['child']]=expr
            for i,row in enumerate(itertools.product(*(nodes[p]['domain'] for p in m['parents']))):
                state=dict(zip(m['parents'],row));out=value(expr,state)
                f['constraints'].append({'id':f['child']+'_assumed_'+str(i),'kind':'row','when':state,
                    'allowed':[out],'basis':'assumption','rationale':spec['assumptions'][f['child']], 'evidence':[]})
        family=build_family(rep,{'functions':functions},packet)
        if not family['models']:
            raise ValueError('Scenario '+spec['id']+' conflicts with established observations or lacks executable scope: '+family['coverage'])
        # Full enumeration checks separately authored prose predicates, not generated table paraphrases.
        for claim in spec.get('claims',[]):
            m=next((m for m in rep['mechanisms'] if m['child']==claim.get('child')),None)
            if m is None or claim.get('record_id')!=m['id']:
                raise ValueError('Formal claim must identify an actual child mechanism')
            prose=m['description']+' '+m['joint_description']+' '+spec['interpretation']+' '+spec['assumptions'][m['child']]
            if not claim.get('text') or claim['text'] not in prose:
                raise ValueError('Formal claim must quote actual mechanism or scenario prose')
        claims=check_claims(rep,family,spec.get('claims',[]))
        if any(c['status']!='entailed_within_family' for c in claims):
            raise ValueError('Description/function counterexample in '+spec['id']+': '+json.dumps(claims))
        scenarios.append({'id':spec['id'],'label':spec['label'],'interpretation':spec['interpretation'],
            'family':family,'typed_expressions':typed,'claims':claims,'family_coverage':'One explicit hypothetical SCM, not identified by narrative evidence'})
    return partial,scenarios


def compile_attempt(root, case, draft, packet, attempt=0):
    """Return actionable errors for a bounded MODEL revision; never relax facts."""
    root=Path(root);folder=root/'runs/application_v4_20261013'/case['id'];folder.mkdir(parents=True,exist_ok=True)
    if attempt>2:raise ValueError('Two targeted repair rounds maximum')
    try:
        rep=expand(draft,packet,case)
        partial,scenarios=compile_families(rep,draft,packet)
        # A source/display issue cannot silently remove an operative edge.
        edgeids={e['id'] for e in rep['edges']}
        review=draft['review'];assessed={r['id'] for r in review['edges']}
        if edgeids!=assessed or len(review['edges'])!=len(edgeids):raise ValueError('Assess every actual displayed edge exactly once')
        known_bad=[r['id'] for r in review['edges'] if r['description_function']=='contradicted' or r['source_description']=='contradicted']
        if known_bad:raise ValueError('Known contradictory operative edges require revision or partial-only display: '+str(known_bad))
        if any(r['description_function']!='consistent' for r in review['edges']):
            raise ValueError('Unresolved description/function review: retain partial record without intervention display')
        for e in rep['edges']:
            assessed_edge=next(r for r in review['edges'] if r['id']==e['id'])
            if e['status']=='explicit' and assessed_edge['source_description']!='supported':
                raise ValueError('Unresolved source review cannot be displayed as explicit support')
        queries=draft['queries']
        if not 2<=len(queries)<=3:raise ValueError('Select two or three substantive questions before execution')
        if any(rep['outcome'] in q['do'] for q in queries):raise ValueError('Do not use direct outcome manipulation as explanatory query')
        # Exact questions are checkpointed BEFORE computing any answer.
        freeze=folder/'queries_frozen.json';payload={'representation_sha256':fingerprint(rep),'queries':queries}
        if freeze.exists() and json.loads(freeze.read_text())!=payload:
            raise ValueError('Selected questions/representation changed after answer freeze; preserve separate revision')
        atomic_json(freeze,payload)
        answers=[]
        for q in queries:
            broad=query(rep,partial,q['do'])
            conditional=[]
            for s in scenarios:
                result=query(rep,s['family'],q['do'])
                assert verify_reported_result(rep,s['family'],q['do'],result)['passed']
                conditional.append({'scenario':s['id'],'result':result})
            answers.append(dict(q,partial_result=broad,conditional=conditional))
        result={'case':case['id'],'scope':case,'generation':draft['generation'],'representation':rep,
            'partial_family':partial,'scenarios':scenarios,'queries':answers,'review':review,
            'status':'executable_conditional' if scenarios else 'partial_mechanism_graph',
            'operative_edge_ids':sorted(edgeids),'displayed_edge_ids':sorted(edgeids),
            'source_packet_sha256':packet['packet_sha256'],'independent_review':'pending',
            'attempt':attempt,'draft_sha256':fingerprint(draft)}
        atomic_json(folder/'validated.json',result)
        return result
    except Exception as error:
        atomic_json(folder/('compilation_failed_%d.json'%attempt),{'draft':draft,'error':type(error).__name__+': '+str(error),
            'repair_instruction':'Revise the specific cited function, claim or representation with evidence and retain the prior draft. Established factual rows cannot be relaxed merely to pass.',
            'at':datetime.now(timezone.utc).isoformat()})
        raise


if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);ident=sys.argv[2]
    cfg=json.loads((root/'configs/v4_campaign.json').read_text());case=next(c for c in cfg['cases'] if c['id']==ident)
    private=root/'.private/v4'/ident
    r=compile_attempt(root,case,json.loads((private/'draft.json').read_text()),json.loads((private/'construction_packet.json').read_text()),int(sys.argv[3]) if len(sys.argv)>3 else 0)
    print(json.dumps({'case':ident,'status':r['status'],'nodes':len(r['representation']['variables']),'edges':len(r['representation']['edges']),
        'questions':[{'id':q['id'],'partial':q['partial_result']['values'],'conditional':[x['result']['values'] for x in q['conditional']]} for q in r['queries']]}))
