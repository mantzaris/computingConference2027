"""Finite partial structural mechanisms, provenance and auditable consistency.

No story vocabulary, generated Python, or implicit completion of unknown rows.
"""
import copy
import hashlib
import itertools as it
import json
import math
import random
import re

import networkx as nx

from ..structural_programs import evaluate
from ..v2.mechanisms import table_expression


STATUSES = {'explicit', 'contextual', 'hypothetical', 'contradicted', 'unresolved'}
KINDS = {'narrative_fact', 'reported_claim', 'character_belief'}
OPS = {'split', 'distinguish', 'mediator', 'temporal_scope', 'retract',
       'alternative_structure', 'record_gap', 'clarify', 'no_change'}
GENERIC = {'and', 'or', 'if', 'influences', 'causes', 'affects', 'leads to', ''}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def informative(text):
    return (isinstance(text, str) and text.strip().lower() not in GENERIC
            and not re.match(r'^(influences|affects|causes|leads to)\b', text.strip(), re.I)
            and 2 <= len(text.split()) <= 12)


def locate(ref, passages):
    """A literal offset is navigation, never an entailment certificate."""
    p = passages[ref['passage_id']]
    quote = ref.get('quote', '')
    if not quote or not ref.get('supports'):
        raise ValueError('Evidence needs an exact quote and an explanation of support')
    starts = [m.start() for m in re.finditer(re.escape(quote), p['text'])]
    if not starts:
        raise ValueError('Quote does not occur in ' + ref['passage_id'])
    start = ref.get('start', starts[0])
    if start not in starts:
        raise ValueError('Incorrect evidence start offset')
    return dict(ref, start=start, end=start+len(quote), source_location={
        k: p.get(k) for k in ('url', 'source_id', 'episode', 'scene', 'first_line',
                              'last_line', 'start', 'end', 'dependence_cluster')},
        passage_sha256=hashlib.sha256(p['text'].encode()).hexdigest(),
        occurrence_count=len(starts), entailment='not certified by literal matching')


def _refs(items, passages):
    return [locate(r, passages) for r in items]


