"""Independent synthetic SCM generator and guaranteed-consistent text renderer."""
import copy, itertools, json, random
from pathlib import Path
import networkx as nx
from .structural_programs import SCM, evaluate


def ref(x): return {'ref':x}
def op(kind,*args): return {'op':kind,'args':list(args)}


def generate(size, seed, incomplete):
    rng=random.Random(seed);nodes=[];background={};states={};nroots=3 if size==12 else 4
    identifiers=['V%02d'%i for i in range(size)]
    for i,ident in enumerate(identifiers):
        base={'id':ident,'label':'Station '+ident,'type':'bool','time':i,'reference':0}
        if i<nroots:
            uid='U'+ident;background[uid]={'type':'bool','observed':rng.randrange(2)}
            base.update(parents=[],noise=[uid],expr={'noise':uid});value=background[uid]['observed']
        else:
            # A random DAG with a backbone and shared earlier parents; no literary rules.
            parents=[identifiers[i-1],rng.choice(identifiers[:i-1])]
            rng.shuffle(parents);a,b=map(ref,parents)
            family=['and','or','xor','inhibit','necessary','conditional'][(i+seed)%6]
            if family=='inhibit':expr=op('and',a,op('not',b))
            elif family=='necessary':expr=op('and',op('not',a),b)
            elif family=='conditional':expr=op('if',a,op('not',b),b)
            else:expr=op(family,a,b)
            base.update(parents=parents,noise=[],expr=expr)
            value=evaluate(expr,{k:states[k] for k in parents},{})
        base['observed']=value;states[ident]=value;nodes.append(base)
    model={'id':'scm_%d'%seed,'nodes':nodes,'background':background,'outcome':identifiers[-1]}
    SCM(model)
    hidden=[];alternatives=[]
    if incomplete:
        eligible=[n for n in nodes if n['parents']]
        # Select an ambiguity with observationally compatible and intervention-distinct equations.
        for target in reversed(eligible):
            a,b=map(ref,target['parents'])
            exprs=[op('and',a,b),op('or',a,b),op('xor',a,b),op('and',a,op('not',b)),op('and',op('not',a),b)]
            candidate_models=[]
            for expression in exprs:
                m=copy.deepcopy(model);m['nodes'][identifiers.index(target['id'])]['expr']=expression
                try: SCM(m);candidate_models.append(m)
                except ValueError: pass
            unique={json.dumps(m,sort_keys=True):m for m in [model]+candidate_models}
            if len(unique)>1:
                hidden=[target['id']];alternatives=list(unique.values());break
    if hidden:
        # Exhaust all deterministic binary rules on the two declared parents,
        # conditional on the factual observation and active dependence.
        target=hidden[0];idx=identifiers.index(target);a,b=map(ref,model['nodes'][idx]['parents'])
        alternatives=[]
        for table in itertools.product((0,1),repeat=4):
            expr=op('if',a,op('if',b,{'const':table[3]},{'const':table[2]}),op('if',b,{'const':table[1]},{'const':table[0]}))
            candidate=copy.deepcopy(model);candidate['nodes'][idx]['expr']=expr
            try: SCM(candidate);alternatives.append(candidate)
            except ValueError:pass
    return model,hidden,alternatives or [model]


def verbal(expr, variant=0):
    if 'ref' in expr: return expr['ref']+' is active'
    if 'noise' in expr: return expr['noise']+' is active'
    if 'const' in expr: return str(expr['const'])
    args=[verbal(a,variant) for a in expr['args']];kind=expr['op']
    if kind=='and':return '('+(' and ' if not variant else ' as well as ').join(args)+')'
    if kind=='or':return '('+(' or ' if not variant else ' or, inclusively, ').join(args)+')'
    if kind=='xor':return '(exactly one of '+args[0]+' and '+args[1]+')'
    if kind=='not':return '(it is not the case that '+args[0]+')'
    if kind=='if':return '(if '+args[0]+' then '+args[1]+'; otherwise '+args[2]+')'
    raise ValueError(kind)


