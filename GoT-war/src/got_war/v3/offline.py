"""CPU contract evaluation and explicitly authored examples, never LLM results."""
import copy
from datetime import datetime, timezone
import hashlib
import itertools as it
import json
from pathlib import Path

from ..budget import atomic_json
from ..structural_programs import SCM, evaluate
from ..v2.mechanisms import inspect_mechanism
from .core import (build_family, check_claims, display_gate, fingerprint,
                   local_family, query, validate_representation, verify_reported_result)
from .study import RUN


def examples(config):
    """Known controlled contracts, authored for software validation, not discovered."""
    result=[]
    for case in config['cases'][:2]:
        segments=case['controlled_text'];packet={'segments':segments,'packet_sha256':case['packet_sha256']}
        refs={s['id']:s for s in segments}
        def ref(s, quote, supports):
            assert quote in refs[s]['text']
            return {'passage_id':s,'quote':quote,'supports':supports}
        if case['id']=='beacon':
            evid=ref('beacon_1','Either source alone provides current; with neither source there is no current.',
                     'Explicit substitution and absence rule in an authored controlled system.')
            lamp_evid=ref('beacon_1','The lamp illuminates exactly when current is available and its opaque safety shutter is open.',
                          'Explicit joint condition for the finite controlled system.')
            facts=ref('beacon_2','the grid and the charged backup battery were both available, the shutter was open, current reached the lamp, and the beacon was illuminated',
                      'Observed state in the controlled inspection.')
            specs=[('G','Grid available',1,0,'fixed_context'),('B','Backup charged',1,0,'fixed_context'),
                   ('S','Safety shutter closed',0,0,'fixed_context'),('P','Current available',1,1,'endogenous'),('Y','Beacon illuminated',1,2,'endogenous')]
            edges=[('e1','G','P','Supplies current without backup','The available grid supplies current even when the backup is unavailable.',evid,'explicit'),
                   ('e2','B','P','Supplies current without grid','The charged backup supplies current even when the grid is unavailable.',evid,'explicit'),
                   ('e3','P','Y','Energizes the exposed lamp','Current illuminates the beacon when the safety shutter is open.',lamp_evid,'explicit'),
                   ('e4','S','Y','Blocks visible illumination','A closed opaque shutter prevents illumination even when current is available.',lamp_evid,'explicit')]
            mechanisms=[('mP','P',['G','B'],'The selector supplies current from either available source.',
                'Grid and backup substitute for each other: either alone supplies current, and neither means no current.',evid),
                ('mY','Y',['P','S'],'The exposed lamp illuminates when supplied with current.',
                 'Current and an open shutter jointly enable illumination; closure blocks illumination even with current.',lamp_evid)]
            constraints={'P':[({'G':1},[1]),({'B':1},[1]),({'G':0,'B':0},[0])],
                         'Y':[({'P':0},[0]),({'S':1},[0]),({'P':1,'S':0},[1])]}
            interventions=[{'G':0},{'G':0,'B':0},{'S':1},{'B':0}]
            quotes={'P':evid,'Y':lamp_evid}
        else:
            evid=ref('ferry_3','The missing three configurations are not disclosed',
                     'The departure rule is explicitly partial; no unobserved value is identified.')
            facts=ref('ferry_3','Its factual output with both inputs present is crossing.',
                      'One known input-output row under the declared two-input scope.')
            delivery=ref('ferry_2','a parcel crossing on the ferry before noon is always recorded as delivered at the far-bank station, and a parcel that does not cross before noon is not recorded there',
                         'Explicit complete recording mechanism in the controlled system.')
            specs=[('P','Permit possessed',1,10,'fixed_context'),('B','Boat ready',1,10,'fixed_context'),
                   ('C','Parcel crosses',1,11,'endogenous'),('Y','Delivery recorded',1,12,'endogenous')]
            edges=[('e1','P','C','Possible departure authorization','Permit possession is a proposed departure input; the missing rule leaves its influence unresolved.',evid,'unresolved'),
                   ('e2','B','C','Possible transport availability','Boat readiness is a proposed crossing input; the missing rule leaves its functional role unresolved.',evid,'unresolved'),
                   ('e3','C','Y','Triggers the delivery record','A crossing parcel is recorded as delivered; no crossing means no delivery record in this controlled system.',delivery,'explicit')]
            mechanisms=[('mC','C',['P','B'],'The departure mechanism is not specified beyond the observed joint input row.',
                'Permission and readiness may interact or substitute, or an input may be irrelevant; the text leaves the other three configurations unknown.',evid),
                ('mY','Y',['C'],'The station records delivery exactly when the parcel crosses before noon.', '', delivery)]
            constraints={'C':[({'P':1,'B':1},[1])],'Y':[({'C':0},[0]),({'C':1},[1])]}
            interventions=[{'P':0},{'B':0},{'C':0},{'P':1,'B':1}]
            quotes={'C':facts,'Y':delivery}
        vs=[{'id':k,'label':label,'definition':label+' during the stated controlled inspection or trip; 1 means present, 0 absent.',
             'actor':'controlled system','domain':[0,1],'factual':value,'event_time':when,'statement_time':when,
             'time_note':'Controlled time/stage index; no TV chronology inferred.', 'kind':'narrative_fact',
             'event_status':'explicit','boundary':boundary,'boundary_reason':'Explicit finite controlled scope.', 'evidence':[facts]}
            for k,label,value,when,boundary in specs]
        if case['id']=='ferry':
            for v in vs:
                if v['id'] in ('P','B'):
                    v['evidence']=[ref('ferry_1','Iona stood at the ferry with a stamped permit in her hand and a boat ready at the landing.',
                                       'Factual permit possession and boat readiness; no universal departure mechanism.')]
                elif v['id']=='Y':
                    v['evidence']=[ref('ferry_2','Today the parcel was recorded as delivered.', 'Factual delivery record.')]
        next(v for v in vs if v['id']=='Y')['definition']=case['outcome']
        es=[{'id':eid,'parent':a,'child':b,'label':label,'process':process,
             'participants':[],'conditions':[],'qualifications':['Author-defined contract example; not LLM discovery.'],
             'evidence':[evidence],'contradictions':[],'gaps':(['Unobserved function rows'] if status=='unresolved' else []),
             'status':status,'endpoint_support':{'parent':'controlled factual input','child':'controlled factual state'},
             'temporal_status':'consistent','information_status':'consistent','structural_implications':[],
             'alternatives':[]} for eid,a,b,label,process,evidence,status in edges]
        ms=[{'id':ident,'child':child,'parents':parents,'description':desc,'joint_description':joint,
             'evidence':[evidence],'assumptions':['Declared deterministic controlled scope.'],
             'gaps':(['Three unobserved rows'] if case['id']=='ferry' and child=='C' else [])}
            for ident,child,parents,desc,joint,evidence in mechanisms]
        r={'outcome':'Y','variables':vs,'edges':es,'mechanisms':ms,'gaps':[]}
        r=validate_representation(r,packet)
        fs={'functions':[{'child':child,'background':[],'scope_status':'declared_family',
             'scope_assumptions':['The explicitly bounded controlled system is deterministic and has the declared inputs only.'],
             'constraints':[{'id':child+'_r'+str(i),'kind':'row','when':when,'allowed':allowed,
                 'basis':'evidence','rationale':'Literal controlled rule or factual row; not a literary generalization.',
                 'evidence':[quotes[child]]} for i,(when,allowed) in enumerate(rows)]}
             for child,rows in constraints.items()]}
        fam=build_family(r,fs,packet)
        audit={'origin':'Authored software-contract fixture, not generated semantic review or independent human review',
            'records':[{'id':x['id'],'source_to_description':'unresolved' if x.get('status')=='unresolved' else 'supported',
                        'description_to_function':'consistent','formal_claims_complete':True,'label_specific':True,
                        'reason':'Controlled fixture contract; not a measured review judgment.'} for x in es+ms],
            'claims':[]}
        gate=display_gate(r,fam,audit)
        qs=[]
        for intervention,gold in zip(interventions,case['queries']):
            answer=query(r,fam,intervention)
            qs.append({'id':gold['id'],'question':gold['question'],'do':intervention,'result':answer,
                'reference':gold['gold'],'correct':answer['values']==gold['gold'],
                'execution_check':verify_reported_result(r,fam,intervention,answer)})
        result.append({'id':case['id'],'provenance':'software-authored controlled fixture, not LLM output',
            'representation':r,'family':fam,'audit':audit,'display_gate':gate,'queries':qs})
    return result


