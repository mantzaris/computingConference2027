"""Recovery must preserve meaning, uncertainty and the historical evidence."""
import copy
import json
from pathlib import Path
import pytest

from got_war.story_reassessment import normalize_interface, partial_projection
from got_war.simple_stories import frozen, load_records, proposition
from got_war.v3.core import fingerprint, query

ROOT = Path(__file__).resolve().parents[1]


def test_normalization_only_moves_uniquely_attributable_records():
    draft = {'variables':[{'id':'X','boundary':'fixed_context'}, {'id':'Y','boundary':'endogenous'}],
        'mechanisms':[{'child':'X','parents':['A','B'],'description':'A helps X.'},
                      {'child':'Y','parents':['A'],'description':'Y may respond.'}],
        'edges':[{'parent':'A','label':'Ambiguous endpoint'}, {'parent':'B','label':'Feeds X'}],
        'claims':[{'text':'A helps X.','type':'necessary','when':{'A':1},'output':1}]}
    original = copy.deepcopy(draft)
    view, log = normalize_interface(draft)
    assert draft == original
    assert view['edges'] == [original['edges'][0]]
    assert view['mechanisms'][0]['edges'] == [original['edges'][1]]
    assert view['mechanisms'][0]['claims'] == original['claims']  # attached, NOT semantically approved
    assert log['unresolved_attachments'][0]['candidate_children'] == ['X','Y']
    assert log['operations'][0]['kind'] == 'representation_precedence'
    assert view['variables'][0]['boundary'] == 'endogenous'


def test_ambiguous_prose_is_not_automatically_quantified_or_completed():
    draft = {'variables':[], 'mechanisms':[{'child':'Y','parents':['A'],
              'description':'The resource helps the response.', 'expression':None, 'rows':[]}], 'edges':[]}
    view, log = normalize_interface(draft)
    assert view['mechanisms'][0]['claims'] == []
    assert view['mechanisms'][0]['expression'] is None and view['mechanisms'][0]['rows'] == []
    # A different wording is not a semantic error, but cannot be automatically
    # attached by this exact-anchor interface adapter.
    draft['claims'] = [{'text':'The resource contributes to the response.','type':'necessary'}]
    view, log = normalize_interface(draft)
    assert view['claims'] == draft['claims'] and len(log['unresolved_attachments']) == 1


def controlled(story_id):
    s = next(s for s in frozen(ROOT)['stories'] if s['id'] == story_id)
    record = next(r for r in load_records(ROOT)['requests'] if r['id'] == story_id+'_controlled_attempt0')
    return s, record['parsed']


def test_partial_projection_preserves_unknowns_and_does_not_use_exact_prose_as_constraints():
    story, draft = controlled('humpty'); before = fingerprint(draft)
    rep, fam = partial_projection(draft, story, 'controlled')
    assert len(fam['models']) == 1024 and fam['exhaustive']
    assert query(rep, fam, {'E':1})['values'] == [0,1]
    assert query(rep, fam, {})['values'] == [1]
    assert fingerprint(draft) == before


def test_projection_never_repairs_a_wrong_source_fact():
    story, draft = controlled('wolf')
    rep, fam = partial_projection(draft, story, 'controlled')
    assert query(rep, fam, {'earlier_false_alarms':0})['values'] == [1]
    # The definite wrong answer is the diagnostic, not something to correct
    # behind the scenes using the reference model.
    draft = copy.deepcopy(draft)
    m = next(m for m in draft['mechanisms'] if m['child'] == 'villagers_respond_in_time')
    m['expression'] = 'boy_gives_new_warning and not villagers_distrust_boy'
    with pytest.raises(ValueError, match='Inconsistent'):
        partial_projection(draft, story, 'controlled')


def test_nonexistent_evidence_and_missing_mechanism_are_not_fabricated():
    story, draft = controlled('humpty')
    broken = copy.deepcopy(draft); broken['variables'][0]['source'] = ['S999']
    with pytest.raises(ValueError, match='Unknown sentence'):
        partial_projection(broken, story, 'controlled')
    broken = copy.deepcopy(draft); broken['mechanisms'] = [m for m in broken['mechanisms'] if m['child'] != 'S']
    with pytest.raises(ValueError, match='Missing mechanism'):
        partial_projection(broken, story, 'controlled')


def test_new_audit_does_not_call_partial_compatibility_a_contradiction():
    audit = json.loads((ROOT/'experiments/simple_stories/reassessment.json').read_text())
    checks = [c for r in audit['records'] for c in r['projection'].get('exact_prose_checks', [])]
    assert len(checks) == 11
    assert sum(c['status'] == 'compatible_not_entailed' for c in checks) == 9
    assert sum(c['status'] == 'inconsistent' for c in checks) == 2
    assert audit['strict_acceptance'] == {'original':0, 'normalized':0}
    # Strict necessity is retained for an actually asserted proposition.
    ok, witness = proposition({'type':'necessary','when':{'A':1},'output':1},
                              ['A','B'],[(0,0),(0,1),(1,0),(1,1)],[0,1,1,1])
    assert not ok and witness['counterexample']['inputs'] == {'A':0,'B':1}


def test_publication_equations_and_dependencies_are_archived_not_invented():
    import sys
    sys.path.insert(0, str(ROOT/'scripts'))
    from publication_figures import specifications, check_display_equations
    specs = specifications()  # checks every equation, edge selection and Bolton result
    assert len(specs) == 7
    assert sum(len(s['edges']) for s in specs if s['folder'] == 'simple_stories') == 19
    b = next(s for s in specs if s['stem'] == 'bolton_mechanism_interventions')
    assert [r['values'] for r in b['comparison']] == [[0,0],[1,1],[0,1]]
    with pytest.raises(ValueError, match='no archived counterpart'):
        check_display_equations(['Y = A ∨ B'], [{'Y':'A and B'}])
