"""LLM mechanism construction/revision with separate source and function checks."""
import copy
import json
from pathlib import Path
import time

from ..budget import atomic_json
from ..retrieval import retrieve
from ..structural_programs import SCM, domain
from ..v2.application import Construction
from ..v2.mechanisms import inspect_mechanism
from .core import (build_family, display_gate, fingerprint, query, revision_record,
                   validate_representation)


REPRESENTATION = '''Return a JSON object with outcome (one variable ID), variables, edges, mechanisms, and gaps.
Discover the concepts; do not copy a prewritten graph or fill gaps from memory. Use at most 7 variables and 8 edges for this small development packet, fewer or no edges when evidence warrants. No connectivity minimum. Keep the designated outcome meaning and time exactly fixed.
Each variable: {id,label,definition,actor,domain:[0,1] or distinct category strings,factual:value or null,kind:narrative_fact|reported_claim|character_belief,event_time:number or null,statement_time:number or null,time_note,event_status:explicit|contextual|hypothetical|contradicted|unresolved,boundary:fixed_context|endogenous|unresolved,boundary_reason,evidence:[REF]}. The outcome variable's definition must copy the supplied OUTCOME literally and use domain [0,1]; its factual value can remain null. When an endpoint episode code is supplied, use it as the outcome event_time.
Use episode codes 101..110 for TV, minute/time indices for other narratives, null if unresolved. Explain units. A fixed_context is explicitly outside the causal scope, never a fabricated residual. Missing upstream mechanisms may instead have boundary=unresolved and a partial mechanism with no parents. Distinguish permission/action/outcome and actual events/reports/beliefs. Do not make a later consequence cause earlier onset.
REF is {passage_id,quote:short EXACT contiguous source text,supports:what this passage establishes and what inferential bridge remains}. Empty evidence is valid for a hypothesis; never fabricate quotes.
Each edge: {id,parent,child,label:specific 2-12 word causal phrase,process:substantive causal explanation,participants:[actors/resources/information/institutions],conditions:[],qualifications:[],evidence:[REF],contradictions:[REF],gaps:[],status:explicit|contextual|hypothetical|contradicted|unresolved,endpoint_support:{parent:judgment,child:judgment},temporal_status:consistent|unresolved|contradicted,information_status:consistent|unresolved|contradicted,structural_implications:[proposed constraint in words],alternatives:[only warranted alternatives]}.
Describe how the influence operates. No empty/operator-only/generic influence labels. No boilerplate to fill quotas. Chronology is not direction. Multiple passages may jointly support a mechanism, with the bridge explicit. An event's evidence does not automatically support its causal role or exact function.
Each non-fixed variable, including unresolved zero-parent variables, needs a mechanism: {id,child,parents:[exact incoming edge parents],description:substantive process,joint_description:interaction among all parents (required with multiple parents),evidence:[REF],assumptions:[],gaps:[]}. Joint explanations must distinguish substitution, joint enabling, inhibition or context dependence only where justified. Unknown interaction is valid. Do NOT generate complete equations or fill missing truth-table rows at this stage.'''

FUNCTIONS = '''Compile the existing generated mechanism propositions into partial functional constraints, without inventing missing rows.
Return {functions:[{child,background:[],scope_status:declared_family|unavailable,scope_assumptions:[explicit fixed graph/domain/determinism/background assumptions or reason unavailable],constraints:[CONSTRAINT]}]}.
All endogenous and unresolved children need an entry. Their parents are fixed by the representation. A justified additional fixed context variable may be listed as background; it then remains fixed across interventions and cannot itself be a do-target. Represent an intervenable influence as a parent instead. Never invent an unmodeled residual to fit facts. Missing mechanism rows are represented by ABSENCE of a constraint. If no defensible executable scope exists use unavailable and preserve partial information.
Each constraint: {id,kind,basis:evidence|assumption,rationale,evidence:[REF],...formal fields}. Evidence and assumptions must stay separate. A factual local row needs an explicit source-backed constraint, not unobserved completions. Evidence for occurrence is not identification of a law. Label universal generalization from one episode as assumption. No requirement that every parent be active in every compatible function.
Formal predicates:
- row: {when:{input:value,...},allowed:[child values]}. ALL configurations matching when must output an allowed value; missing inputs are universally quantified. Full input rows are safer when only an observation is known.
- necessary: {when:{input:value,...},output:child_value}: whenever child equals output, every when condition holds. It is NOT sufficiency.
- changes: {parent,low:value,high:value,when:{other inputs},sign:positive|negative|different}: there EXISTS a context matching when where changing low to high strictly changes output in this direction. It does NOT imply monotonicity, necessity or sufficiency.
- monotone: same fields; ALL compared configurations in context have nondecreasing/nonincreasing output. Use only if justified, integer outputs only for signed claims.
- invariant: {parent,low,high,when}: output unchanged for ALL matching configurations.
REF={passage_id,quote:source-exact,supports}. Do not turn 'helps' into a complete AND or OR. Unknown rows and alternatives must survive. Deterministic software enumerates compatible finite functions and executes interventions without regenerating functions.'''

