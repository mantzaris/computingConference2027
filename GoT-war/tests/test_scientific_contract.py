import copy, json, os, signal, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from got_war.structural_programs import SCM,InvalidModel
from got_war.attribution import coalitions,disjoint_mechanism_groups
from got_war.budget import Budget


def ref(x):return {'ref':x}
def op(k,*args):return {'op':k,'args':list(args)}
def tiny(kind='or'):
    return {'outcome':'W','background':{'U':{'type':'bool','observed':1}},'nodes':[
     {'id':'A','label':'A','type':'bool','time':0,'parents':[],'noise':['U'],'expr':{'noise':'U'},'observed':1,'reference':0},
     {'id':'B','label':'B','type':'bool','time':1,'parents':['A'],'noise':[],'expr':ref('A'),'observed':1,'reference':0},
     {'id':'C','label':'C','type':'bool','time':1,'parents':['A'],'noise':[],'expr':ref('A'),'observed':1,'reference':0},
     {'id':'W','label':'W','type':'bool','time':2,'parents':['B','C'],'noise':[],'expr':op(kind,ref('B'),ref('C')),'observed':1,'reference':0}]}


def test_shared_background_and_non_descendants():
    s=SCM(tiny()); factual=s.solve(); assert s.solve(interventions={'B':factual['B']})==factual
    changed=s.solve(interventions={'B':0});assert changed['A']==factual['A'];assert changed['C']==factual['C']
    assert s.solve(background={'U':0})['W']==0
    assert s.solve(background={'U':0},interventions={'B':1})['W']==1

@pytest.mark.parametrize('kind,expected', [('or',[.5,.5]),('and',[.5,.5])])
def test_redundancy_conjunction_and_efficiency(kind,expected):
    result=coalitions(SCM(tiny(kind)),[['A','B','W'],['A','C','W']])
    assert result['phi']==pytest.approx(expected)
    assert result['efficiency_residual']<1e-12
    if kind=='or': assert result['naive_sum']==2
    else: assert result['naive_sum']==0


def test_shared_edge_cache_and_recombination():
    m=tiny();m['nodes'].append({'id':'T','label':'T','type':'bool','time':3,'parents':['W'],'noise':[],'expr':ref('W'),'observed':1,'reference':0});m['outcome']='T'
    paths=[['A','B','W','T'],['A','C','W','T']]
    r=coalitions(SCM(m),paths);assert r['full']==1;assert sum(r['phi'])==1
    duplicate=coalitions(SCM(m),[paths[0],paths[0]]);assert duplicate['unique_edge_masks']==2
    assert disjoint_mechanism_groups(paths)==[[0,1]]


def test_negative_contributions_and_reference_sensitivity():
    m=tiny();m['nodes'][2]['expr']=op('not',ref('A'));m['nodes'][2]['observed']=0
    m['nodes'][3]['expr']=op('and',ref('B'),op('not',ref('C')))
    s=SCM(m);p=[['A','B','W'],['A','C','W']]
    result=coalitions(s,p,references={('A','C'):0,('C','W'):1})
    assert result['efficiency_residual']<1e-12
    # Explicit inhibitory route with present inhibitory input.
    m=tiny();m['nodes'][3]['expr']=op('sub',ref('B'),ref('C'));m['nodes'][3].update(type='int',bounds=[-1,1],observed=0)
    r=coalitions(SCM(m),p);assert r['phi']==pytest.approx([1,-1])
    other=coalitions(SCM(m),p,references={('A','B'):1,('B','W'):1})
    assert other['baseline']!=r['baseline']


def test_undeclared_and_inactive_inputs_rejected():
    m=tiny();m['nodes'][1]['expr']=ref('undeclared')
    with pytest.raises(InvalidModel):SCM(m)
    m=tiny();m['nodes'][3]['expr']=op('or',ref('B'),op('and',ref('C'),{'const':0}))
    with pytest.raises(InvalidModel,match='Inactive'):SCM(m)


