"""Independent version-2 SCM generation and exact-information rule texts."""
import collections
import copy
import itertools
import json
from pathlib import Path
import random
import networkx as nx
from ..benchmark import verbal, ref, op
from ..budget import atomic_json
from ..structural_programs import SCM, evaluate
from .mechanisms import compatible_family, fingerprint, outcome_sets
from .runtime import paths

CONDITIONS=('complete','missing_intermediate','missing_outcome','multiple_missing')


def generate(size, seed, condition):
    rng=random.Random(seed)
    for attempt in range(100):
        nodes=[];background={};states={}
        for i in range(size):
            ident='V%02d'%i
            node={'id':ident,'label':'Station '+ident,'type':'bool','time':i,'reference':0,'unknown':False}
            if i<3:
                noise='U'+ident;value=rng.randrange(2)
                background[noise]={'type':'bool','observed':value}
                node.update(parents=[],noise=[noise],expr={'noise':noise})
            else:
                parents=sorted(rng.sample(list(states),2))
                a,b=map(ref,parents);family=rng.choice(('and','or','xor','inhibit','nand','reverse_inhibit'))
                expression=(op('and',a,op('not',b)) if family=='inhibit' else
                            op('and',op('not',a),b) if family=='reverse_inhibit' else
                            op('not',op('and',a,b)) if family=='nand' else op(family,a,b))
                value=evaluate(expression,states,{})
                node.update(parents=parents,noise=[],expr=expression,generated_family=family)
            node['observed']=value;states[ident]=value;nodes.append(node)
        model={'id':'v2_scm_%d'%seed,'nodes':nodes,'background':background,'outcome':nodes[-1]['id']}
        scm=SCM(model);eligible=sorted(n for n in nx.ancestors(scm.graph,model['outcome']) if scm.nodes[n]['parents'])
        needed=2 if condition=='multiple_missing' and seed%2==0 else 1
        if condition=='complete' or condition=='missing_outcome' or len(eligible)>=needed:break
    else:raise ValueError('Topology gate exhausted')
    hidden=[]
    if condition=='missing_intermediate':hidden=[rng.choice(eligible)]
    elif condition=='missing_outcome':hidden=[model['outcome']]
    elif condition=='multiple_missing':
        hidden=sorted(rng.sample(eligible,2)) if seed%2==0 else [rng.choice(eligible),model['outcome']]
    partial=copy.deepcopy(model)
    for n in partial['nodes']:n['unknown']=n['id'] in hidden
    family=compatible_family(partial)
    if not family['summary']['exhaustive']:raise ValueError('Gold benchmark must have exhaustive compatible coverage')
    return model,hidden,family,attempt


def render(model, hidden):
    segments=[]
    for node in model['nodes']:
        ident=node['id']
        if not node['parents']:
            rule='%s equals its external setting %s, fixed at %d in this individual.'%(ident,node['noise'][0],node['observed'])
        elif ident in hidden:
            rule='%s depends actively on %s, but the exact combination rule is absent. All deterministic Boolean functions of precisely these inputs that depend on each input and agree with the recorded factual states remain possible.'%(ident,', '.join(node['parents']))
        else:
            rule='%s is active if and only if %s; otherwise it is inactive.'%(ident,verbal(node['expr']))
        rule+=' Factual activity: %s=%d.'%(ident,node['observed'])
        segments.append({'id':'seg_'+ident,'node_id':ident,'text':rule,'rule_known':ident not in hidden})
    preamble=('This complete record describes binary stations: active=1, inactive=0. '
              'Every rule is deterministic and uses exactly its documented inputs. '
              'An intervention replaces only the named equations; all external settings remain fixed. '
              'For missing rules consider every compatible deterministic Boolean function, not a guessed preferred rule. '
              'Factual states constrain missing rules but do not specify unseen input rows. No hidden common cause is assumed in this controlled family.')
    return preamble+'\n'+'\n'.join('['+s['id']+'] '+s['text'] for s in segments),segments