AUDIT = '''Review actual edge and joint-mechanism records against supplied passages and finite behavior. Same-model review is fallible. Do not review instructions as prose.
Return {records:[{id:actual edge/mechanism ID,source_to_description:supported|inferred|unresolved|contradicted,description_to_function:consistent|unresolved|contradicted,label_specific:true|false,formal_claims_complete:true|false,reason,questions:[]}],claims:[{record_id,child,text:EXACT substring from that record's process or description/joint_description,predicate:FORMAL}],variable_flags:[{id,issue}],queries:[]}.
For each edge label, label_specific requires a substantive process phrase, not generic influence, vague causation or repetitive boilerplate. Use false for a label that misdescribes the proposed process. Flag actual variable IDs whose meanings or times remain inadequate; affected edges will be withheld rather than silently reinterpreted.
Assess EVERY edge and mechanism exactly once, including ones with unresolved source support. source_to_description and description_to_function are separate. Claims about actual supported links do not identify exact functions. Label unsupported necessity/sufficiency or chronology-based links. A finite family can agree with a carefully qualified partial description while differing on unknown rows. A categorical statement contradicted by ANY retained candidate is not consistent across that family. No silent replacement by generic prose.
Translate every CHECKABLE functional assertion in the actual prose into a formal predicate independently of the compiled constraints. Do not add these claims to the family. Formal predicates use kind row (when,allowed), necessary (when,output), changes (parent,low,high,when,sign), monotone (same fields), invariant (parent,low,high,when). The semantics are those in the compiler contract. A universal claim with unspecified context has when={}. If the prose has no definite functional assertion, claims may be empty; mark formal_claims_complete true only if no checkable assertion is omitted. Unknown/unavailable function behavior must remain unresolved if consistency cannot be assessed. Check event/report distinction, timing, missing steps and full context, not just quote match.'''


def source_text(packet, chars=14000):
    # Identical complete packet for paired arms, never a hidden additional source.
    s = '\n\n'.join('['+p['id']+'] '+p.get('episode', '')+'\n'+p['text'] for p in packet['segments'])
    if len(s) > chars:
        raise ValueError('Frozen packet exceeds prompt source budget')
    return s


def compact_rep(rep):
    """Drop deterministic offset duplication only, never substantive prose."""
    def clean(x):
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items() if k not in ('source_location', 'passage_sha256', 'occurrence_count', 'entailment', 'topological_order', 'source_packet_sha256')}
        if isinstance(x, list):
            return [clean(v) for v in x]
        return x
    return clean(rep)


def behavior_view(family):
    return {k: {**{key: value for key, value in f.items() if key != 'tables'}, **{
        'distinct_outputs_by_row': [sorted({t[i] for t in f['tables']}, key=repr) for i in range(len(f['rows']))],
        'example_tables': f['tables'][:4],
        'note': 'Row-wise sets lose cross-row correlations; exact tables retained for deterministic checks.'}}
        for k, f in family['local'].items()}