def test_temporal_and_state_types():
    m=tiny();m['nodes'][0]['time']=9
    with pytest.raises(InvalidModel,match='Temporal'):SCM(m)
    m=tiny();m['nodes'][3]['expr']=op('add',ref('B'),ref('C'))
    with pytest.raises(InvalidModel,match='domain'):SCM(m)


def test_ast_cannot_execute_code():
    m=tiny();m['nodes'][1]['expr']={'op':'eval','args':[{'const':'open("/etc/passwd")'}]}
    with pytest.raises(InvalidModel):SCM(m)


def test_categorical_and_numeric_equations():
    m={'outcome':'Y','background':{'U':{'type':'category','values':['calm','alert'],'observed':'alert'}},'nodes':[
      {'id':'X','type':'category','values':['calm','alert'],'parents':[],'noise':['U'],'expr':{'noise':'U'},'observed':'alert','reference':'calm','time':0},
      {'id':'Y','type':'int','bounds':[0,4],'parents':['X'],'noise':[],'expr':op('if',op('eq',ref('X'),{'const':'alert'}),{'const':4},{'const':1}),'observed':4,'reference':1,'time':1}]}
    s=SCM(m);assert s.solve(interventions={'X':'calm'})['Y']==1
    assert coalitions(s,[['X','Y']])['phi']==[3]


def test_passage_removal_is_not_event_intervention():
    model=tiny();model['nodes'][0]['segments']=['s1'];before=SCM(model).solve()
    altered=copy.deepcopy(model);altered['nodes'][0]['segments']=[]
    assert SCM(altered).solve()==before
    assert SCM(model).solve(interventions={'A':0})!=before


def test_deadline_resume_and_scoped_timeout(tmp_path):
    # pytest basetemp is configured inside GoT-war so all test artifacts stay in scope.
    now=datetime.now(timezone.utc);cfg=tmp_path/'configs';cfg.mkdir()
    hard=now+timedelta(seconds=3)
    (cfg/'budget.json').write_text(json.dumps({'campaign_id':'test','hard_deadline':hard.isoformat(),'soft_deadline':hard.isoformat(),'no_heavy_jobs_after':hard.isoformat()}))
    b=Budget(tmp_path);first=b.config['hard_deadline'];assert Budget(tmp_path).config['hard_deadline']==first
    other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    task=b.launch([sys.executable,'-c','import time;time.sleep(30)'],'owned')
    (b.run/'completed_artifact').write_text('preserve')
    try:
        time.sleep(3.1)
        with pytest.raises(RuntimeError):b.check()
        assert b.stop_owned(signal.SIGKILL)==['owned']
        assert other.poll() is None
        assert (b.run/'completed_artifact').read_text()=='preserve'
    finally:other.terminate();other.wait(timeout=5)


def test_unknown_rule_intervention_can_override_ambiguity():
    from got_war.experiments import execute_answers
    m=tiny();m['nodes'][3]['unknown']=True
    case={'queries':[{'id':'q','kind':'intervention','target':'W','do':{'W':0}}]}
    assert execute_answers(m,case,True)[0]['values']==[0]
    assert not execute_answers(m,case,True)[0]['abstain']


def test_persistent_generation_cache_never_repeats_completed_request(tmp_path):
    from got_war.generation import Generator,digest,SYSTEM
    now=datetime.now(timezone.utc);(tmp_path/'configs').mkdir()
    (tmp_path/'configs/budget.json').write_text(json.dumps({'campaign_id':'test','hard_deadline':(now+timedelta(hours=24)).isoformat()}))
    (tmp_path/'configs/models.json').write_text(json.dumps({'primary':'test','revision':'frozen'}))
    specification={'model':'test','revision':'frozen','system':SYSTEM,'prompt':'cached','seed':2027,'temperature':.2,'max_tokens':2048,'top_p':.8,'thinking':False}
    g=Generator(tmp_path);key=digest(specification)
    g.db.execute('INSERT INTO jobs(key,status,response) VALUES(?,?,?)',(key,'done','{"cached_result":true}'));g.db.commit();g.db.close()
    resumed=Generator(tmp_path)
    assert resumed.call('test','cached')=={'cached_result':True}
    assert resumed.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1