def validate_representation(record, packet):
    r = copy.deepcopy(record)
    ps = {p['id']: p for p in packet['segments']}
    vs = r.get('variables', [])
    ids = [v['id'] for v in vs]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError('Nonempty unique variable identifiers required')
    if r.get('outcome') not in ids:
        raise ValueError('Outcome must be an existing variable')
    for v in vs:
        for key in ('label', 'definition', 'actor', 'time_note', 'boundary_reason'):
            if not isinstance(v.get(key), str) or not v[key].strip():
                raise ValueError(v['id'] + ' needs ' + key)
        dom = v['domain']
        if (not isinstance(dom, list) or not 2 <= len(dom) <= 8
                or any(type(x) not in (str, int) for x in dom)
                or len({json.dumps(x) for x in dom}) != len(dom)):
            raise ValueError('Use 2–8 distinct finite integer/string states')
        if v.get('factual') is not None and v['factual'] not in dom:
            raise ValueError('Factual state outside domain')
        if v.get('kind') not in KINDS or v.get('event_status') not in STATUSES:
            raise ValueError('Invalid event kind/support')
        if v.get('boundary') not in ('fixed_context', 'endogenous', 'unresolved'):
            raise ValueError('Declare the upstream boundary, do not infer one from zero indegree')
        for key in ('event_time', 'statement_time'):
            if v.get(key) is not None and type(v[key]) not in (int, float):
                raise ValueError('Numeric common-unit time or null required')
        v['evidence'] = _refs(v.get('evidence', []), ps)
        if v['event_status'] in ('explicit', 'contextual') and not v['evidence']:
            raise ValueError('Supported event needs evidence')
        if v['boundary'] == 'fixed_context' and v.get('factual') is None:
            raise ValueError('Fixed context needs a stated value')
    nodes = {v['id']: v for v in vs}
    edgeids = []
    pairs = []
    for e in r.get('edges', []):
        edgeids.append(e['id']); pairs.append((e['parent'], e['child']))
        if e['parent'] not in nodes or e['child'] not in nodes or e['parent'] == e['child']:
            raise ValueError('Invalid edge endpoints')
        if not informative(e.get('label')) or len(e.get('process', '').split()) < 6:
            raise ValueError('Every edge needs an informative phrase and substantive process')
        for k in ('participants', 'conditions', 'qualifications', 'gaps', 'alternatives',
                  'structural_implications'):
            if not isinstance(e.get(k), list):
                raise ValueError('Edge needs array ' + k)
        if e.get('status') not in STATUSES:
            raise ValueError('Invalid directional status')
        for k in ('temporal_status', 'information_status'):
            if e.get(k) not in ('consistent', 'unresolved', 'contradicted'):
                raise ValueError('Edge needs temporal and information constraints')
        if not isinstance(e.get('endpoint_support'), dict) or not all(
                k in e['endpoint_support'] for k in ('parent', 'child')):
            raise ValueError('Separate endpoint assessments required')
        e['evidence'] = _refs(e.get('evidence', []), ps)
        e['contradictions'] = _refs(e.get('contradictions', []), ps)
        if e['status'] in ('explicit', 'contextual') and not e['evidence']:
            raise ValueError('Supported direction requires source evidence')
        a, b = nodes[e['parent']], nodes[e['child']]
        if a['event_time'] is not None and b['event_time'] is not None and a['event_time'] > b['event_time']:
            raise ValueError('Temporal counterexample: ' + e['parent'] + ' occurs after ' + e['child'])
    if len(set(edgeids)) != len(edgeids) or len(set(pairs)) != len(pairs):
        raise ValueError('Duplicate edge identifier/pair')
    g = nx.DiGraph(); g.add_nodes_from(ids); g.add_edges_from(pairs)
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError('Cyclic structure; preserve unresolved feedback outside this prototype')
    ms = r.get('mechanisms', [])
    if len({m['child'] for m in ms}) != len(ms):
        raise ValueError('One joint mechanism per child')
    for m in ms:
        if m['child'] not in nodes or set(m['parents']) != set(g.predecessors(m['child'])):
            raise ValueError('Mechanism parents must equal persistent edge endpoints')
        if not m.get('description') or (len(m['parents']) > 1 and not m.get('joint_description')):
            raise ValueError('Describe the mechanism, including multi-parent interaction')
        m['evidence'] = _refs(m.get('evidence', []), ps)
        if not isinstance(m.get('gaps'), list) or not isinstance(m.get('assumptions'), list):
            raise ValueError('Mechanisms need gaps and assumptions')
    expected = {v['id'] for v in vs if v['boundary'] != 'fixed_context'}
    if {m['child'] for m in ms} != expected:
        raise ValueError('Every endogenous/unresolved variable needs a partial mechanism; fixed contexts do not')
    if any(g.in_degree(v['id']) for v in vs if v['boundary'] == 'fixed_context'):
        raise ValueError('A fixed boundary cannot have operative parents')
    r['topological_order'] = list(nx.topological_sort(g))
    r['source_packet_sha256'] = packet['packet_sha256']
    return r


def revision_record(before, after, operations, retrieved, packet):
    if not isinstance(operations, list) or len(operations) > 6:
        raise ValueError('At most six bounded operations')
    ps = {p['id']: p for p in packet['segments']}
    for op in operations:
        if op.get('kind') not in OPS or not op.get('reason'):
            raise ValueError('Revision needs an allowed operation and evidence-based justification')
        op['evidence'] = _refs(op.get('evidence', []), ps)
        if op['kind'] not in ('record_gap', 'no_change') and not op['evidence']:
            raise ValueError('Substantive representation revision needs actual source evidence')
    if before['outcome'] != after['outcome']:
        raise ValueError('Outcome identifier/scope is fixed; preserve the target')
    old = next(v for v in before['variables'] if v['id'] == before['outcome'])
    new = next(v for v in after['variables'] if v['id'] == after['outcome'])
    if any(old[k] != new[k] for k in ('definition', 'domain', 'event_time')):
        raise ValueError('Representation revision cannot silently move outcome scope')
    return {'before_sha256': fingerprint(before), 'after_sha256': fingerprint(after),
            'operations': operations, 'retrieval': retrieved,
            'structural_change': fingerprint([(e['parent'], e['child']) for e in before['edges']]) !=
                                 fingerprint([(e['parent'], e['child']) for e in after['edges']]),
            'human_adjudication': 'pending'}


def contexts(mechanism, nodes):
    names = mechanism['parents'] + mechanism.get('background', [])
    if len(names) != len(set(names)) or any(n not in nodes for n in names):
        raise ValueError('Unknown or repeated declared input')
    return names, list(it.product(*(nodes[p]['domain'] for p in names)))