class MechanismFirst:
    def __init__(self, gen, case, packet, folder):
        self.gen, self.case, self.packet, self.folder = gen, case, packet, Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.revisions = []

    def validate(self, response):
        rep = validate_representation(response, self.packet)
        v = next(v for v in rep['variables'] if v['id'] == rep['outcome'])
        if v['definition'] != self.case['outcome'] or v['domain'] != [0,1]:
            raise ValueError('Keep the literal specified outcome definition and Boolean domain')
        if self.case.get('endpoint_code') is not None and v['event_time'] != self.case['endpoint_code']:
            raise ValueError('Keep the specified outcome endpoint episode')
        return rep

    def call(self, stage, prompt, limit, validator=lambda x: x):
        response = None
        start = time.monotonic()
        try:
            response = self.gen.call(stage, prompt, limit, seed=3701)
            result = validator(response)
            atomic_json(self.folder/(stage+'.json'), {'response': response, 'accepted': result, 'elapsed': time.monotonic()-start})
            return result
        except Exception as e:
            atomic_json(self.folder/(stage+'_failed.json'), {'response': response, 'error': type(e).__name__+': '+str(e), 'elapsed': time.monotonic()-start})
            raise

    def audit(self, rep, family, stage='audit'):
        # The function engine, not the reviewer, determines exact counterexamples.
        prompt = AUDIT+'\nOUTCOME: '+self.case['outcome']+'\nRECORDS:\n'+json.dumps(compact_rep(rep), ensure_ascii=False)+'\nBEHAVIOR:\n'+json.dumps(behavior_view(family))+'\nPASSAGES:\n'+source_text(self.packet)
        audit = self.call(stage, prompt, 2300)
        return audit, display_gate(rep, family, audit)

    def run(self):
        prefix = '\nOUTCOME: '+self.case['outcome']+'\nENDPOINT EPISODE CODE: '+str(self.case.get('endpoint_code','not applicable'))+'\nPASSAGES:\n'+source_text(self.packet)
        rep = self.call('propositions', REPRESENTATION+prefix, 4400,
                        self.validate)
        diagnosis = self.call('diagnosis',
            'Diagnose this generated explanation BEFORE any complete equations. Inspect supplied context for conflated variables, missing intermediate steps, permission/action/report distinctions, chronology errors, unsupported links and unresolved joint mechanisms. Return {issues:[{record_id,problem,operation:split|distinguish|mediator|temporal_scope|retract|alternative_structure|record_gap|clarify,question}],retrieval_questions:[specific question strings],revision_needed:true|false}. Do not prescribe a desired graph or force connectivity. Do not invent missing links.\nREPRESENTATION:\n'+json.dumps(compact_rep(rep))+prefix, 1400)
        retrieved = []
        for question in diagnosis.get('retrieval_questions', [])[:3]:
            found = retrieve(self.packet['segments'], question, max_chars=6000)
            retrieved.append({'question': question, 'passage_ids': [p['id'] for p in found],
                              'scores': [p['retrieval_score'] for p in found], 'method': 'BM25 within same available packet'})
        atomic_json(self.folder/'retrieval.json', retrieved)
        if diagnosis.get('revision_needed') is True:
            result = self.call('representation_revision',
                'Make ONE bounded evidence-driven representation revision. Return {representation:FULL revised representation,operations:[{kind,reason,evidence:[REF]}]}. Keep the exact outcome identifier, definition, domain and event_time. Retain unchanged meanings. Every split/mediator/retraction needs source evidence; record_gap/no_change may cite none. Preserve rejected hypotheses in gaps. Do not supply functions yet.\n'+REPRESENTATION+'\nPRIOR:\n'+json.dumps(compact_rep(rep))+'\nDIAGNOSIS:\n'+json.dumps(diagnosis)+'\nTARGETED RETRIEVAL:\n'+json.dumps(retrieved)+prefix, 4600)
            revised = self.validate(result['representation'])
            self.revisions.append(revision_record(rep, revised, result['operations'], retrieved, self.packet))
            rep = revised
        atomic_json(self.folder/'representation.json', rep)
        functional = self.call('functions', FUNCTIONS+'\nREPRESENTATION:\n'+json.dumps(compact_rep(rep))+prefix,
                               4000)
        family = build_family(rep, functional, self.packet)
        atomic_json(self.folder/'family_initial.json', family)
        audit, gate = self.audit(rep, family)
        atomic_json(self.folder/'gate_initial.json', gate)
        if (not gate['review_valid'] or gate['withheld'] or family['coverage'] == 'inconsistent'):
            # A single substantive repair, with concrete counterexamples and no gold.
            fixed = self.call('consistency_repair',
                'One final targeted consistency repair. Return {representation:FULL representation,functions:[full partial function records],operations:[{kind,reason,evidence:[REF]}]}. Preserve the outcome, all original records in the archive, and supported uncertainty. Repair the concrete discrepancies below through source-justified clarification/retraction or explicit assumptions; do not change evidence status to make a graph pass. Do not replace substantive processes with generic table prose. A still-unresolved interpretation should remain unresolved and will be withheld.\n'+REPRESENTATION+'\n'+FUNCTIONS+'\nCURRENT:\n'+json.dumps(compact_rep(rep))+'\nFUNCTIONS:\n'+json.dumps(functional)+'\nREVIEW:\n'+json.dumps(audit)+'\nCOUNTEREXAMPLES/GATE:\n'+json.dumps(gate)+prefix, 5000)
            revised = self.validate(fixed['representation'])
            self.revisions.append(revision_record(rep, revised, fixed.get('operations', []), [], self.packet))
            rep = revised; functional = {'functions': fixed['functions']}
            family = build_family(rep, functional, self.packet)
            audit, gate = self.audit(rep, family, 'audit_after_repair')
        result = {'arm': 'C', 'case': self.case['id'], 'status': 'partial' if not family['models'] else 'executable',
                  'representation': rep, 'family': family, 'audit': audit, 'display_gate': gate,
                  'revisions': self.revisions, 'packet_sha256': self.packet['packet_sha256']}
        atomic_json(self.folder/'final.json', result)
        return result


