"""Non-destructive interface recovery and partial-encoding audit.

This is an audit adapter, not a new construction method or semantic repair.
It never translates prose into functions, resolves an ambiguous endpoint,
changes a factual value, or treats a linguistic hint as a quantified claim.
"""
import copy
import itertools as it
import json
from pathlib import Path

import networkx as nx

from .simple_stories import (FOLDER, compile_model, frozen, load_records, packet,
                            proposition, schema_diagnostics)
from .v3.core import build_family, fingerprint, query
from .v4.application import expression, value


def normalize_interface(original):
    """Relocate only uniquely attributable records; retain an operation ledger.

    Explicit mechanisms take precedence over conflicting root metadata in the
    *derived view*. That convention is logged separately from lossless moves;
    it is not a claim that contradictory metadata was already consistent.
    Exact prose anchors locate records, never establish semantic correctness.
    """
    draft = copy.deepcopy(original)
    mechanisms = draft.get('mechanisms', [])
    children = [m['child'] for m in mechanisms]
    if len(children) != len(set(children)):
        raise ValueError('Multiple mechanisms for one child need interpretation')
    nodes = {v['id']: v for v in draft.get('variables', [])}
    operations, unresolved = [], []
    for m in mechanisms:
        if m['child'] in nodes and nodes[m['child']].get('boundary') == 'fixed_context':
            nodes[m['child']]['boundary'] = 'endogenous'
            operations.append({'kind': 'representation_precedence', 'child': m['child'],
                'from': 'fixed_context', 'to': 'endogenous',
                'reason': 'Use the explicitly supplied mechanism in this derived view; retain the original contradiction in this ledger.'})
        for field in ('edges', 'claims'):
            m.setdefault(field, [])
    for field in ('edges', 'claims'):
        remaining = []
        for index, item in enumerate(draft.get(field, [])):
            if field == 'edges':
                candidates = [m for m in mechanisms if item.get('parent') in m['parents']
                              and ('child' not in item or item['child'] == m['child'])]
                criterion = 'Unique declared mechanism containing this parent'
            else:
                candidates = [m for m in mechanisms if item.get('text') and
                              item['text'] in m['description'] and
                              ('child' not in item or item['child'] == m['child'])]
                criterion = 'Unique exact prose anchor (provenance, not semantic scoring)'
            if len(candidates) == 1:
                candidates[0][field].append(copy.deepcopy(item))
                operations.append({'kind': 'lossless_relocation', 'field': field,
                    'index': index, 'child': candidates[0]['child'], 'criterion': criterion})
            else:
                remaining.append(item)
                unresolved.append({'field': field, 'index': index,
                    'candidate_children': [m['child'] for m in candidates],
                    'reason': 'No unique attachment; no interpretation or endpoint was invented.'})
        if remaining:
            draft[field] = remaining
        else:
            draft.pop(field, None)
    return draft, {'input_sha256': fingerprint(original), 'normalized_sha256': fingerprint(draft),
                   'operations': operations, 'unresolved_attachments': unresolved}


def partial_projection(draft, story, version, max_models=4096):
    """Execute only the already encoded rows/expressions and observed states.

    The projection bypasses presentation requirements, NOT factual consistency
    or missing equations. Its declared graph is a scope assumption, not a
    source-validity finding. Generated formal-claim tags and prose supply no
    extra constraints. A bad recorded fact stays bad and must be flagged by
    the separate source audit.
    """
    d = copy.deepcopy(draft)
    ids = [v['id'] for v in d['variables']]
    if len(ids) != len(set(ids)) or d['outcome'] not in ids:
        raise ValueError('Duplicate variable identifiers or nonexistent outcome; interpretation required')
    children = [m['child'] for m in d['mechanisms']]
    if len(children) != len(set(children)) or set(children)-set(ids):
        raise ValueError('Duplicate or undeclared mechanism child')
    pack = packet(story, version)
    ps = {s['id']: s for s in pack['segments']}

    def refs(source, reason):
        if any(s not in ps for s in source):
            raise ValueError('Unknown sentence reference')
        return [{'passage_id': s, 'quote': ps[s]['text'], 'supports': reason} for s in source]

    nodes, graph = {}, nx.DiGraph()
    graph.add_nodes_from(ids)
    for v in d['variables']:
        boundary = 'endogenous' if v['id'] in children else v['boundary']
        if boundary == 'endogenous' and v['id'] not in children:
            raise ValueError('Missing mechanism for '+v['id'])
        if boundary == 'fixed_context' and v['factual'] not in (0, 1):
            raise ValueError('Unknown root state for '+v['id']+'; no root distribution or function invented')
        nodes[v['id']] = dict(id=v['id'], domain=[0, 1], factual=v['factual'],
            boundary=boundary, event_status=v['basis'], evidence=refs(v['source'], v['meaning']))
    functions = []
    for m in d['mechanisms']:
        child, parents = m['child'], m['parents']
        if len(parents) != len(set(parents)) or set(parents)-set(ids):
            raise ValueError('Invalid parents')
        graph.add_edges_from((p, child) for p in parents)
        byid = {v['id']: v for v in d['variables']}
        if any(byid[p]['time'] > byid[child]['time'] for p in parents):
            raise ValueError('Recorded cause follows its child: '+child)
        constraints = []
        if nodes[child]['factual'] is not None and all(nodes[p]['factual'] is not None for p in parents):
            constraints.append(dict(id='observed_'+child, kind='row',
                when={p: nodes[p]['factual'] for p in parents}, allowed=[nodes[child]['factual']],
                basis='evidence', rationale='Recorded factual configuration only (source correctness audited separately).',
                evidence=nodes[child]['evidence']+sum([nodes[p]['evidence'] for p in parents], [])))
        for i, row in enumerate(m.get('rows', [])):
            constraints.append(dict(id='row_'+str(i), kind='row', when=row['when'], allowed=row['allowed'],
                basis=row['basis'], rationale=row['reason'], evidence=refs(row['source'], row['reason'])))
        if m.get('expression') is not None:
            expr = expression(m['expression'], parents)
            for i, row in enumerate(it.product([0, 1], repeat=len(parents))):
                state = dict(zip(parents, row))
                constraints.append(dict(id='expr_'+str(i), kind='row', when=state, allowed=[value(expr, state)],
                    basis='assumption', rationale='Unmodified generated expression, not inferred from prose.',
                    evidence=refs(m['source'], m['description'])))
        functions.append(dict(child=child, background=[], scope_status='declared_family',
            scope_assumptions=['Audit projection assumes the supplied parents are the complete graph and keeps recorded root states fixed.'],
            constraints=constraints))
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError('Cyclic mechanism dependencies')
    rep = dict(variables=list(nodes.values()), mechanisms=d['mechanisms'],
        topological_order=list(nx.topological_sort(graph)), outcome=d['outcome'])
    family = build_family(rep, {'functions': functions}, pack, max_models=max_models)
    if not family['models']:
        raise ValueError('Inconsistent or unavailable partial family: '+family['coverage'])
    return rep, family