def render(model, hidden, variant=0):
    paragraphs=[]
    for node in model['nodes']:
        ident=node['id'];sid='seg_'+ident
        if not node['parents']:
            body='%s has a persistent external setting %s, fixed at %d in this individual. Its activity equals that setting.'%(ident,node['noise'][0],node['observed'])
        elif ident in hidden:
            body='%s depends on %s. The local combination rule is missing from the record; do not infer it from the observed state.'%(ident,' and '.join(node['parents']))
        else:
            body=('%s is active if and only if %s. Otherwise it is inactive.'%(ident,verbal(node['expr'],variant)))
        body+=' Its factual activity is %d.'%node['observed']
        paragraphs.append({'id':sid,'text':body,'node_id':ident,'mechanism_available':ident not in hidden})
    if variant: random.Random(179).shuffle(paragraphs)
    preamble='A synthetic network of stations uses binary activity: active=1, inactive=0. Every mechanism is deterministic. Interventions replace only the target equation; external settings stay fixed. IDs name states, not time. This record is the entire evidence. '
    return preamble+'\n'+'\n'.join('['+p['id']+'] '+p['text'] for p in paragraphs),paragraphs


def queries(model, hidden, compatible):
    scm=SCM(model);ids=list(scm.nodes);target=model['outcome'];states=scm.solve()
    # Fixed queries are designed without seeing any inference output.
    proposals=[('factual',{},target),('intervention',{ids[0]:1-states[ids[0]]},target),
               ('counterfactual',{ids[len(ids)//2]:1-states[ids[len(ids)//2]]},target),
               ('joint',{ids[0]:1,ids[1]:1},target),
               ('joint',{ids[-2]:0,ids[-3]:1},target),
               ('counterfactual',{ids[-2]:1-states[ids[-2]]},target)]
    result=[]
    for i,(kind,interventions,outcome) in enumerate(proposals):
        values=sorted(set(SCM(m).solve(interventions=interventions)[outcome] for m in compatible))
        result.append({'id':'q%d'%i,'kind':kind,'target':outcome,'do':interventions,'gold_possible':values,
                       'identified':len(values)==1,'text':('What is the factual activity of '+outcome+'?' if not interventions else 'With the SAME external settings, set '+json.dumps(interventions)+' by intervention. What is '+outcome+'? Return all supported values or abstain if underdetermined.')})
    a=ids[1];b=ids[-1]
    result.append({'id':'q6','kind':'ancestry','source':a,'target':b,'gold_possible':[int(nx.has_path(scm.graph,a,b))],'identified':True,'text':'Is '+a+' an ancestor of '+b+' in the documented causal graph? Return 1 for yes, 0 for no.'})
    h=hidden[0] if hidden else ids[-1]
    result.append({'id':'q7','kind':'evidence','target':h,'gold_possible':[int(h not in hidden)],'identified':True,'text':'Does the record specify the complete mechanism for '+h+'? Return 1 for yes and 0 for no.'})
    return result


def build(root):
    root=Path(root);cases=[]
    for size in (12,18,24):
        for condition in ('complete','incomplete'):
            for j in range(10):
                seed=10000+size*100+(condition=='incomplete')*20+j
                model,hidden,alternatives=generate(size,seed,condition=='incomplete')
                split='development' if j<2 else 'calibration' if j<4 else 'test'
                for variant in range(2 if split=='test' else 1):
                    narrative,segments=render(model,hidden,variant)
                    case={'id':model['id']+'_v%d'%variant,'scm_id':model['id'],'seed':seed,'split':split,'size':size,'condition':condition,'variant':variant,'narrative':narrative,'segments':segments,'gold':model,'hidden_nodes':hidden,'compatible_family':alternatives,'queries':queries(model,hidden,alternatives),'verification':'deterministic renderer and automated solver checks; no human review'}
                    cases.append(case)
    (root/'benchmark/cases.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in cases))
    manifest={'independent_scms':60,'sizes':[12,18,24],'splits':{'development':12,'calibration':12,'test':36},'narratives':len(cases),'queries_per_narrative':8,'test_variants':'deterministic connective paraphrase and paragraph reordering','split_unit':'generating SCM, both variants kept together','gold_hidden_from_inference':True,'ambiguity_family':'all deterministic binary truth tables over the declared two parents, restricted to active dependence and factual compatibility','parameters_frozen_before_test':True}
    (root/'benchmark/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    import sys
    print(build(sys.argv[1]))
