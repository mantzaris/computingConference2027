"""Sentence-level trace audits; model judgments are not independent verification."""
import json,re
from pathlib import Path
from .generation import Generator
from .budget import atomic_json


def run(root):
    gen=Generator(root)
    for file in sorted((gen.run/'application').glob('*/alternative_*.json')):
        destination=file.with_name('explanation_audit_'+file.stem.split('_')[-1]+'.json')
        if destination.exists():continue
        record=json.loads(file.read_text())
        # Avoid consuming the audit artifacts themselves on resume.
        if 'model' not in record:continue
        text=record['explanation'].get('text','')
        trace={'outcome_definition':record['model']['outcome_definition'],
               'variables':[{k:n.get(k) for k in ('id','label','definition','observed','reference','reference_meaning','assumptions')} for n in record['model']['nodes']],
               'attribution':record['attribution'],'paths':record['evidence_priority']['paths'],
               'queries':record['queries'],'model_assumptions':record['model']['assumptions']}
        if record.get('explanation_input_trace'):trace=record['explanation_input_trace']
        prompt='Audit EVERY sentence of this generated explanation against the execution trace only. Decompose the entire explanation into contiguous verbatim quote fields; do not silently omit a sentence. Return each sentence ONCE, at most EIGHT claims total; never repeat a claim. For each quote, return supported, unsupported, or unverifiable with a reason of at most 20 words and at most three trace fields. Numerical values must match the trace. A path allocation is NOT an individual event or edge contribution. Tied largest contributions do not establish a unique strongest path. Causal claims must describe frozen model consequences, and an assumed literary counterfactual must never be asserted as established historical fact. Return {"claims":[{"quote":"verbatim sentence or clause","verdict":"supported OR unsupported OR unverifiable","trace_fields":["field path"],"reason":"brief"}]}. This is an automatic same-model consistency audit, not human review or independent causal validation.\nEXPLANATION: '+text+'\nTRACE: '+json.dumps(trace)
        try:
            response=gen.call('application_explanation_audit',prompt,3072,2027)
            covered=set();invalid=[]
            for claim in response.get('claims',[]):
                quote=claim.get('quote','');start=text.find(quote) if quote else -1
                if start<0:invalid.append(quote[:120]);continue
                covered.update(range(start,start+len(quote)))
            relevant={i for i,c in enumerate(text) if c.isalnum()}
            coverage=len(relevant&covered)/max(1,len(relevant))
            structured=record.get('explanation_checks',{})
            structured_pass=structured.get('structured_numeric_claims',False) and structured.get('path_ids',False)
            passed=bool(relevant) and coverage==1 and not invalid and structured_pass and all(c.get('verdict')=='supported' for c in response.get('claims',[]))
            result={'claims':response.get('claims',[]),'text_coverage':coverage,'nonverbatim_quotes':invalid,
                    'automatic_check_passed':passed,'structured_check_passed':structured_pass,
                    'display_status':'automatic consistency check passed; independent review still required' if passed else 'VERIFICATION FAILURE: withhold generated prose; use numerical trace and inspect flagged claims',
                    'independence':'Same primary LLM; no human or independent semantic verification.'}
        except Exception as e:
            result={'automatic_check_passed':False,'display_status':'VERIFICATION FAILURE: explanation audit did not complete','error':str(e)}
        atomic_json(destination,result)
        print(file.parent.name,file.stem,result['display_status'],flush=True)
