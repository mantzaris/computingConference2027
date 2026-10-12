"""Archive primary bibliographic metadata and the official conference template."""
import hashlib, json, re, zipfile, io
from pathlib import Path
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 ('conference','https://saiconference.com/Computing/CallforPapers'),
 ('bynum','https://aclanthology.org/2025.emnlp-main.107/'),
 ('shojaee','https://proceedings.iclr.cc/paper_files/paper/2025/hash/28df8e730c054c5331855fd4d5403ba9-Abstract-Conference.html'),
 ('li','https://aclanthology.org/2025.wnu-1.10/'),
 ('koupaee','https://aclanthology.org/2025.acl-long.1269/'),
 ('yamin','https://proceedings.iclr.cc/paper_files/paper/2026/hash/98741856b327ec2f9503179398da662f-Abstract-Conference.html'),
 ('wilmot','https://arxiv.org/abs/2605.02475'),
 ('wang','https://proceedings.mlr.press/v130/wang21b.html'),
 ('jung','https://proceedings.mlr.press/v162/jung22a.html'),
 ('terminassian','https://proceedings.mlr.press/v202/ter-minassian23a.html'),
 ('witter','https://proceedings.mlr.press/v306/witter26a.html'),
 ('pearl','https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12065'),
 ('graphviz','https://graphviz.org/docs/layouts/dot/')]
manifest=[];bib=[];raw=ROOT/'data/raw/references';raw.mkdir(parents=True,exist_ok=True)
session=requests.Session()
for key,url in SOURCES:
    try:
        r=session.get(url,timeout=40);r.raise_for_status();(raw/(key+'.html')).write_text(r.text)
        soup=BeautifulSoup(r.text,'html.parser');meta={}
        for m in soup.find_all('meta'):
            name=m.get('name','');value=m.get('content','')
            if name.startswith('citation_'):meta.setdefault(name,[]).append(value)
        record={'id':key,'url':url,'accessed':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(r.content).hexdigest(),'title':soup.title.get_text(strip=True) if soup.title else soup.find('h1').get_text(strip=True),'metadata':meta,'status':r.status_code}
        text=soup.get_text(' ',strip=True);record['abstract_preview']=text[text.find('Abstract'):text.find('Abstract')+1600] if 'Abstract' in text else ''
        for tag in soup.find_all(['pre','code','textarea']):
            t=tag.get_text()
            if re.search(r'@(?:article|inproceedings|misc)',t,re.I):bib.append(t);record['bibtex_source']='embedded';break
        if key in ('bynum','li','koupaee'):
            br=session.get(url.rstrip('/')+'.bib',timeout=20)
            if br.ok:bib.append(br.text);record['bibtex_source']=br.url
        manifest.append(record);print(key,'OK',flush=True)
    except Exception as e:manifest.append({'id':key,'url':url,'error':str(e)});print(key,str(e),flush=True)
(ROOT/'docs/reference_audit.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT/'paper/verified_metadata.bib').write_text('\n\n'.join(dict.fromkeys(bib)))
url='https://saiconference.com/Downloads/SAI_Paper_Format_Latex_Conference.zip'
try:
 r=session.get(url,timeout=60);r.raise_for_status();(raw/'conference_template.zip').write_bytes(r.content)
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  for name in z.namelist():
   if Path(name).suffix in ('.cls','.sty','.bst','.tex','.pdf') and not name.startswith('__MACOSX'):
    dest=ROOT/'paper/template'/Path(name).name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
 (ROOT/'paper/template/SOURCE.json').write_text(json.dumps({'url':url,'sha256':hashlib.sha256(r.content).hexdigest(),'accessed':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
 print('TEMPLATE OK')
except Exception as e:print('TEMPLATE',str(e))