class V2Adapter(Construction):
    """Only storage, packet and generator isolation; inherited construction unchanged."""
    def __init__(self, root, gen, case, packet, folder):
        self.root = Path(root); self.run = Path(folder).parent
        self.results = self.root/'results/v3'; self.gen = gen
        self.packet = packet; self.segments = {s['id']: s for s in packet['segments']}
        self.case = dict(case, endpoint_code=case.get('endpoint_code', 9999), name=case['id'])
        self.folder = Path(folder); self.folder.mkdir(parents=True, exist_ok=True)
        self.semantic_compile_fallback = False


def from_v2(model):
    """Lossless finite functional adapter; no new mechanism prose or story rule."""
    scm = SCM(model); vs = []; ms = []; fs = []; local = {}; choices = {}
    for n in model['nodes']:
        vs.append({'id': n['id'], 'label': n['label'], 'definition': n['definition'], 'domain': domain(n),
                   'actor': n.get('actor'), 'event_time': n.get('time'), 'statement_time': None,
                   'time_note': n.get('event_time'), 'kind': n.get('proposition_kind'), 'factual': n['observed'],
                   'boundary': 'endogenous' if n['parents'] else 'fixed_context',
                   'boundary_reason': 'Preserved v2 scope, not reinterpreted', 'evidence': [],
                   'event_status': 'unresolved'})
        if n['parents']:
            report = inspect_mechanism(scm, n['id']); names = list(report['rows'][0]['inputs'])
            if n.get('noise'):
                raise ValueError('V3 paired display adapter cannot flatten nonroot v2 background')
            rows = [[r['inputs'][p] for p in names] for r in report['rows']]
            table = [r['output'] for r in report['rows']]
            local[n['id']] = {'inputs': names, 'rows': rows, 'tables': [table], 'coverage': report['coverage'], 'unknown_rows': []}
            choices[n['id']] = table
            ms.append({'id': 'M_'+n['id'], 'child': n['id'], 'parents': n['parents'],
                       'description': n.get('generated_description', ''), 'joint_description': '',
                       'assumptions': n.get('assumptions', []), 'gaps': [], 'evidence': []})
            fs.append({'child': n['id'], 'parents': n['parents'], 'constraints': [], 'background': []})
    rep = {'outcome': model['outcome'], 'variables': vs, 'edges': [], 'mechanisms': ms, 'topological_order': scm.order}
    fam = {'models': [choices], 'local': local, 'functions': fs, 'exhaustive': False,
           'coverage': 'single v2 hypothesis; not identification from evidence'}
    return rep, fam


def v2_family(records):
    """Preserve all actually retained v2 hypotheses, without asserting coverage."""
    rep, family = from_v2(records[0]['model'])
    for record in records[1:]:
        other, alternate = from_v2(record['model'])
        if [(m['child'], m['parents']) for m in other['mechanisms']] != [(m['child'], m['parents']) for m in rep['mechanisms']]:
            raise ValueError('V2 alternatives have unaligned meanings/parents')
        family['models'].extend(alternate['models'])
        for child, local in alternate['local'].items():
            for table in local['tables']:
                if table not in family['local'][child]['tables']:
                    family['local'][child]['tables'].append(table)
    family['coverage'] = 'retained v2 hypotheses; no exhaustive coverage claim'
    return rep, family