def archive_audit(root):
    data, records = frozen(root), load_records(root)
    requests = {r['id']: r for r in records['requests']}
    report = {'scope': 'Post hoc interface/partial-encoding audit of unchanged first attempts; not new generation or a replacement score.',
              'independent_review': 'pending', 'inference_requests': 0, 'records': []}
    for story in data['stories']:
        for version in ('natural', 'controlled'):
            ident = story['id']+'_'+version+'_attempt0'
            original = requests[ident]['parsed']
            normalized, ledger = normalize_interface(original)
            row = dict(id=ident, **ledger, variables=len(original['variables']),
                declared_dependencies=sum(len(m['parents']) for m in original['mechanisms']),
                mechanisms=len(original['mechanisms']),
                before_schema_diagnostics=schema_diagnostics(original),
                after_schema_diagnostics=schema_diagnostics(normalized))
            for name, draft in [('original', original), ('normalized', normalized)]:
                try:
                    compile_model(draft, story, version)
                    row[name+'_strict_acceptance'] = True
                except (ValueError, KeyError) as error:
                    row[name+'_strict_acceptance'] = False
                    row[name+'_compiler_error'] = str(error)
            try:
                rep, family = partial_projection(normalized, story, version)
                audit = records['audits'][ident]
                projection = {'status': 'diagnostic_projection', 'coverage': family['coverage'],
                    'compatible_models': len(family['models']), 'unknown_rows': {
                        k: len(v['unknown_rows']) for k, v in family['local'].items()},
                    'source_errors_in_original_audit': audit['source_errors'], 'queries': []}
                projection['exact_prose_checks'] = []
                # Reuse the archived assistant's formal translations. They are
                # reviewable interpretations, never new family constraints.
                for claim in audit.get('local_claims', []):
                    if claim['type'] != 'exact':
                        continue
                    m = next(m for m in original['mechanisms'] if m['child'] == claim['child'])
                    if claim['text'] != m['description']:
                        raise ValueError('Translated claim is not anchored to this description')
                    local = family['local'][claim['child']]
                    checks = [proposition(claim, local['inputs'], local['rows'], t) for t in local['tables']]
                    good = sum(ok for ok,w in checks)
                    projection['exact_prose_checks'].append({'child':claim['child'], 'claim':claim,
                        'translation_provenance':'Archived Codex semantic audit, not independent adjudication',
                        'status':'inconsistent' if not good else 'entailed' if good == len(checks) else 'compatible_not_entailed',
                        'passing_tables':good, 'tables':len(checks),
                        'counterexample':next((w for ok,w in checks if not ok), None)})
                if version == 'controlled':
                    alignment = audit['alignment']
                    for q in story['reference']['questions']:
                        answer = query(rep, family, {alignment[k]: v for k, v in q['do'].items()})
                        projection['queries'].append({'id': q['id'], 'question': q['text'],
                            'expected': q['expected'], 'values': answer['values'],
                            'identified_within_declared_family': answer['identified'],
                            'coverage': answer['status']})
                row['projection'] = projection
            except ValueError as error:
                row['projection'] = {'status': 'unavailable', 'reason': str(error)}
            # Meaning-based mappings and source judgments remain attributed to
            # the archived assistant audit, not to this deterministic adapter.
            row['archived_factual_audit'] = records['audits'][ident]['factual_assertions']
            report['records'].append(row)
    report['strict_acceptance'] = {k: sum(r[k+'_strict_acceptance'] for r in report['records'])
                                   for k in ('original', 'normalized')}
    return report


def write_audit(root):
    report = archive_audit(root)
    path = Path(root)/FOLDER/'reassessment.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    return report
