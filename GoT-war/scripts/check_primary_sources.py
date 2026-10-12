"""Record exact primary-access outcomes; supplemental text never silently changes frozen packets."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
items=[('hbo_synopsis','https://www.hbo.com/game-of-thrones/season-1/7-you-win-or-you-die/synopsis','html'),('television_wiki','https://gameofthrones.fandom.com/wiki/Robert%27s_Rebellion','html'),('emmy_s06e09_script','https://www.emmys.com/sites/default/files/Downloads/GameofThronesEP%20609%20-%20Battle%20of%20the%20Bastards%20-%20GOT%20S6.pdf','pdf')]
records=[]
for key,url,extension in items:
 row={'id':key,'url':url,'accessed_at':datetime.now(timezone.utc).isoformat(),'used_in_frozen_generation_packets':False}
 try:
  r=requests.get(url,timeout=40);row.update(status=r.status_code,final_url=r.url,content_type=r.headers.get('Content-Type'),bytes=len(r.content));r.raise_for_status()
  raw=ROOT/'data/raw'/(key+'.'+extension);raw.write_bytes(r.content);row['sha256']=hashlib.sha256(r.content).hexdigest()
  if extension=='pdf' and r.content.startswith(b'%PDF'):
   subprocess.run(['pdftotext','-layout',str(raw),str(raw.with_suffix('.txt'))],check=True)
   row['source_type']='primary published television shooting script; production text may differ from broadcast';row['license_notes']='Copyrighted screenplay; private storage only, short justified audit spans if used.'
  else:row['source_type']='access check only; not automatically accepted as episode material'
 except Exception as e:row['error']=str(e)
 records.append(row);print(key,row.get('status'),row.get('error','downloaded'),flush=True)
(ROOT/'data/manifests/primary_access_audit.json').write_text(json.dumps(records,indent=2)+'\n')