def presentation(gen, case, packet, a, folder):
    model = a['records'][0]['model']; before = fingerprint(model)
    rep, fam = v2_family(a['records'])
    edge_pairs = [(p, n['id']) for n in model['nodes'] for p in n['parents']]
    source = source_text(packet)
    prompt = ('Presentation-only arm. Keep the supplied variables, domains, parents, background and functions EXACTLY unchanged. '
        'Generate specific edge labels/process explanations and joint-mechanism descriptions describing the actual function, with assumptions visible. '
        'If a function is unsupported or contradicts its generated story description, report this; do not rescue it by changing the function or overstating evidence. '
        'Return {edges:[edge objects as below],mechanisms:[{id,child,parents,description,joint_description,evidence,assumptions,gaps}]}. No variables or functions in the output. '
        'Use edge IDs E1,E2,... in supplied pair order and mechanism IDs M_childID. No equations or reinterpretations may change.\n'+REPRESENTATION+
        '\nEXACT EDGE PAIRS:\n'+json.dumps(edge_pairs)+'\nFIXED MODEL:\n'+json.dumps(compact_rep(rep))+
        '\nBEHAVIOR:\n'+json.dumps(behavior_view(fam))+'\nPASSAGES:\n'+source)
    response = gen.call('presentation', prompt, 2100, seed=3701)
    atomic_json(Path(folder)/'presentation.json', response)
    if [(e['parent'], e['child']) for e in response.get('edges', [])] != edge_pairs:
        raise ValueError('Presentation changed underlying edge structure')
    if sorted(m['child'] for m in response.get('mechanisms', [])) != sorted(m['child'] for m in rep['mechanisms']):
        raise ValueError('Presentation changed mechanism identities')
    prior = {m['child']: m for m in rep['mechanisms']}
    if any(m['id'] != prior[m['child']]['id'] or m['parents'] != prior[m['child']]['parents'] for m in response['mechanisms']):
        raise ValueError('Presentation changed declared parents or mechanism record IDs')
    rep['edges'] = response['edges']; rep['mechanisms'] = response['mechanisms']
    # Validate all generated citations/labels without pretending the old variables
    # were generated in the new schema or giving them new event support scores.
    from .core import locate, informative
    ps = {p['id']: p for p in packet['segments']}
    from .core import STATUSES
    for e in rep['edges']:
        if not informative(e.get('label')) or not e.get('process') or e.get('status') not in STATUSES:
            raise ValueError('Uninformative display phrase')
        e['evidence'] = [locate(r, ps) for r in e.get('evidence', [])]
        e['contradictions'] = [locate(r, ps) for r in e.get('contradictions', [])]
    for m in rep['mechanisms']:
        m['evidence'] = [locate(r, ps) for r in m.get('evidence', [])]
        if len(m['parents']) > 1 and not m.get('joint_description'):
            raise ValueError('Missing joint-mechanism description')
    audit = gen.call('presentation_audit', AUDIT+'\nRECORDS:\n'+json.dumps(compact_rep(rep))+'\nBEHAVIOR:\n'+json.dumps(behavior_view(fam))+'\nPASSAGES:\n'+source, 900, seed=3701)
    gate = display_gate(rep, fam, audit)
    assert before == fingerprint(a['records'][0]['model'])
    result = {'arm': 'B', 'case': case['id'], 'status': 'executable', 'representation': rep,
              'family': fam, 'audit': audit, 'display_gate': gate, 'revisions': [],
              'base_model_sha256': before, 'after_model_sha256': fingerprint(model),
              'packet_sha256': packet['packet_sha256']}
    atomic_json(Path(folder)/'final.json', result)
    return result


def align_queries(gen, case, representation, folder):
    # Only natural-language intervention requests, never gold keys or answers.
    questions = [{'id': q['id'], 'question': q['question']} for q in case['queries']]
    answer = gen.call('align_queries',
        'Translate each intervention request onto the supplied operational variables. Return {queries:[{id,do:{variable_id:value},target:outcome_id,abstain:true|false,reason}]}. '
        'Do not answer the query or invent missing variables. If an input meaning is absent/conflated, abstain. Use exact domain values. No further modeling or function changes.\nVARIABLES:\n'+
        json.dumps(representation['variables'])+'\nOUTCOME_ID: '+representation['outcome']+'\nQUESTIONS:\n'+json.dumps(questions), 850, seed=3701)
    if sorted(q.get('id') for q in answer.get('queries', [])) != sorted(q['id'] for q in questions):
        raise ValueError('Query alignment requires each supplied ID once')
    atomic_json(Path(folder)/'query_alignment.json', answer)
    return answer