def validate_constraint(c, m, nodes, passages=None):
    names, rows = contexts(m, nodes)
    out = nodes[m['child']]['domain']
    if c.get('kind') not in ('row', 'necessary', 'changes', 'monotone', 'invariant'):
        raise ValueError('Unsupported formal predicate ' + str(c.get('kind')))
    if c.get('basis') not in ('evidence', 'assumption') or not c.get('rationale'):
        raise ValueError('Constraint needs separate evidence/assumption origin and rationale')
    when = c.get('when', {})
    if set(when)-set(names) or any(v not in nodes[p]['domain'] for p, v in when.items()):
        raise ValueError('Invalid input context')
    if c['kind'] == 'row':
        if not c.get('allowed') or set(c['allowed'])-set(out):
            raise ValueError('Row must allow a nonempty subset of output domain')
    elif c['kind'] == 'necessary':
        if not when or c.get('output') not in out:
            raise ValueError('Necessary condition needs input conjunction and child value')
    else:
        if c.get('parent') not in names or c['parent'] in when:
            raise ValueError('Invalid varying parent/context')
        if c.get('low') not in nodes[c['parent']]['domain'] or c.get('high') not in nodes[c['parent']]['domain'] or c['low'] == c['high']:
            raise ValueError('Specify distinct compared input values')
        if c['kind'] in ('changes', 'monotone') and c.get('sign') not in ('positive', 'negative', 'different'):
            raise ValueError('Explicit ordinal direction or different required')
        if c['kind'] == 'monotone' and c['sign'] == 'different':
            raise ValueError('Monotonicity requires an ordered positive/negative direction')
        if c.get('sign') in ('positive', 'negative') and any(type(x) is not int for x in out):
            raise ValueError('Signed comparisons require ordered integer outputs')
    if passages is not None:
        c['evidence'] = _refs(c.get('evidence', []), passages)
    if c['basis'] == 'evidence' and not c.get('evidence'):
        raise ValueError('Evidence constraint needs a provenance reference')
    return c


def predicate(c, names, rows, values):
    """Return satisfaction and a concrete violating/witness context."""
    maps = [dict(zip(names, row)) for row in rows]
    matches = lambda x: all(x[k] == v for k, v in c.get('when', {}).items())
    if c['kind'] == 'row':
        bad = [(x, y) for x, y in zip(maps, values) if matches(x) and y not in c['allowed']]
        return not bad, ({'inputs': bad[0][0], 'output': bad[0][1], 'allowed': c['allowed']} if bad else None)
    if c['kind'] == 'necessary':
        bad = [(x, y) for x, y in zip(maps, values) if y == c['output'] and not matches(x)]
        return not bad, ({'inputs': bad[0][0], 'output': bad[0][1]} if bad else None)
    lookup = dict(zip(rows, values)); p = c['parent']; j = names.index(p)
    pairs = []
    for row, x in zip(rows, maps):
        if x[p] != c['low'] or not matches(x):
            continue
        other = row[:j] + (c['high'],) + row[j+1:]
        a, b = lookup[row], lookup[other]
        pairs.append({'inputs': x, 'set_to': c['high'], 'before': a, 'after': b})
    def sign(w, strict):
        if c.get('sign') == 'positive':
            return w['after'] > w['before'] if strict else w['after'] >= w['before']
        if c.get('sign') == 'negative':
            return w['after'] < w['before'] if strict else w['after'] <= w['before']
        return w['after'] != w['before']
    if c['kind'] == 'changes':
        good = [w for w in pairs if sign(w, True)]
        return bool(good), (None if good else {'no_directional_witness': True, 'contexts': pairs[:8]})
    bad = [w for w in pairs if (w['before'] != w['after'] if c['kind'] == 'invariant' else not sign(w, False))]
    return not bad, (bad[0] if bad else None)