def exhaustive_validation():
    """Independent bit-mask oracle for all two-input Boolean truth tables/row masks."""
    nodes={k:{'domain':[0,1]} for k in ['A','B','Y']};rows=[(0,0),(0,1),(1,0),(1,1)]
    trials=0;sets=0;failures=[];count_range=set()
    # Here bit i is row i. The oracle does not call the constraint evaluator.
    oracle_tables=[tuple((mask>>i)&1 for i in range(4)) for mask in range(16)]
    for truth in oracle_tables:
        for observed_mask in range(16):
            known={i:truth[i] for i in range(4) if (observed_mask>>i)&1}
            cs=[{'id':'r'+str(i),'kind':'row','when':dict(zip(['A','B'],rows[i])),
                 'allowed':[val],'basis':'assumption','rationale':'Controlled mathematical test row','evidence':[]}
                for i,val in known.items()]
            got=local_family({'child':'Y','parents':['A','B'],'constraints':cs},nodes)
            expected={t for t in oracle_tables if all(t[i]==val for i,val in known.items())}
            trials+=1;count_range.add(len(expected))
            if {tuple(t) for t in got['tables']}!=expected:
                failures.append({'truth':truth,'observations':observed_mask,'failure':'family mismatch'})
            for i in range(4):
                sets+=1
                if {t[i] for t in got['tables']}!={t[i] for t in expected}:
                    failures.append({'truth':truth,'observations':observed_mask,'row':i})
    return {'type':'finite-engine validation, not narrative or LLM accuracy',
        'generating_boolean_functions':16,'observation_masks_per_function':16,
        'local_family_comparisons':trials,'outcome_set_comparisons':sets,
        'compatible_counts':sorted(count_range),'failures':failures,'passed':not failures}


