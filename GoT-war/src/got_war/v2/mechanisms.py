"""Inspectable local behavior and bounded families of unresolved functions."""
import copy
import hashlib
import itertools
import json
import math
import random
from ..structural_programs import SCM, InvalidModel, domain, evaluate, equation


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def inspect_mechanism(scm, ident, limit=256):
    node = scm.nodes[ident]
    parents = node['parents']
    noise = node.get('noise', [])
    names = parents + noise
    specs = [scm.nodes[p] for p in parents] + [scm.background[u] for u in noise]
    domains = [domain(spec) for spec in specs]
    exact = (math.prod(map(len, domains)) <= limit and all(
        s['type'] in ('bool','category') or (s['type']=='int' and s['bounds'][1]-s['bounds'][0]<=15)
        for s in specs))
    rng = random.Random(9107)
    contexts = list(itertools.product(*domains)) if exact else list(dict.fromkeys(
        tuple(rng.choice(d) for d in domains) for _ in range(limit)))
    rows = []
    for values in contexts:
        p = dict(zip(parents, values[:len(parents)]))
        u = dict(zip(noise, values[len(parents):]))
        rows.append({'inputs':dict(zip(names, values)), 'output':evaluate(node['expr'],p,u)})
    changes = []
    for parent in parents:
        witnesses = []
        for row in rows:
            inputs = row['inputs']
            for other in domain(scm.nodes[parent]):
                if other == inputs[parent]:
                    continue
                changed = dict(inputs, **{parent:other})
                result = evaluate(node['expr'], {p:changed[p] for p in parents}, {u:changed[u] for u in noise})
                if result != row['output']:
                    witnesses.append({'context':inputs, 'set_to':other, 'before':row['output'], 'after':result})
        polarity = 'categorical or unresolved'
        if scm.nodes[parent]['type']=='bool' and node['type']=='bool':
            differences = {r['after']-r['before'] for r in witnesses if r['context'][parent]==0 and r['set_to']==1}
            polarity = 'positive' if differences=={1} else 'inhibitory' if differences=={-1} else 'mixed' if differences else 'inactive'
        changes.append({'parent':parent,'polarity':polarity,'witness_count':len(witnesses),'witnesses':witnesses[:8]})
    necessary = []; sufficient = []; joint = []; substitutes = []
    if node['type']=='bool':
        positive = [row for row in rows if row['output']==1]
        for name, values in zip(names, domains):
            for value in values:
                matching = [r for r in rows if r['inputs'][name]==value]
                if positive and all(r['inputs'][name]==value for r in positive):
                    necessary.append({name:value})
                if matching and all(r['output']==1 for r in matching):
                    sufficient.append({name:value})
        lookup = {tuple(r['inputs'][n] for n in names):r['output'] for r in rows}
        for a,b in itertools.combinations([p for p in parents if scm.nodes[p]['type']=='bool'],2):
            others = [n for n in names if n not in (a,b)]
            contexts_other = {tuple(r['inputs'][n] for n in others) for r in rows}
            for context in sorted(contexts_other, key=repr):
                base = dict(zip(others,context));outputs=[]
                for x,y in ((0,0),(0,1),(1,0),(1,1)):
                    combined=dict(base, **{a:x,b:y})
                    outputs.append(lookup.get(tuple(combined[n] for n in names)))
                item={'parents':[a,b],'context':base}
                if outputs==[0,0,0,1]:joint.append(item)
                if outputs==[0,1,1,1]:substitutes.append(item)
    qualifiers = 'Exhaustive over the declared finite inputs.' if exact else 'Bounded probes only; untested behavior remains unresolved.'
    description = ['Fixed equation: '+equation(node['expr'])+'.', qualifiers]
    if node['type']=='bool':
        description += ['Necessary input conditions for output 1 in these rows: '+json.dumps(necessary)+'.',
                        'Individually sufficient input conditions for output 1 in these rows: '+json.dumps(sufficient)+'.']
    return {'node':ident, 'equation':equation(node['expr']), 'coverage':'exhaustive' if exact else 'bounded probes',
            'rows':rows,'parent_changes':changes,'necessary_for_one':necessary,'sufficient_for_one':sufficient,
            'joint_enabling':joint,'substitution':substitutes,'derived_description':' '.join(description),
            'interpretation':'Behavior of the assumed function, not evidence that the story obeys it.',
            'signature':fingerprint(rows)}


