"""Bounded numerical refinement and explanations for the frozen application models.

This does not change variables, dependencies, expressions, or factual background.
The original records and their sampled allocations remain available for audit.
"""
import copy,hashlib,itertools,json,shutil
from got_war.budget import atomic_json
from got_war.generation import Generator
from got_war.structural_programs import SCM
from got_war.attribution import coalitions,disjoint_mechanism_groups,evidence_priority
from got_war.application_baselines import run as baselines
from got_war.explanation_audit import run as audit_explanations

gen=Generator('.')
for file in sorted((gen.run/'application').glob('*/alternative_*.json')):
    record=json.loads(file.read_text())
    if record.get('final_refinement_version')==1:continue
    archived=gen.run/'application_initial_attribution'/file.parent.name/file.name
    archived.parent.mkdir(parents=True,exist_ok=True)
    if not archived.exists():shutil.copy2(file,archived)
    scm=SCM(record['model']);paths=record['selection']['paths']
    exact=len(paths)<=8
    record['initial_attribution']=copy.deepcopy(record['attribution'])
    record['attribution']=coalitions(scm,paths,exact=exact)
    factual=scm.solve()
    for key,old in record['reference_sensitivity'].items():
        if not isinstance(old,dict) or 'references' not in old:continue
        refs={tuple(edge.split('>')):v for edge,v in old['references'].items()}
        record['reference_sensitivity'][key]=coalitions(scm,paths,references=refs,exact=exact)
    groups=disjoint_mechanism_groups(paths)
    record['disjoint_groups']={'groups':groups,'attribution':coalitions(scm,paths,groups=groups,exact=True)}
    # An unsupported/unassessed mechanism cannot acquire evidential support from
    # an inconsistent positive scalar. Keep the raw assessment for sensitivity.
    record['raw_edge_evidence']=copy.deepcopy(record['edge_evidence'])
    for edge in record['edge_evidence'].values():
        edge['raw_score']=edge.get('score',0)
        if edge.get('status','unassessed') in ('unsupported','unassessed'):
            edge['score']=0
            edge['normalization']='Unsupported or unassessed mechanism: effective evidence score zero. Raw score retained.'
    packet=json.loads((gen.root/'.private/packets'/(file.parent.name+'.json')).read_text())
    clusters={s['id']:s['cluster_id'] for s in packet['segments']}
    for key,uniform,method in [('evidence_priority',False,'minimum'),('uniform_priority',True,'minimum'),('geometric_priority',False,'geometric')]:
        record[key]=evidence_priority(paths,record['attribution'],record['edge_evidence'],clusters,uniform,method)
    record['raw_score_priority']=evidence_priority(paths,record['attribution'],record['raw_edge_evidence'],clusters)
    names=[n for n in scm.order if n!=scm.model['outcome']]
    interventions=[{n:scm.nodes[n]['reference']} for n in names[:12]]
    if len(interventions)<12:
        for pair in itertools.combinations(names,2):
            interventions.append({n:scm.nodes[n]['reference'] for n in pair})
            if len(interventions)>=12:break
    record['queries']=[]
    for i,intervention in enumerate(interventions):
        values=scm.solve(interventions=intervention)
        record['queries'].append({'id':'q%d'%i,'kind':'retrospective_counterfactual' if len(intervention)==1 else 'joint_counterfactual',
            'intervention':intervention,'factual_outcome':factual[scm.model['outcome']],'modeled_outcome':values[scm.model['outcome']],
            'changed_nodes':{k:{'before':factual[k],'after':v} for k,v in values.items() if v!=factual[k]},'gold_available':False})
    trace={'outcome_definition':scm.model['outcome_definition'],'attribution':record['attribution'],
        'variables':[{k:n.get(k) for k in ('id','label','definition','observed','reference','reference_meaning','expr','assumptions')} for n in scm.model['nodes']],
        'paths':record['evidence_priority']['paths'],'queries':record['queries'],
        'interpretation':'Fixed factual background; equations and reference states are assumptions, not identified historical causes. Evidence support is separate from structural influence.'}
    record['execution_trace']=trace
    prose_trace=dict(trace,queries=trace['queries'][:3])
    record['explanation_input_trace']=prose_trace
    record['initial_explanation']=record['explanation']
    prompt='Write at most 120 words in at most SIX sentences explaining this execution trace. Return {"text":"...","numeric_claims":[{"field":"baseline OR full","value":0}],"path_ids":["p1"]}. Use actual event names from the trace. Every causal statement must explicitly concern the frozen model. Distinguish evidence support from modeled influence. Mention that structural rules and reference inputs are assumptions, not identified historical causes or war probabilities. Discuss the strongest nonzero path and the reference-to-full contrast; if all contributions are zero, say so. Do not invent source evidence or universal necessity. Avoid explaining every query.\nTRACE: '+json.dumps(prose_trace)
    try:
        record['explanation']=gen.call('application_trace_explanation',prompt,1536,2027)
        record['explanation_checks']={'structured_numeric_claims':all(c.get('field') in ('baseline','full') and c.get('value')==record['attribution'][c['field']] for c in record['explanation'].get('numeric_claims',[])),
            'path_ids':set(record['explanation'].get('path_ids',[]))<={'p%d'%(i+1) for i in range(len(paths))},'free_text_semantic_verification':'pending same-model sentence audit; no human verification'}
    except Exception as error:
        record['explanation']={'text':'','error':str(error),'display_status':'VERIFICATION FAILURE: use the execution trace; generated explanation unavailable.'}
    record['final_refinement_version']=1
    record['refinement_policy']={'attribution':'Exact coalition enumeration for at most eight paths; original 64-permutation allocation retained.',
        'support':'Set unsupported/unassessed edge scores to zero; retain raw model scores and raw-score ranking sensitivity.',
        'queries':'Up to twelve canonical single-node, then lexicographically ordered paired reference interventions. Literary outcomes have no gold labels.'}
    atomic_json(file,record)
    print('REFINED',file.parent.name,file.stem,flush=True)
baselines('.')
audit_explanations('.')