def local_family(m, nodes, max_tables=4096, sample_draws=4096, seed=3701):
    names, rows = contexts(m, nodes); dom = nodes[m['child']]['domain']
    if len(rows) > 64:
        return {'coverage': 'unavailable', 'reason': 'More than 64 finite input rows', 'tables': [], 'rows': [], 'inputs': names}
    options = [list(dom) for _ in rows]
    constraints = m.get('constraints', [])
    # Row constraints prune the product without changing the constraint family.
    for c in constraints:
        validate_constraint(c, m, nodes)
        if c['kind'] == 'row':
            for i, row in enumerate(rows):
                if all(dict(zip(names, row))[k] == v for k, v in c.get('when', {}).items()):
                    options[i] = [v for v in options[i] if v in c['allowed']]
    total = math.prod(map(len, options)); exact = total <= max_tables
    rng = random.Random(seed)
    trials = list(it.product(*options)) if exact else list(dict.fromkeys(
        tuple(rng.choice(o) for o in options) for _ in range(sample_draws)))
    accepted = [list(table) for table in trials if all(predicate(c, names, rows, table)[0] for c in constraints)]
    return {'inputs': names, 'rows': [list(x) for x in rows], 'tables': accepted,
            'coverage': 'exhaustive' if exact else 'sampled', 'row_pruned_space': total,
            'tables_examined': len(trials), 'compatible_count': len(accepted),
            'unknown_rows': ([i for i in range(len(rows)) if len({t[i] for t in accepted}) > 1]
                             if exact else [i for i, o in enumerate(options) if len(o) > 1]),
            'unconstrained_by_row_predicates': [i for i, o in enumerate(options) if len(o) > 1],
            'unknown_row_interpretation': 'Exact variation within compatible family' if exact else 'Rows not fixed by row predicates; sampled agreement cannot identify them',
            'empty_means': 'inconsistent declared constraints' if exact else 'no candidate found; not an impossibility proof'}


def build_family(rep, functional, packet=None, max_tables=4096, max_models=512, seed=3701):
    nodes = {v['id']: v for v in rep['variables']}
    ps = {p['id']: p for p in packet['segments']} if packet else None
    functions = copy.deepcopy(functional.get('functions', []))
    ids = [m['child'] for m in rep['mechanisms']]
    if sorted(f['child'] for f in functions) != sorted(ids):
        raise ValueError('Compile every partial mechanism exactly once')
    local = {}; reports = []; signatures = []
    for f in functions:
        m = next(m for m in rep['mechanisms'] if m['child'] == f['child'])
        f['parents'] = list(m['parents']); f.setdefault('background', [])
        for u in f['background']:
            if u not in nodes or nodes[u]['boundary'] != 'fixed_context':
                raise ValueError('Background must be an already justified fixed context variable')
        cids = [c['id'] for c in f.get('constraints', [])]
        if len(cids) != len(set(cids)):
            raise ValueError('Unique constraint identifiers required')
        for c in f.get('constraints', []):
            validate_constraint(c, f, nodes, ps)
        result = local_family(f, nodes, max_tables=max_tables, seed=seed)
        # Evidence does not imply a complete parent set. Explicit unmodeled gaps
        # can leave a useful explanation with no defensible executable scope.
        result['scope_status'] = f.get('scope_status', 'unavailable')
        if result['scope_status'] not in ('declared_family', 'unavailable'):
            raise ValueError('State whether an executable scope can be defended')
        if not f.get('scope_assumptions'):
            raise ValueError('Declare fixed graph/domain/background assumptions, or why unavailable')
        local[f['child']] = result
        signatures.append({'child': f['child'], 'signature': fingerprint(result)})
    executable = all(v['coverage'] != 'unavailable' and v['scope_status'] == 'declared_family' and v['tables'] for v in local.values())
    certified_empty = any(v['coverage'] == 'exhaustive' and not v['tables'] for v in local.values())
    if not executable:
        return {'functions': functions, 'local': local, 'models': [], 'exhaustive': False,
                'coverage': 'inconsistent' if certified_empty else 'unavailable', 'signatures': signatures,
                'reason': 'At least one local family is inconsistent, outside bounds, empty-sampled, or scope-unavailable'}
    keys = list(local); total = math.prod(len(local[k]['tables']) for k in keys)
    exact = total <= max_models and all(v['coverage'] == 'exhaustive' for v in local.values())
    if total <= max_models:
        combos = list(it.product(*(range(len(local[k]['tables'])) for k in keys)))
    else:
        rng = random.Random(seed); chosen = set()
        while len(chosen) < max_models:
            chosen.add(tuple(rng.randrange(len(local[k]['tables'])) for k in keys))
        combos = sorted(chosen)
    models = [{k: local[k]['tables'][i] for k, i in zip(keys, combo)} for combo in combos]
    result = {'functions': functions, 'local': local, 'models': models, 'exhaustive': exact,
            'coverage': 'exhaustive within declared family' if exact else 'sampled candidates',
            'cartesian_size_within_local_candidates': total, 'signatures': signatures,
            'frequency_is_probability': False}
    # The compiler must retain established observations, not just its chosen
    # subset of source constraints. Reject an underspecified family with a
    # concrete diagnostic; never silently invent an unobserved output row.
    established = {v['id']: v['factual'] for v in rep['variables']
                   if v.get('event_status') in ('explicit', 'contextual') and v.get('factual') is not None}
    for child, f in local.items():
        if child in established and all(p in established for p in f['inputs']):
            row = [established[p] for p in f['inputs']]
            index = f['rows'].index(row)
            bad = next((table[index] for table in f['tables'] if table[index] != established[child]), None)
            if bad is not None:
                raise ValueError('Known factual row not enforced for '+child+': inputs '+str(dict(zip(f['inputs'],row)))+
                                 ' permit '+str(bad)+' but recorded evidence establishes '+str(established[child])+
                                 '. Retain the observed constraint or revise the evidence assessment; do not complete unobserved rows.')
    for index, model in enumerate(models):
        world = solve(rep, result, model)
        for ident, expected in established.items():
            if world[ident] != expected:
                raise ValueError('Known factual-state conflict in joint candidate '+str(index)+': '+ident+
                                 ' computes '+str(world[ident])+' versus established '+str(expected)+
                                 '. This bounded compiler requires explicit compatible observational constraints.')
    return result