def table_expression(parents, domains, outputs):
    """Compile a finite lookup table into the existing restricted typed AST."""
    def build(level, offset):
        if level==len(parents):
            return {'const':outputs[offset]}
        step=math.prod(len(d) for d in domains[level+1:])
        branches=[build(level+1,offset+i*step) for i in range(len(domains[level]))]
        value=branches[-1]
        for i in reversed(range(len(branches)-1)):
            value={'op':'if','args':[{'op':'eq','args':[{'ref':parents[level]},{'const':domains[level][i]}]},branches[i],value]}
        return value
    return build(0,0)


def compatible_family(model, max_models=512, max_local_tables=256, seed=311):
    """Enumerate finite functions jointly, with explicit sampled-coverage flags.

    The family conditions on declared parents, finite domains, factual states,
    active dependence and any explicitly supplied local input-output constraints.
    Unknown graph structure/confounding is outside this family.
    """
    base=SCM(model)
    unknown=[n for n in model['nodes'] if n.get('unknown') or n.get('unresolved')]
    options={};coverage=[];rng=random.Random(seed)
    for node in unknown:
        parents=node['parents'];domains=[domain(base.nodes[p]) for p in parents]
        outputs=domain(node);contexts=list(itertools.product(*domains))
        finite=all(base.nodes[p]['type'] in ('bool','category') for p in parents) and node['type'] in ('bool','category')
        if not parents or node.get('noise') or not finite or len(contexts)>8:
            options[node['id']]=[node['expr']]
            coverage.append({'node':node['id'],'coverage':'single supplied candidate only','reason':'outside bounded finite family'})
            continue
        combinations=len(outputs)**len(contexts)
        exhaustive=combinations<=max_local_tables
        tables=list(itertools.product(outputs,repeat=len(contexts))) if exhaustive else [tuple(rng.choice(outputs) for _ in contexts) for _ in range(max_local_tables)]
        # Always retain the supplied admissible function, without giving it a probability.
        supplied=tuple(evaluate(node['expr'],dict(zip(parents,c)),{}) for c in contexts)
        tables=list(dict.fromkeys([supplied]+tables));valid=[]
        constraints=[{'inputs':{p:base.nodes[p]['observed'] for p in parents},'output':node['observed']}]+node.get('function_constraints',[])
        for table in tables:
            lookup=dict(zip(contexts,table))
            if any(lookup.get(tuple(row['inputs'][p] for p in parents))!=row['output'] for row in constraints):continue
            active=True
            for j,p in enumerate(parents):
                if not any(lookup[c]!=lookup[c[:j]+(other,)+c[j+1:]] for c in contexts for other in domains[j]):active=False;break
            if not active:continue
            valid.append(table_expression(parents,domains,table))
        if not valid:raise InvalidModel('No compatible local function for '+node['id'])
        options[node['id']]=valid
        coverage.append({'node':node['id'],'coverage':'exhaustive' if exhaustive else 'sampled','candidate_functions':len(valid),'tables_considered':len(tables),'full_table_space':combinations})
    identifiers=list(options)
    total=math.prod(len(options[k]) for k in identifiers)
    if total<=max_models:
        choices=list(itertools.product(*(range(len(options[k])) for k in identifiers)))
    else:
        choices=[tuple(0 for _ in identifiers)];seen=set(choices)
        while len(choices)<max_models:
            value=tuple(rng.randrange(len(options[k])) for k in identifiers)
            if value not in seen:choices.append(value);seen.add(value)
    models=[];signatures=set()
    for choice in choices:
        candidate=copy.deepcopy(model)
        for ident,index in zip(identifiers,choice):
            next(n for n in candidate['nodes'] if n['id']==ident)['expr']=options[ident][index]
        try: scm=SCM(candidate)
        except InvalidModel:continue
        signature=fingerprint([inspect_mechanism(scm,n)['signature'] for n in scm.order])
        if signature not in signatures:models.append(candidate);signatures.add(signature)
    exhaustive=total<=max_models and all(c['coverage']=='exhaustive' for c in coverage)
    return {'models':models,'summary':{'unknown_nodes':identifiers,'local_coverage':coverage,
        'cartesian_candidates':total,'retained_functionally_distinct':len(models),'coverage':'exhaustive within declared family' if exhaustive else 'bounded candidate coverage',
        'exhaustive':exhaustive,'max_models':max_models,'generation_frequency_is_probability':False,
        'assumptions':'Fixed graph, active declared parents, finite deterministic functions, explicit factual background and recorded row constraints. No claim of coverage over arbitrary omitted variables or confounding.'}}


def outcome_sets(models, queries):
    scms=[SCM(model) for model in models]
    return [{'id':q['id'],'values':sorted({s.solve(interventions=q['do'])[q['target']] for s in scms}),
             'abstain':False} for q in queries]
