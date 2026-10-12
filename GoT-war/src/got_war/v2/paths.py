"""Coalition behavior, query contrasts and evidence weighting with separate rubrics."""
import collections
import copy
import itertools
import math
from ..structural_programs import SCM
from ..attribution import coalitions, select_paths, evidence_priority
from .mechanisms import inspect_mechanism


def edge_support(model):
    nodes={n['id']:n for n in model['nodes']};result={}
    for node in model['nodes']:
        influences={e['parent']:e for e in node.get('influences',[]) if isinstance(e,dict) and 'parent' in e}
        for parent in node['parents']:
            record=copy.deepcopy(influences.get(parent,{}))
            directional=record.get('direction_status','unassessed')
            score={'explicit':1.,'contextually_supported':.5}.get(directional,0.)
            endpoints=all(nodes[x].get('event_status') in ('established','reported_claim','character_belief') for x in (parent,node['id']))
            if not endpoints or not record.get('segments') or record.get('contradictions') or record.get('temporal_status','consistent')!='consistent' or record.get('information_status','consistent')!='consistent':score=0.
            record.update(parent=parent,child=node['id'],score=score,status=directional,
                parent_event_status=nodes[parent].get('event_status','unassessed'),child_event_status=node.get('event_status','unassessed'),
                function_identification=node.get('function_identification','unidentified'),
                rubric='Directional support only: explicit=1, contextually supported=.5, otherwise 0; unsupported endpoints, absent references, contradictions or unresolved temporal/information constraints force 0. Exact-function identification is separate.')
            result[parent+'>'+node['id']]=record
    return result


def game_report(scm, paths, references=None):
    if len(paths)>10:raise ValueError('Exact game diagnostic limited to ten paths')
    attr=coalitions(scm,paths,references=references,exact=True)
    edge_sets=[set(zip(p,p[1:])) for p in paths];focus=set().union(*edge_sets) if edge_sets else set()
    values=[]
    for mask in range(1<<len(paths)):
        active=set().union(*(e for i,e in enumerate(edge_sets) if mask>>i&1))
        values.append(scm.solve(inactive_edges=focus-active,references=references)[scm.model['outcome']])
    marginal=[];interaction=[];minimal_full=[]
    for mask,value in enumerate(values):
        if value==values[-1] and value!=values[0] and all(values[mask^(1<<i)]!=value for i in range(len(paths)) if mask>>i&1):
            minimal_full.append([i+1 for i in range(len(paths)) if mask>>i&1])
        for i in range(len(paths)):
            if not mask>>i&1:
                marginal.append(values[mask|1<<i]-value)
                for j in range(i+1,len(paths)):
                    if not mask>>j&1:
                        interaction.append(values[mask|1<<i|1<<j]-values[mask|1<<i]-values[mask|1<<j]+value)
    largest=max(map(abs,attr['phi']),default=0)
    attr.update(coalition_values=values,coalition_histogram=dict(collections.Counter(map(str,values))),
        all_paths_required=bool(paths) and values[-1]!=values[0] and all(v==values[0] for v in values[:-1]),
        minimal_full_outcome_coalitions=minimal_full,substitute_path_sets=len(minimal_full)>1,
        negative_marginals=sum(x<0 for x in marginal),positive_marginals=sum(x>0 for x in marginal),
        pair_interaction_range=[min(interaction,default=0),max(interaction,default=0)],
        largest_absolute_ties=['p%d'%(i+1) for i,x in enumerate(attr['phi']) if largest and abs(abs(x)-largest)<1e-12])
    return attr


def query_model(model, query):
    """The do-operator changes targeted equations only; background is preserved."""
    original=SCM(model);factual=original.solve();counter=original.solve(interventions=query['do'])
    changed=copy.deepcopy(model)
    for node in changed['nodes']:
        node['reference']=factual[node['id']];node['observed']=counter[node['id']]
        if node['id'] in query['do']:
            node.update(parents=[],noise=[],expr={'const':query['do'][node['id']]})
    return SCM(changed),factual,counter


def explain_query(model, query, alternatives=None):
    changed,factual,counter=query_model(model,query)
    selection=select_paths(changed,maximum=8,sources=sorted(query['do']))
    attr=game_report(changed,selection['paths'])
    edges=edge_support(model)
    priorities=evidence_priority(selection['paths'],attr,edges)
    uniform=evidence_priority(selection['paths'],attr,edges,uniform=True)
    possible=sorted({SCM(m).solve(interventions=query['do'])[query['target']] for m in (alternatives or [model])})
    ranking_available=any(x['priority']>0 for x in priorities['segments'])
    relevant=set(n for p in selection['paths'] for n in p)
    mechanisms=[]
    original=SCM(model)
    for ident in original.order:
        if ident in relevant:
            report=inspect_mechanism(original,ident)
            mechanisms.append({k:report[k] for k in ('node','equation','coverage','necessary_for_one','sufficient_for_one','derived_description')})
    return {'query':{k:query[k] for k in ('id','do','target')},'outcome_label':changed.nodes[query['target']]['label'],
        'factual_states':factual,'counterfactual_states':counter,'possible_outcomes':possible,
        'changed_nodes':[n for n in factual if factual[n]!=counter[n]],'paths':selection,
        'attribution':attr,'evidence_priority':priorities,'uniform_priority':uniform,'ranking_available':ranking_available,
        'ranking_status':'available' if ranking_available else 'unavailable: all evidence-weighted priorities are zero',
        'weak_evidence_paths':[p for p in priorities['paths'] if abs(p['signed_contribution'])>1e-12 and p['evidence_support']<.5],
        'mechanisms':mechanisms,'assumptions':model.get('assumptions',[])+[a for n in model['nodes'] for a in n.get('assumptions',[])],
        'interpretation':'The do intervention freezes all other mechanisms and factual background. The selected-edge coalition allocation is relative to explicit factual edge references; it need not equal the entire intervention contrast if paths are omitted. It is not a probability, an individual event effect or a natural path-specific effect.'}