def questions(model, family, seed):
    scm=SCM(model);target=model['outcome'];states=scm.solve();ids=[n for n in scm.order if n!=target]
    # Fixed enumeration, then seeded joint queries and factual-value controls.
    # Neither sampling nor omission selection sees method outputs or scores.
    proposals=[('single',{n:1-states[n]}) for n in ids]
    rng=random.Random(seed+731)
    pairs=list(itertools.combinations(ids,2));rng.shuffle(pairs)
    proposals += [('joint',{a:1-states[a],b:1-states[b]}) for a,b in pairs[:3]]
    controls=list(ids);rng.shuffle(controls)
    proposals += [('factual_value_control',{n:states[n]}) for n in controls[:3]]
    queries=[]
    for i,(kind,intervention) in enumerate(proposals):
        relevant=set()
        for changed in intervention:
            relevant |= (nx.descendants(scm.graph,changed)&(nx.ancestors(scm.graph,target)|{target}))
        relevant-=set(intervention)
        queries.append({'id':'q%02d'%i,'kind':kind,'target':target,'do':intervention,
            'text':'With the SAME external settings, intervene to set '+json.dumps(intervention,sort_keys=True)+'. What values of '+target+' are supported by the record?',
            'relevance':{'seg_'+n:2 if n in relevant and not scm.nodes[n].get('unknown') else 1 if n in relevant else 0 for n in scm.nodes}})
    possible=outcome_sets(family['models'],queries)
    for q,answer in zip(queries,possible):
        q.update(gold_possible=answer['values'],identified=len(answer['values'])==1,
            factual=states[target],generating_outcome=scm.solve(interventions=q['do'])[target],
            changed=(answer['values'][0]!=states[target]) if len(answer['values'])==1 else None)
    return queries


def build(root):
    root,run,result=paths(root);dest=run/'benchmark_cases.jsonl'
    if dest.exists():return json.loads((run/'benchmark_design.json').read_text())
    cases=[]
    for condition_index,condition in enumerate(CONDITIONS):
        for size in (8,12):
            for replicate in range(15):
                seed=270000+size*1000+condition_index*100+replicate
                model,hidden,family,retries=generate(size,seed,condition)
                narrative,segments=render(model,hidden)
                question_model=copy.deepcopy(model)
                for n in question_model['nodes']:n['unknown']=n['id'] in hidden
                q=questions(question_model,family,seed)
                split='development' if replicate<3 else 'calibration' if replicate<6 else 'test'
                cases.append({'id':model['id'],'scm_id':model['id'],'seed':seed,'split':split,'condition':condition,'size':size,
                    'narrative':narrative,'segments':segments,'gold':model,'hidden_nodes':hidden,
                    'compatible_family_summary':family['summary'],'queries':q,'topology_retries':retries,
                    'information_fidelity':'Deterministic explicit rule renderer; no uncontrolled paraphrase or model-generated gold.'})
    dest.write_text(''.join(json.dumps(case,separators=(',',':'))+'\n' for case in cases))
    strata=[]
    for split in ('development','calibration','test'):
        for condition in CONDITIONS:
            group=[c for c in cases if c['split']==split and c['condition']==condition]
            counts=collections.Counter('underidentified' if not q['identified'] else 'identified_changed' if q['changed'] else 'identified_unchanged' for c in group for q in c['queries'])
            strata.append({'split':split,'condition':condition,'scms':len(group),'factual_outcomes':dict(collections.Counter(str(c['queries'][0]['factual']) for c in group)),**counts})
    manifest={'version':2,'independent_scms':len(cases),'splits':dict(collections.Counter(c['split'] for c in cases)),
        'conditions':list(CONDITIONS),'sizes':[8,12],'queries':'All non-outcome single flips, three seeded joint flips, three factual-value controls. No direct outcome overrides.',
        'gold_family':'All active two-parent deterministic Boolean functions consistent with factual rows, jointly enumerated for all omitted rules; exact in every generated case.',
        'source_relevance':'Query-specific gold causal slice: descendants of intervened nodes that are outcome ancestors, excluding intervened equations. Grade 2 for available rules, 1 for explicitly missing rules, 0 otherwise. Defined without generated paths or method outputs; evaluates structural information relevance, not human literary importance.',
        'scm_ids_by_split':{s:[c['id'] for c in cases if c['split']==s] for s in ('development','calibration','test')},
        'distinct_programs':len({fingerprint([{k:n[k] for k in ('id','parents','expr')} for n in c['gold']['nodes']]) for c in cases}),
        'sha256':__import__('hashlib').sha256(dest.read_bytes()).hexdigest(),'strata':strata,
        'status':'Development design generated; freeze model/prompts/analysis after measured pilot and before test inference.'}
    atomic_json(run/'benchmark_design.json',manifest)
    return manifest


if __name__=='__main__':
    import sys
    print(json.dumps(build(sys.argv[1] if len(sys.argv)>1 else '.'),indent=2))
