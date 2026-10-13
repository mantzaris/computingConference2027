"""Three fixed development packets, bounded paired inference, no held-out tuning."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from ..budget import Budget, atomic_json
from ..generation import Generator, SYSTEM
from ..retrieval import retrieve
from ..structural_programs import SCM
from .core import fingerprint, query, verify_reported_result
from .pipeline import (MechanismFirst, V2Adapter, align_queries, v2_family,
                       presentation)

RUN = 'development_v3_20261013'


def packet(segments):
    text = '\n\n'.join('['+s['id']+'] '+s.get('episode', '')+'\n'+s['text'] for s in segments)
    return {'segments': segments, 'packet_sha256': hashlib.sha256(text.encode()).hexdigest()}


def controlled_segment(ident, text):
    return {'id': ident, 'text': text, 'episode': 'controlled time indices',
            'source_id': ident.split('_')[0], 'source_type': 'authored controlled narrative',
            'url': 'controlled://v3/'+ident, 'dependence_cluster': ident.split('_')[0],
            'start': 0, 'end': len(text), 'first_line': 1, 'last_line': 1, 'scene': 1}


def prepare(root):
    root = Path(root); run = root/'runs'/RUN; run.mkdir(parents=True, exist_ok=True)
    dest = root/'configs/v3_development.json'
    if dest.exists():
        raise RuntimeError('Development cases already frozen; do not overwrite')
    cases = [
        {'id': 'beacon', 'kind': 'controlled_complete', 'outcome': 'The harbor beacon is illuminated at noon.',
         'segments': [controlled_segment('beacon_1',
             'At noon, the harbor beacon can draw current from the grid or from a charged backup battery. Either source alone provides current; with neither source there is no current. The selector always uses an available source and needs no operator action. The lamp illuminates exactly when current is available and its opaque safety shutter is open. A closed shutter prevents illumination even with current. These rules hold throughout the noon inspection; no other faults or inputs are in scope.'),
             controlled_segment('beacon_2',
             'During the inspection the grid and the charged backup battery were both available, the shutter was open, current reached the lamp, and the beacon was illuminated. A clerk rang the lunch bell one minute later. The bell is electrically separate and does not operate the beacon.')],
         'queries': [
             {'id':'q1','question':'Disconnect the grid at noon while leaving the backup battery and shutter as observed. Is the beacon illuminated?', 'gold':[1], 'changing':False},
             {'id':'q2','question':'Make both the grid and backup battery unavailable at noon. Is the beacon illuminated?', 'gold':[0], 'changing':True},
             {'id':'q3','question':'Close the opaque safety shutter at noon, with the other background conditions unchanged. Is the beacon illuminated?', 'gold':[0], 'changing':True},
             {'id':'q4','question':'Make the backup battery unavailable at noon while leaving the grid available. Is the beacon illuminated?', 'gold':[1], 'changing':False}],
         'reference': {'variables':['grid','backup','current','shutter_closed','illuminated'],
                       'factual':[1,1,1,0,1], 'equations':{'current':'grid OR backup','illuminated':'current AND NOT shutter_closed'},
                       'scope':'Explicit deterministic rules in text; the later disconnected bell is not causal.',
                       'independent_human_verification':False}},
        {'id': 'ferry', 'kind': 'controlled_partial', 'outcome': 'The parcel is recorded as delivered at the far-bank station by noon.',
         'segments': [controlled_segment('ferry_1',
             'At ten, Iona stood at the ferry with a stamped permit in her hand and a boat ready at the landing. She showed the permit to the watchman. He inspected it, lifted the chain across the landing, and she carried the parcel aboard. At eleven the ferry crossed with the parcel. The account does not say whether a permit is indispensable, whether exceptions are allowed, or what happens when a boat is not ready. A causal influence of permission on departure is suggested by the exchange, but a universal policy is not recorded.'),
             controlled_segment('ferry_2',
             'The controlled delivery system has this rule: a parcel crossing on the ferry before noon is always recorded as delivered at the far-bank station, and a parcel that does not cross before noon is not recorded there. No other route or recording failure is possible in this system. Today the parcel was recorded as delivered. At twelve Iona announced that she believed the permit had guaranteed success. Her later announcement is a belief about the completed trip, not a prior instruction to the ferry.'),
             controlled_segment('ferry_3',
             'For this diagnostic, the only varying inputs to whether the parcel crosses are permit possession and boat readiness at ten. The omitted departure rule is some fixed deterministic Boolean function of these two inputs. Its factual output with both inputs present is crossing. The missing three configurations are not disclosed; investigators must not infer them from chronology or Iona\'s claim. Permission and physical departure are different events even if an analyst chooses to model their combined consequence.')],
         'queries': [
             {'id':'q1','question':'Remove Iona\'s permit at ten, keeping the boat ready. Is the parcel recorded as delivered by noon?', 'gold':[0,1], 'changing':None},
             {'id':'q2','question':'Make the boat not ready at ten while Iona still has her permit. Is the parcel recorded as delivered by noon?', 'gold':[0,1], 'changing':None},
             {'id':'q3','question':'Prevent the parcel from crossing before noon, replacing its crossing mechanism. Is it recorded as delivered by noon?', 'gold':[0], 'changing':True},
             {'id':'q4','question':'Set permit possession and boat readiness at ten to their observed present values. Is the parcel recorded as delivered by noon?', 'gold':[1], 'changing':False}],
         'reference': {'variables':['permit','boat_ready','crossing','recorded'], 'factual':[1,1,1,1],
                       'hidden_generating_equations':{'crossing':'permit AND boat_ready','recorded':'crossing'},
                       'compatible_family':'All 8 Boolean functions on permit/boat with f(1,1)=1; recorded=crossing.',
                       'scope':'Latent generating equation is not a uniquely defensible narrative answer; reference sets use declared missing information.',
                       'independent_human_verification':False}},
        {'id': 'five_kings', 'kind': 'natural_uncertain',
         'outcome': 'Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1.',
         'endpoint_code':110, 'queries':[], 'reference': {'gold':None, 'independent_human_verification':False}}
    ]
    original = json.loads((root/'.private/v2/five_kings_packet.json').read_text())
    # Outcome-time coverage is selected before inference, independently of causes.
    # Equal character budgets over three temporal strata prevent lexical matching
    # from silently excluding the endpoint. Retain source-native scene units.
    selected = []
    episodes = sorted({s['episode'] for s in original['segments']})
    for group in (episodes[:4], episodes[4:7], episodes[7:]):
        pool = [s for s in original['segments'] if s['episode'] in group]
        selected.extend(retrieve(pool, cases[2]['outcome'], max_chars=2600))
    if not selected:
        raise RuntimeError('No accessible natural-narrative source packet')
    cases[2]['segments'] = selected
    cases[2]['acquisition'] = {'source_packet_sha256':original['packet_sha256'],
        'method':'Existing BM25, outcome text only; 2600 characters each for early/middle/late episode strata (4/3/3 episodes); no handpicked causes',
        'corpus_segments':len(original['segments']), 'selected_segments':len(selected),
        'source_validity':'Unofficial transcripts; dependent source records; fidelity unadjudicated'}
    public = []
    for c in cases:
        p = packet(c.pop('segments')); private = root/'.private/v3'/ (c['id']+'_packet.json')
        atomic_json(private, p)
        c['packet_sha256'] = p['packet_sha256']
        c['passages'] = [{k:v for k,v in s.items() if k!='text'} for s in p['segments']]
        if c['kind'].startswith('controlled'):
            c['controlled_text'] = p['segments']
        public.append(c)
    cfg = {'version':3,'development_only':True,'base_commit':'d639553', 'created':datetime.now(timezone.utc).isoformat(),
        'run':RUN,'cases':public,'arms':{'A':20000,'B_increment':3000,'C':24000},
        'global_generated_token_cap':150000,'inference_service_seconds':7200,'seed':3701,
        'maximum_cases':12,'initial_cases':3,'expansion':'Only after all three pass the end-to-end gate; optional, no search for significance',
        'old_test_set_used':False,'review':'pending','packet_access':'identical within case',
        'gold_access':'references/gold excluded from construction, repair, semantic review and query alignment'}
    atomic_json(dest, cfg)
    paths = ['src/got_war/v3/core.py','src/got_war/v3/pipeline.py','src/got_war/v3/study.py','docs/V3_METHOD.md','configs/v3_development.json']
    atomic_json(run/'pre_inference_freeze.json', {'at':datetime.now(timezone.utc).isoformat(),
        'hashes':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}})
    return cfg


class ScopedGenerator(Generator):
    def __init__(self, root, case, arm, cap):
        super().__init__(root, budget=Budget(root,'budget_v3.json'),results_dir='results/v3',prompt_dir='.private/prompts_v3')
        self.prefix = 'v3_'+case+'_'+arm+'_'; self.cap = cap
        from transformers import AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.config['primary'], revision=self.config['revision'],
            local_files_only=True,cache_dir=str(self.root/'.cache/huggingface/hub'))

    def call(self, role, prompt, max_tokens=2048, seed=3701, temperature=.2, schema=None, thinking=False):
        used = self.db.execute('SELECT COALESCE(SUM(output_tokens),0) FROM jobs WHERE role LIKE ?', (self.prefix+'%',)).fetchone()[0]
        count = len(self.tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
            tokenize=True,add_generation_prompt=True,enable_thinking=False))
        allowance = self.config['max_model_len']-count-32
        limit = min(max_tokens, allowance, self.cap-used)
        if limit < 512:
            raise RuntimeError('Case/context token allowance exhausted: '+self.prefix+' used='+str(used)+' prompt='+str(count))
        # Global accounting includes server interrupted-token counters and a
        # conservative 2-context reserve inherited from Generator.
        return super().call(self.prefix+role,prompt,limit,seed,temperature,schema,False)


def evaluate_queries(gen, case, result, folder, alignment=None):
    if not case['queries']:
        # Natural queries are generated from the newly discovered representation;
        # these are model consequences, not source-validated gold outcomes.
        rep = result['representation']; choices = [v for v in rep['variables'] if v['id'] != rep['outcome']]
        qs = [{'id':'explore_'+v['id'],'do':{v['id']:next(x for x in v['domain'] if x != v['factual'])},'target':rep['outcome'],'abstain':False,
               'reason':'Deterministic domain contrast for generated variable; no literary reference answer'} for v in choices[:4]]
        alignment = {'queries':qs}
    elif alignment is None:
        alignment = align_queries(gen, case, result['representation'], folder)
    responses = []
    for q in alignment['queries']:
        try:
            if q.get('abstain'):
                answer = {'status':'alignment_abstention','values':[],'identified':False}
            else:
                if q['target'] != result['representation']['outcome']:
                    raise ValueError('Alignment changed outcome')
                answer = query(result['representation'],result['family'],q['do'],q['target'])
            check = (None if q.get('abstain') else verify_reported_result(
                result['representation'], result['family'], q['do'], answer, q['target']))
            responses.append({'id':q['id'],'alignment':q,'result':answer,'execution_check':check})
        except Exception as error:
            responses.append({'id':q['id'],'alignment':q,'error':str(error),'result':{'status':'unavailable','values':[],'identified':False}})
    result['queries'] = responses
    atomic_json(Path(folder)/'evaluated.json',result)
    return result, alignment


def run(root):
    root = Path(root); cfg = json.loads((root/'configs/v3_development.json').read_text()); run = root/'runs'/RUN
    Budget(root,'budget_v3.json').check(heavy=True)
    records = []
    for case_full in cfg['cases']:
        # Explicit access firewall: gold/reference never enter pipeline objects.
        case = {k:v for k,v in case_full.items() if k not in ('reference','controlled_text','passages')}
        case['queries'] = [{'id':q['id'],'question':q['question']} for q in case['queries']]
        packet_data = json.loads((root/'.private/v3'/(case['id']+'_packet.json')).read_text())
        if packet(packet_data['segments'])['packet_sha256'] != case['packet_sha256'] or packet_data['packet_sha256'] != case['packet_sha256']:
            raise ValueError('Frozen source packet content/hash mismatch')
        a = None; a_alignment = None
        for arm in ('A','B','C'):
            folder = run/case['id']/arm; folder.mkdir(parents=True,exist_ok=True)
            if (folder/'evaluated.json').exists():
                done = json.loads((folder/'evaluated.json').read_text()); records.append(done)
                if arm=='A':
                    raw=folder/'final.json'; a=json.loads(raw.read_text()) if raw.exists() else None
                    align=folder/'query_alignment.json';a_alignment=json.loads(align.read_text()) if align.exists() else None
                continue
            gen = ScopedGenerator(root,case['id'],arm,{'A':20000,'B':3000,'C':24000}[arm]); start=time.monotonic()
            try:
                if arm=='A':
                    a = V2Adapter(root,gen,case,packet_data,folder).build()
                    rep,fam=v2_family(a['records'])
                    done={'case':case['id'],'arm':'A','status':'executable','representation':rep,'family':fam,
                          'base_model_sha256':fingerprint(a['records'][0]['model']),'packet_sha256':packet_data['packet_sha256']}
                    done,a_alignment=evaluate_queries(gen,case,done,folder)
                elif arm=='B':
                    if a is None:
                        raise RuntimeError('Inherited A synthesis failure; presentation cannot change or manufacture its model')
                    done=presentation(gen,case,packet_data,a,folder)
                    done,_=evaluate_queries(gen,case,done,folder,a_alignment)
                else:
                    done=MechanismFirst(gen,case,packet_data,folder).run()
                    done,_=evaluate_queries(gen,case,done,folder)
            except Exception as error:
                done={'case':case['id'],'arm':arm,'status':'failed','error':type(error).__name__+': '+str(error),
                      'packet_sha256':packet_data['packet_sha256'],'elapsed_seconds':time.monotonic()-start}
                # A failure after a saved model does not erase that partial result.
                partial=folder/'final.json'
                if partial.exists():done['partial_record']='final.json'
                atomic_json(folder/'evaluated.json',done)
            records.append(done)
            atomic_json(run/'progress.json',{'completed':len(records),'total':9,
                'records':[{'case':r['case'],'arm':r['arm'],'status':r['status']} for r in records], 'at':datetime.now(timezone.utc).isoformat()})
            print('V3_DONE',case['id'],arm,done['status'],flush=True)
    atomic_json(run/'comparison.json',{'records':records,'planned_cases':3,'development_only':True})
    # Completion closes this bounded pilot, not the old campaigns or the pod.
    (run/'INFERENCE_DONE').write_text(datetime.now(timezone.utc).isoformat()+'\n')


def component_scores(config, records, requests=()):
    """Post-inference analysis only; gold never enters generation/repair feedback."""
    cells=[];lookup={(r['case'],r['arm']):r for r in records}
    for case in config['cases']:
        for arm in ('A','B','C'):
            record=lookup.get((case['id'],arm),{})
            attempted=record.get('status') not in (None,'unrun_infrastructure')
            gold={q['id']:q for q in case['queries']}
            answers={q['id']:q.get('result',{}) for q in record.get('queries',[])}
            by_category={name:[] for name in ('all','changing','preserving','underidentified')}
            confident_errors=[];coverage=[]
            for ident,q in gold.items():
                a=answers.get(ident,{})
                valid=a.get('status') in ('exhaustive_set','certified_set','observed_sample') and bool(a.get('values'))
                correct=valid and set(a['values'])==set(q['gold'])
                by_category['all'].append(int(correct));coverage.append(int(valid))
                category='underidentified' if len(q['gold'])>1 else 'changing' if q['changing'] else 'preserving'
                by_category[category].append(int(correct))
                confident_errors.append(int(bool(a.get('identified')) and (len(q['gold'])>1 or not correct)))
            rate=lambda xs:sum(xs)/len(xs) if xs and attempted else None
            gate=record.get('display_gate',{});rep=record.get('representation',{});audit=record.get('audit',{})
            edgeids={e['id'] for e in rep.get('edges',[])}
            reviews=[r for r in audit.get('records',[]) if r.get('id') in edgeids]
            usage=[r for r in requests if r.get('role','').startswith('v3_'+case['id']+'_'+arm+'_')]
            cells.append({'case':case['id'],'arm':arm,'status':record.get('status','unrun'),
                'planned_queries':len(gold),'attempted':attempted,
                'set_accuracy':rate(by_category['all']),'changing_accuracy':rate(by_category['changing']),
                'preserving_accuracy':rate(by_category['preserving']),'underidentified_set_accuracy':rate(by_category['underidentified']),
                'unsupported_identification_rate':rate(confident_errors),'answer_coverage':rate(coverage),
                'synthesis_failed':int(record.get('status')=='failed') if attempted else None,
                'variables':len(rep.get('variables',[])) if attempted else None,
                'variable_temporal_flags':audit.get('variable_flags') if attempted else None,
                'displayed_edges':len(gate.get('displayed_edges',[])) if attempted else None,
                'formal_contradictions':sum(c['status']=='contradicted_by_candidate' for c in gate.get('formal_claims',[])) if attempted else None,
                'source_review_support_fraction':sum(r.get('source_to_description') in ('supported','inferred') for r in reviews)/len(reviews) if reviews else None,
                'source_review_is_independent':False,'functional_ground_truth_agreement':None,
                'human_variable_meaning_quality':None,'human_mechanism_grounding':None,
                'presentation_preserved_model':record.get('base_model_sha256')==record.get('after_model_sha256') if arm=='B' and record.get('after_model_sha256') else None,
                'revisions':len(record.get('revisions',[])) if attempted else None,
                'tokens':sum(r.get('output_tokens',0) for r in usage),'request_seconds':sum(r.get('elapsed_seconds',0) for r in usage),
                'request_failures':sum(bool(r.get('error')) for r in usage),
                'interpretation':'Development only; failed attempts score zero on planned controlled questions. Unrun cells are unavailable. Same-model judgments are not ground truth; functional schema alignment needs independent review.'})
    return {'cells':cells,'planned_cases':len(config['cases']),'no_composite_score':True,
            'uncertainty_intervals':'Not estimated: three development cases, and current inference unrun.',
            'B_cost_policy':'A cost is shared; B token/time columns are incremental and must be added to A for total cost.'}


def score(root):
    root=Path(root);config=json.loads((root/'configs/v3_development.json').read_text());run=root/'runs'/RUN
    records=[json.loads(p.read_text()) for p in run.glob('*/[ABC]/evaluated.json')]
    log=run/'requests.jsonl';requests=[json.loads(s) for s in log.read_text().splitlines()] if log.exists() else []
    result=component_scores(config,records,requests)
    atomic_json(root/'results/v3/component_summary.json',result)
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','score']);p.add_argument('--root',default='.')
    args=p.parse_args();globals()[args.action](args.root)