def solve(rep, family, model, interventions=None):
    interventions = interventions or {}; nodes = {v['id']: v for v in rep['variables']}
    if set(interventions)-set(nodes):
        raise ValueError('Unknown intervention target')
    if any(value not in nodes[k]['domain'] for k, value in interventions.items()):
        raise ValueError('Invalid intervention value')
    background_ids = {u for f in family['functions'] for u in f.get('background', [])}
    if set(interventions) & background_ids:
        raise ValueError('Declared background parameters stay fixed; represent an intervenable input as a parent variable instead')
    # Background contexts can appear later in a graph ordering because they
    # are not new causal arrows. Their factual values are available from start.
    state = {k: interventions.get(k, v['factual']) for k, v in nodes.items()
             if v['boundary'] == 'fixed_context'}
    for k in rep['topological_order']:
        v = nodes[k]
        if k in interventions:
            state[k] = interventions[k]
        elif v['boundary'] == 'fixed_context':
            state[k] = v['factual']
        else:
            f = family['local'][k]
            expr = table_expression(f['inputs'], [nodes[p]['domain'] for p in f['inputs']], model[k])
            state[k] = evaluate(expr, state, {})
    return state


def query(rep, family, intervention, target=None):
    if not family['models']:
        return {'status': 'unavailable', 'values': [], 'identified': False, 'factual_values': [], 'worlds': []}
    target = target or rep['outcome']; worlds = []
    for model in family['models']:
        factual = solve(rep, family, model); counter = solve(rep, family, model, intervention)
        worlds.append({'factual': factual, 'counterfactual': counter})
    vals = sorted({w['counterfactual'][target] for w in worlds}, key=repr)
    outer = next(v['domain'] for v in rep['variables'] if v['id'] == target)
    certificate = None
    if not family['exhaustive'] and target in intervention:
        certificate = 'The intervention directly replaces the target equation with this constant.'
        outer = [intervention[target]]
    elif not family['exhaustive'] and set(vals) == set(outer):
        certificate = 'Retained valid witnesses attain every declared target-domain value; no unseen function can add another value.'
    exact_outcomes = family['exhaustive'] or certificate is not None
    return {'status': 'exhaustive_set' if family['exhaustive'] else 'certified_set' if certificate else 'observed_sample',
            'values': vals, 'identified': exact_outcomes and len(vals) == 1,
            'bounds': {'inner': vals, 'outer': vals if exact_outcomes else sorted(outer,key=repr)},
            'certificate': certificate,
            'factual_values': sorted({w['factual'][target] for w in worlds}, key=repr),
            'worlds': worlds, 'intervention': intervention, 'target': target,
            'model_family_sha256': fingerprint(family['models'])}


def check_claims(rep, family, claims):
    nodes = {v['id']: v for v in rep['variables']}; reports = []
    for claim in claims:
        ident = claim.get('record_id'); child = claim.get('child')
        try:
            f = next(f for f in family['functions'] if f['child'] == child)
            c = dict(claim['predicate'], id=ident, basis='assumption', rationale='Reviewer translation of exact prose, NOT a family constraint', evidence=[])
            validate_constraint(c, f, nodes)
            local = family['local'][child]
            rows = [tuple(x) for x in local['rows']]
            bad = []
            for i, table in enumerate(local['tables']):
                ok, witness = predicate(c, local['inputs'], rows, table)
                if not ok:
                    bad.append({'candidate': i, 'counterexample': witness})
            reports.append({'record_id': ident, 'text': claim.get('text'), 'child': child,
                'status': 'contradicted_by_candidate' if bad else 'entailed_within_family' if local['coverage'] == 'exhaustive' and local['tables'] else 'unresolved',
                'counterexamples': bad[:3], 'violating_candidates': len(bad), 'examined': len(local['tables']),
                'coverage': local['coverage']})
        except (KeyError, ValueError, StopIteration) as error:
            reports.append({'record_id': ident, 'status': 'invalid_review_claim', 'error': str(error)})
    return reports


