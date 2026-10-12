"""Post-hoc literal coverage check for generated parenthetical personal aliases.

Absence is a review flag, not a proof that a historical identity is false.
This does not introduce an event, parent, structural equation, or human label.
"""
import json,re,unicodedata
from pathlib import Path

root=Path(__file__).resolve().parents[1]
run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
def normalized(value):return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',value).casefold()))
findings=[];checked=[]
for folder in sorted((run/'application').iterdir()):
    files=sorted(folder.glob('alternative_*.json'))
    if not files:continue
    record=json.loads(files[0].read_text())
    packet=json.loads((root/'.private/packets'/(folder.name+'.json')).read_text())
    text=normalized(' '.join(s['text'] for s in packet['segments']))
    for node in record['model']['nodes']:
        for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*\(([^)]+)\)',node['definition']):
            name,alias=match.groups();present=normalized(name) in text
            row={'case':folder.name,'node_id':node['id'],'generated_name':name,'parenthetical_alias':alias,
                 'literal_name_present_in_frozen_packet':present,'packet_sha256':packet['packet_sha256'],
                 'model_event_assessment':node.get('event_assessment'),'source_ids':[c['segment_id'] for c in node.get('citations',[])],
                 'interpretation':'Post-hoc literal coverage flag only. An absent name is not a verified source identity; this does not establish the true alias or constitute human adjudication.'}
            checked.append(row)
            if not present:findings.append(row)
result={'protocol':'Post-hoc generic parenthetical-name coverage scan prompted by an observed alias discrepancy; no inference or model edits.',
        'checked':checked,'findings':findings,'independent_human_review':False,
        'scope':'The scan is not a comprehensive semantic audit and its selected names are not an independent evaluation sample.'}
(root/'results/source_alias_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print('Parenthetical names checked',len(checked),'absent',len(findings))
