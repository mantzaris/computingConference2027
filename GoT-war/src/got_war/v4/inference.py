"""Auditable source passes on the project endpoint, with token/runtime records."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import requests

from ..budget import Budget, atomic_json

INSTRUCTION = '''Read only the supplied aired-television passages. Discover event/state propositions and substantive directional mechanisms relevant to the specified outcome. Do not use model memory as evidence. Separate event, report, belief, plan and execution. Later reports may concern earlier events but cannot themselves cause them. No prescribed graph or minimum size.
Return JSON with events [{label,definition,event_time,statement_time,kind,evidence:[passage_id]}], mechanisms [{parent_meaning,child_meaning,label,process,conditions,qualifications,evidence:[{passage_id,supports}],gaps,alternative}], joint_mechanisms [{child_meaning,interaction,unidentified_behavior}], retrieval_questions, contradictions. Explain how actors/information/resources/decisions connect, not generic 'influences'. Do not invent exact truth-table entries. A factor helping is not universal necessity or sufficiency. Multiple passages can support a mechanism; state the inferential bridge. Explicitly retract tempting chronology-only connections. Use at most 6 event propositions and 5 candidate mechanisms PER PASS, not a case-wide limit. Keep each description concise and finish the JSON. These are fallible hypotheses, not independent source adjudication.'''


def passes(root, case_id):
    root=Path(root);b=Budget(root,'budget_v4.json');b.check(heavy=True)
    cfg=json.loads((root/'configs/v4_campaign.json').read_text())
    case=next(c for c in cfg['cases'] if c['id']==case_id)
    packet=json.loads((root/'.private/v4'/case_id/'construction_packet.json').read_text())
    folder=b.run/'qwen'/case_id;folder.mkdir(parents=True,exist_ok=True)
    batches=[];batch=[];chars=0
    for s in packet['segments']:
        if batch and chars+len(s['text'])>18000:
            batches.append(batch);batch=[];chars=0
        batch.append(s);chars+=len(s['text'])
    if batch:batches.append(batch)
    # The campaign bounds use output counts across all completed and interrupted calls.
    for i,batch in enumerate(batches):
        dest=folder/('pass_%02d.json'%i)
        repair=False
        if dest.exists():
            old=json.loads(dest.read_text())
            if old.get('parsed') is not None:continue
            dest=folder/('pass_%02d_repair.json'%i)
            if dest.exists():continue
            repair=True
        b.check(heavy=True)
        window=json.loads((b.run/'service_window.json').read_text())
        if datetime.now(timezone.utc)>=datetime.fromisoformat(window['deadline']):raise RuntimeError('Service window over')
        prompt=INSTRUCTION+'\nOUTCOME: '+case['outcome']+'\nPASS '+str(i+1)+'/'+str(len(batches))+'\n'+ '\n\n'.join('['+s['id']+']\n'+s['text'] for s in batch)
        body={'model':'Qwen/Qwen3-14B-AWQ','messages':[{'role':'system','content':'Produce grounded JSON; no outside facts.'},{'role':'user','content':prompt}],
              'max_tokens':4500,'temperature':0.2,'seed':4701+i,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_object'}}
        started=time.monotonic();atomic_json(folder/('prompt_%02d%s.json'%(i,'_repair' if repair else '')),body)
        try:
            r=requests.post('http://127.0.0.1:8765/v1/chat/completions',json=body,timeout=180);r.raise_for_status()
            raw=r.json();text=raw['choices'][0]['message']['content']
            try:parsed=json.loads(text)
            except ValueError:parsed=None
            record={'case':case_id,'passage_ids':[s['id'] for s in batch],'request_sha256':hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),
                'raw':raw,'parsed':parsed,'elapsed_seconds':time.monotonic()-started,'at':datetime.now(timezone.utc).isoformat(),
                'route':'Qwen3-14B-AWQ on authorized RTX 4090','independent_human_review':False}
        except Exception as e:
            record={'case':case_id,'error':type(e).__name__+': '+str(e),'elapsed_seconds':time.monotonic()-started,'passage_ids':[s['id'] for s in batch]}
        atomic_json(dest,record)
        print(case_id,i,record.get('raw',{}).get('usage'),record.get('error','OK'),flush=True)


if __name__=='__main__':
    import sys
    passes(sys.argv[1],sys.argv[2])