def display_gate(rep, family, audit):
    """Withhold known discrepancies; never manufacture substitute narrative prose."""
    expected = {e['id'] for e in rep['edges']} | {m['id'] for m in rep['mechanisms']}
    review = audit.get('records', [])
    if len(review) != len(expected) or {r.get('id') for r in review} != expected:
        return {'review_valid': False, 'displayed_edges': [], 'withheld': sorted(expected),
                'reason': 'Reviewer must assess actual mechanism/edge IDs exactly once', 'formal_claims': []}
    claims = audit.get('claims', [])
    prose = {e['id']: e['process'] for e in rep['edges']}
    prose.update({m['id']: m['description']+' '+m.get('joint_description', '') for m in rep['mechanisms']})
    if any(c.get('record_id') not in expected or not c.get('text') or c['text'] not in prose[c['record_id']] for c in claims):
        return {'review_valid': False, 'displayed_edges': [], 'withheld': sorted(expected),
                'reason': 'Formal reviewer assertion must quote actual mechanism prose', 'formal_claims': []}
    checks = check_claims(rep, family, claims)
    bad = {c['record_id'] for c in checks if c['status'] in ('contradicted_by_candidate', 'invalid_review_claim')}
    edge_ids = {e['id'] for e in rep['edges']}
    for r in review:
        if r.get('source_to_description') == 'contradicted' or r.get('description_to_function') != 'consistent':
            bad.add(r['id'])
        if r.get('formal_claims_complete') is not True:
            bad.add(r['id'])
        if r['id'] in edge_ids and r.get('label_specific') is not True:
            bad.add(r['id'])
    flagged = {v.get('id') for v in audit.get('variable_flags', [])}
    if flagged - {v['id'] for v in rep['variables']}:
        return {'review_valid': False, 'displayed_edges': [], 'withheld': sorted(expected),
                'reason': 'Reviewer flagged nonexistent variable IDs', 'formal_claims': checks}
    bad.update(e['id'] for e in rep['edges'] if e['parent'] in flagged or e['child'] in flagged)
    bad_children = {m['child'] for m in rep['mechanisms'] if m['id'] in bad}
    # Directional hypotheses may be displayed with an explicit unresolved tag,
    # but a known description/function contradiction is never drawn as accepted.
    displayed = [e['id'] for e in rep['edges'] if e['id'] not in bad and e['child'] not in bad_children and e['status'] != 'contradicted']
    by_id = {r['id']: r for r in review}
    child_review = {m['child']: by_id[m['id']] for m in rep['mechanisms']}
    statuses = {}
    for e in rep['edges']:
        status = e['status']
        if (by_id[e['id']].get('source_to_description') not in ('supported', 'inferred')
                or child_review[e['child']].get('source_to_description') not in ('supported', 'inferred')
                or e.get('temporal_status') != 'consistent' or e.get('information_status') != 'consistent'):
            status = 'unresolved'
        # Never upgrade original hypothetical/unresolved/contradicted support.
        statuses[e['id']] = status
    return {'review_valid': True, 'displayed_edges': displayed,
            'withheld': sorted(expected-set(displayed)-{m['id'] for m in rep['mechanisms'] if m['id'] not in bad}),
            'formal_claims': checks, 'display_status': statuses, 'semantic_review_is_independent': False}


def verify_reported_result(rep, family, intervention, reported, target=None):
    """Check the exact typed claims that accompany any prose/figure result."""
    actual = query(rep, family, intervention, target)
    fields = ('status', 'values', 'identified', 'factual_values', 'bounds', 'certificate')
    mismatches = [{'field': k, 'reported': reported.get(k), 'computed': actual.get(k)}
                  for k in fields if reported.get(k) != actual.get(k)]
    return {'passed': not mismatches, 'mismatches': mismatches,
            'family_sha256': fingerprint(family),
            'scope': 'Exact structured content only; free-text entailment is a separate semantic check.'}
