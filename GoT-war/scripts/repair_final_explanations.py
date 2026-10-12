"""Bounded trace-only prose repair; retain prior text and failed audits.

This can change explanatory prose, never a graph, expression, or numerical result.
Automatic checks are same-model judgments and do not establish source validity.
"""
import copy,json,shutil
from got_war.budget import atomic_json
from got_war.generation import Generator
from got_war.explanation_audit import run as audit

gen=Generator('.')
for file in sorted((gen.run/'application').glob('*/alternative_*.json')):
    record=json.loads(file.read_text())
    if record.get('trace_prose_repair_version')==1:continue
    checks=record.get('explanation_checks',{})
    if checks.get('structured_numeric_claims',False) and checks.get('path_ids',False):continue
    archive=gen.run/'application_before_prose_repair'/file.parent.name/file.name
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():shutil.copy2(file,archive)
    audit_file=file.with_name('explanation_audit_'+file.stem.split('_')[-1]+'.json')
    if audit_file.exists():
        shutil.copy2(audit_file,archive.with_name(audit_file.name));audit_file.unlink()
    attempts=[]
    for attempt in range(2):
        prompt='Repair this explanation against the supplied NUMERICAL TRACE only. Return a JSON object with text (at most 100 words, at most FIVE sentences), numeric_claims (a list with field equal to exactly baseline or full, and the matching numerical value), and path_ids (only actual path IDs). Distinguish a path allocation from a node or edge effect; a tied largest value is not a unique strongest path. Report evidence support separately from allocation. Qualify causal claims as consequences of the frozen model, and say the rules and references are assumptions rather than historical identification or probabilities. Do not invent evidence, improve reported support, or alter any model.\nPRIOR TEXT: '+json.dumps(record['explanation'])+'\nVALIDATION DIAGNOSTIC: '+json.dumps(checks)+'\nTRACE: '+json.dumps(record['explanation_input_trace'])
        try:
            output=gen.call('application_trace_prose_repair',prompt,1536,2037+attempt)
            claims=output.get('numeric_claims',[])
            numeric=bool(claims) and all(c.get('field') in ('baseline','full') and c.get('value')==record['attribution'][c['field']] for c in claims)
            ids=bool(output.get('path_ids')) and set(output['path_ids'])<={'p%d'%(i+1) for i in range(len(record['selection']['paths']))}
            attempts.append({'attempt':attempt,'output':output,'structured_numeric_claims':numeric,'path_ids':ids})
            if numeric and ids:
                record['explanation']=output
                record['explanation_checks']={'structured_numeric_claims':numeric,'path_ids':ids,'free_text_semantic_verification':'pending same-model sentence audit; no human verification'}
                break
            checks={'structured_numeric_claims':numeric,'path_ids':ids}
        except Exception as error:attempts.append({'attempt':attempt,'error':str(error)})
    record['trace_prose_repair_version']=1
    record['trace_prose_repairs']=attempts
    atomic_json(file,record)
audit('.')
