"""Tests of quantified prose claims and reused SCM semantics, not story validity."""
import copy
import itertools as it
from pathlib import Path
import pytest
from got_war.simple_stories import (FROZEN_SHA, compile_model, construction_request,
    direct_request, frozen, mutation_checks, proposition, reference_world, verify_references)
from got_war.v3.core import fingerprint, query

ROOT=Path(__file__).resolve().parents[1]

def partial_fixture():
    s={'id':'unit','natural':[{'id':'S1','origin':'retelling','text':'The input is on; the device runs.'}]}
    d={'outcome':'Y','scope_assumptions':['Boolean local scope'], 'variables':[
        {'id':'A','label':'Input on','meaning':'Input is on','actor':'device','time':0,'factual':1,'kind':'narrative_fact','boundary':'fixed_context','source':['S1'],'basis':'explicit'},
        {'id':'Y','label':'Device running','meaning':'Device runs','actor':'device','time':1,'factual':1,'kind':'narrative_fact','boundary':'endogenous','source':['S1'],'basis':'explicit'}],
       'mechanisms':[{'child':'Y','parents':['A'],'description':'The input may support operation; off behavior is unknown.',
        'source':['S1'],'assumptions':[],'unknowns':['Off behavior unspecified'],'expression':None,'rows':[],
        'edges':[{'parent':'A','label':'May supply power','process':'The input may supply the power needed by the device.',
            'source':['S1'],'status':'hypothetical','conditions':[],'gaps':['Direction not explicit']}],'claims':[]}]}
    return s,d


def test_necessity_checks_all_other_inputs_not_all_zero():
    rows=list(it.product([0,1],repeat=2));or_values=[0,1,1,1]
    assert or_values[0]==0  # the old weak check would pass
    ok,w=proposition({'type':'necessary','when':{'A':1},'output':1},['A','B'],rows,or_values)
    assert not ok and w['counterexample']=={'inputs':{'A':0,'B':1},'output':1}


def test_conjunction_checks_each_necessity_and_joint_sufficiency():
    rows=list(it.product([0,1],repeat=2));c={'type':'conjunction','when':{'A':1,'B':1},'output':1}
    assert proposition(c,['A','B'],rows,[0,0,0,1])[0]
    for table in ([0,1,1,1],[0,0,1,1],[0,1,0,1],[0,0,0,0]):
        assert not proposition(c,['A','B'],rows,table)[0]


def test_inhibition_distinguishes_possible_from_universal():
    rows=[list(x) for x in it.product([0,1],repeat=2)];xor=[0,1,1,0]
    c={'type':'inhibits','parent':'B','global':False}
    assert proposition(c,['A','B'],rows,xor)[0]
    assert not proposition(dict(c,**{'global':True}),['A','B'],rows,xor)[0]


def test_sufficiency_is_universal_over_unspecified_context():
    c={'type':'sufficient','when':{'A':1},'output':1};rows=list(it.product([0,1],repeat=2))
    assert not proposition(c,['A','B'],rows,[0,0,0,1])[0]
    assert proposition(c,['A','B'],rows,[0,1,1,1])[0]


def test_vacuous_necessity_exposed():
    assert proposition({'type':'necessary','when':{'A':1},'output':1},['A'],[(0,),(1,)],[0,0])==(True,{'vacuous':True})


def test_mutations_are_detected_with_concrete_contexts():
    mutations=mutation_checks()
    assert len(mutations)==4 and all(x['detected'] and x['counterexample'] for x in mutations)


def test_natural_missing_row_preserved_and_fixed_functions_reused():
    s,d=partial_fixture();c=compile_model(d,s,'natural');fam=c['family'];rep=c['representation']
    assert fam['local']['Y']['tables']==[[0,1],[1,1]]
    before=fingerprint(fam)
    assert query(rep,fam,{'A':0})['values']==[0,1]
    assert query(rep,fam,{})['values']==[1]
    assert query(rep,fam,{'Y':0})['values']==[0]
    assert fingerprint(fam)==before


def test_factual_conflict_rejected_without_relaxation():
    s,d=partial_fixture();d['mechanisms'][0]['expression']='not A'
    with pytest.raises(ValueError):compile_model(d,s,'natural')


def test_nonexistent_sentence_cannot_be_used_as_evidence():
    s,d=partial_fixture();d['mechanisms'][0]['edges'][0]['source']=['S999']
    with pytest.raises(KeyError):compile_model(d,s,'natural')


def test_claim_must_quote_actual_description():
    s,d=partial_fixture();d['mechanisms'][0]['claims']=[{'type':'necessary','text':'Invented claim','when':{'A':1},'output':1}]
    with pytest.raises(ValueError,match='actual mechanism'):compile_model(d,s,'natural')


def test_reference_freeze_and_factual_and_twelve_interventions():
    data=frozen(ROOT);assert len(verify_references(data))==12
    assert all(80<=sum(len(x['text'].split()) for x in s[v])<=160 for s in data['stories'] for v in ['natural','controlled'])


def test_generation_prompt_is_invariant_to_reference_changes():
    data=frozen(ROOT)
    for i,s in enumerate(data['stories']):
        changed=copy.deepcopy(s);changed['reference']={'SECRET':'gold graph must not leak'}
        assert construction_request(s,'controlled',i)==construction_request(changed,'controlled',i)
        changed=copy.deepcopy(s)
        for q in changed['reference']['questions']:q.update(expected=1-q['expected'],do={'SECRET':1})
        assert direct_request(s,i)==direct_request(changed,i)


def test_full_adapter_detects_necessary_input_removed_not_just_zero_row():
    s,d=partial_fixture();m=d['mechanisms'][0]
    m['description']='The input must be on for the device to run.'
    m['expression']='A';m['claims']=[{'text':m['description'],'type':'necessary','when':{'A':1},'output':1}]
    assert compile_model(d,s,'natural')['formal_consistent']
    m['expression']='1'  # preserves factual reconstruction but contradicts necessity
    result=compile_model(d,s,'natural')
    assert not result['formal_consistent']
    assert result['claims'][0]['counterexamples'][0]['counterexample']['inputs']=={'A':0}


def test_actionable_schema_errors_do_not_guess_missing_causal_targets():
    from got_war.simple_stories import schema_diagnostics
    s,d=partial_fixture();d['edges']=d['mechanisms'][0].pop('edges');d['variables'][1]['boundary']='fixed_context'
    errors=schema_diagnostics(d)
    assert any('flat edges without child IDs' in x for x in errors)
    assert any('labelled fixed_context' in x for x in errors)
    with pytest.raises(ValueError,match='Representation diagnostics'):compile_model(d,s,'natural')


def test_reference_semantic_equivalence_all_mapped_interventions():
    from got_war.simple_stories import reference_draft, compare_all_interventions
    # Alias every variable to show scoring is semantic mapping, not name equality.
    story=frozen(ROOT)['stories'][0];draft=reference_draft(story)
    mapping={v['id']:'alias_'+v['id'] for v in draft['variables']}
    for v in draft['variables']:v['id']=mapping[v['id']]
    draft['outcome']=mapping[draft['outcome']]
    for m in draft['mechanisms']:
        m['child']=mapping[m['child']];m['parents']=[mapping[p] for p in m['parents']]
        import re
        m['expression']=re.sub(r'\b[A-Z]\b',lambda x:mapping[x.group()],m['expression'])
        for e in m['edges']:e['parent']=mapping[e['parent']]
    result=compare_all_interventions(story,compile_model(draft,story,'controlled'),mapping)
    assert result['all_equivalent'] and result['interventions']==243