def test_generated_identifier_cannot_select_artifact_path():
    from got_war.construction import variable_error
    node={'id':'../../escape','label':'state','definition':'state','type':'bool','time':0,'observed':1,'reference':0,'reference_meaning':'absent','actor':'x','status':'established_event','segment_id':'s'}
    assert 'identifier' in variable_error(node,{'s':{'text':'state'}})


def test_numeric_latent_needs_measurement_rule():
    from got_war.construction import variable_error
    node={'id':'x','label':'quantity','definition':'unmeasured quantity','type':'float','bounds':[0,1],'time':0,'observed':.6,'reference':0.,'reference_meaning':'baseline','actor':'x','status':'modeling_assumption','segment_id':'s'}
    assert 'measurement_rule' in variable_error(node,{'s':{'text':'state'}})


def test_failed_answer_is_not_successful_uncertainty_handling():
    from got_war.evaluation import score
    case={'queries':[{'id':'q','kind':'counterfactual','gold_possible':[0,1],'identified':False}]}
    assert score(case,{'error':'generation failed'})['score']==0
    assert score(case,{'answers':[{'id':'q','abstain':True}]})['score']==1
    assert score(case,{'answers':[{'id':'q','values':[0,1]}]})['score']==1


def test_invalid_application_noise_gets_bounded_repair():
    from got_war.application import synthesize
    from pathlib import Path
    class FixtureGenerator:
        root=Path(__file__).resolve().parents[1]
        roles=[]
        def call(self,role,*args,**kwargs):
            self.roles.append(role)
            child=op('and',ref('A'),{'noise':'unjustified'}) if role=='application_equations' else ref('A')
            return {'rules':[{'id':'A','expr':{'noise':'U_A'}},{'id':'B','expr':child}]}
    nodes=[{'id':ident,'label':ident,'type':'bool','observed':1,'reference':0,'parents':parents,'time':i}
           for i,(ident,parents) in enumerate([('A',[]),('B',['A'])])]
    gen=FixtureGenerator()
    packet={'case':{'id':'fixture','outcome':'B active'},'segments':[],'packet_sha256':'fixture'}
    model,diagnostics,failures=synthesize(gen,packet,{'nodes':nodes,'outcome':'B'},0)
    assert len(failures)==1
    assert gen.roles==['application_equations','application_equation_repair']
    assert set(model['background'])=={'U_A'}
    assert SCM(model).solve(interventions={'A':0})['B']==0


def test_literal_alignment_cannot_invent_or_join_passages():
    from got_war.spans import align_quote
    text='The "northern unit" sends its forces, after deliberation, to the gate.'
    result=align_quote("The 'northern unit' sends its forces.",text)
    assert result['quote'] in text and not result['raw_quote_exact']
    assert align_quote('The northern unit defeats its forces',text) is None
    excerpt=align_quote('The northern unit sends its forces...to the gate',text)
    assert excerpt['quote'] in text and 'deliberation' not in excerpt['quote']


def test_local_parent_slots_preserve_declared_dependencies():
    from got_war.local_equations import bind_expression,check_local
    parents=[{'id':x,'type':'bool','observed':1,'reference':0,'parents':[],'time':0} for x in ('A','B')]
    child={'id':'Y','type':'bool','observed':1,'reference':0,'parents':['A','B'],'time':1}
    expression=bind_expression(op('or',ref('P0'),ref('P1')),{'P0':'A','P1':'B'},None)
    check_local(child,parents,expression)
    assert expression==op('or',ref('A'),ref('B'))
    with pytest.raises(InvalidModel):bind_expression(ref('unlisted'),{'P0':'A'},None)
    with pytest.raises(InvalidModel):check_local(child,parents,ref('A'))