def replay_v2(root):
    root=Path(root);choice=json.loads((root/'configs/application_selection_v2.json').read_text())
    source=root/choice['record'];app=json.loads(source.read_text());model=app['records'][0]['model'];scm=SCM(model)
    nodes=[]
    for ident in scm.order:
        n=scm.nodes[ident];b=inspect_mechanism(scm,ident)
        nodes.append({'id':ident,'label':n['label'],'parents':n['parents'],
            'original_generated_description':n.get('generated_description'),
            'v2_displayed_description':n.get('description'),'v2_short_mechanism':n.get('short_mechanism'),
            'retained_v2_semantic_review':n.get('function_review',{}),
            'behavior':b,'factual':scm.solve()[ident]})
    checks=[]
    for rec in app['records']:
        s=SCM(rec['model'])
        for q in rec['queries']:
            actual=s.solve(interventions=q['do'])[q['target']]
            checks.append({'id':q['id'],'do':q['do'],'target':q['target'],'actual':actual,'stored':q['modeled_outcome'],'match':actual==q['modeled_outcome']})
    return {'origin':'Preserved v2 conditional application; no v3 discovery or semantic re-review',
        'record':choice['record'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'model':model,'nodes':nodes,'query_replay':checks,'passed':all(c['match'] for c in checks),
        'directional_support':app['records'][0]['edge_evidence'],
        'interpretation':'A prior negative semantic flag is retained evidence about review behavior, not independent truth. A bare if-description may be sufficient-only; do not silently read it as if-and-only-if.'}


def run(root):
    root=Path(root);run=root/'runs'/RUN;config=json.loads((root/'configs/v3_development.json').read_text())
    data={'engine':exhaustive_validation(),'examples':examples(config),'v2_replay':replay_v2(root),
          'inference_status':'unrun','independent_review':'pending',
          'at':datetime.now(timezone.utc).isoformat()}
    block=run/'infrastructure_blocker.json'
    if block.exists():data['blocker']=json.loads(block.read_text())
    atomic_json(run/'offline.json',data)
    comparisons=[{'case':c['id'],'arm':a,'status':'unrun_infrastructure',
        'reason':'CUDA initialization 999; /dev/nvidia-uvm I/O error; no reachable authorized inference API',
        'generated_tokens':0,'inference_requests':0,'failed_synthesis':None,'intervention_accuracy':None,
        'source_packet_sha256':c['packet_sha256']} for c in config['cases'] for a in ('A','B','C')]
    atomic_json(root/'results/v3/comparison.json',{'development_only':True,'planned_cases':3,'attempted_inference_cases':0,
        'arms':comparisons,'offline_controlled_examples_are_not_method_results':True,'expansion_performed':False,
        'gate':'Not passed: actual end-to-end model generation/revision has not run.'})
    print(json.dumps({'local_families':data['engine']['local_family_comparisons'],
        'outcome_sets':data['engine']['outcome_set_comparisons'],'failures':len(data['engine']['failures']),
        'controlled_fixture_queries':sum(len(x['queries']) for x in data['examples']),
        'v2_queries_replayed':len(data['v2_replay']['query_replay'])}))


if __name__=='__main__':
    import sys
    run(sys.argv[1] if len(sys.argv)>1 else '.')
