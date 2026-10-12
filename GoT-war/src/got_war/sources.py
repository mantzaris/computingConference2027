"""Traceable, television-only episode plot corpus; raw text is not distributed."""
import hashlib, json, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup

# Episode selection defines a corpus, never a graph or causal mechanism.
EPISODES = [
 ('s01e01','Winter Is Coming'),('s01e02','The Kingsroad'),
 ('s01e03','Lord Snow'),('s01e04','Cripples, Bastards, and Broken Things'),
 ('s01e05','The Wolf and the Lion'),('s01e06','A Golden Crown'),
 ('s01e07','You Win or You Die'),('s01e08','The Pointy End'),
 ('s01e09','Baelor'),('s01e10','Fire and Blood (Game of Thrones)'),
 ('s02e01','The North Remembers'),('s02e02','The Night Lands'),
 ('s02e03','What Is Dead May Never Die'),('s02e04','Garden of Bones'),
 ('s03e05','Kissed by Fire'),('s05e03','High Sparrow (Game of Thrones)'),
 ('s05e06','Unbowed, Unbent, Unbroken'),('s05e10',"Mother's Mercy"),
 ('s06e02','Home (Game of Thrones)'),('s06e04','Book of the Stranger'),
 ('s06e05','The Door (Game of Thrones)'),('s06e07','The Broken Man'),
 ('s06e09','Battle of the Bastards'),('s06e10','The Winds of Winter (Game of Thrones)'),
 ('s07e01','Dragonstone (Game of Thrones)'),('s07e02','Stormborn'),
 ('s07e03',"The Queen's Justice"),('s07e04','The Spoils of War (Game of Thrones)'),
 ('s07e05','Eastwatch'),('s07e07','The Dragon and the Wolf'),
 ('s08e04','The Last of the Starks'),('s08e05','The Bells (Game of Thrones)')]


def sha(data):
    return hashlib.sha256(data if isinstance(data,bytes) else data.encode()).hexdigest()


def extract_plot(html):
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup.select('sup.reference, span.mw-editsection'): tag.decompose()
    marker=soup.find(id='Plot')
    if not marker: raise ValueError('No explicit Plot section; refusing whole-page/book contamination')
    heading=marker if marker.name=='h2' else marker.find_parent('h2')
    if heading is None: heading=marker
    sections=[]; scene='Plot'
    for tag in heading.find_all_next(['h2','h3','p']):
        if tag.name=='h2': break
        if tag.name=='h3': scene=tag.get_text(' ',strip=True).replace('[ edit ]','').strip();continue
        text=re.sub(r'\s+',' ',tag.get_text(' ',strip=True)).strip()
        if len(text)>45: sections.append((scene,text))
    if not sections: raise ValueError('Empty plot')
    permanent=soup.select_one('#t-permalink a')
    return sections, permanent.get('href') if permanent else None


def build(root):
    root=Path(root); raw=root/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    manifest=[];segments=[];failures=[]
    session=requests.Session(); session.headers['User-Agent']='GoT-war-research/0.1 (noncommercial reproducibility study)'
    for episode,title in EPISODES:
        url='https://en.wikipedia.org/wiki/'+quote(title.replace(' ','_'),safe='(),')
        file=raw/(episode+'.html')
        try:
            if file.exists(): html=file.read_text();status=200
            else:
                response=session.get(url,timeout=40);status=response.status_code;response.raise_for_status()
                html=response.text;file.write_text(html);time.sleep(.3)
            passages,permanent=extract_plot(html)
            normalized='\n\n'.join(t for _,t in passages)
            (raw/(episode+'.txt')).write_text(normalized)
            source={'source_id':episode,'url':url,'permanent_url':permanent,'title':title,'episode':episode,
                    'continuity':'HBO television Game of Thrones','source_type':'secondary episode plot summary',
                    'access_utc':datetime.now(timezone.utc).isoformat(),'html_sha256':sha(html),'text_sha256':sha(normalized),
                    'license_notes':'Wikipedia contributors; CC BY-SA, attribution required; raw text excluded from release.',
                    'offset_space':'Unicode character offsets in normalized plot-only text','http_status':status}
            manifest.append(source);offset=0
            for index,(scene,text) in enumerate(passages):
                seg={'id':episode+'_p%02d'%index,'source_id':episode,'start':offset,'end':offset+len(text),
                     'text':text,'scene':scene,'statement_time':episode,'audience_revelation_time':episode,
                     'story_event_time':'unresolved; must be annotated during synthesis',
                     'cluster_id':sha(re.sub(r'\W+',' ',text.lower()))[:16]}
                segments.append(seg);offset+=len(text)+2
            print(episode,len(passages),len(normalized),flush=True)
        except Exception as e:
            failures.append({'source_id':episode,'url':url,'error':str(e)});print('FAILED',episode,str(e),flush=True)
        (root/'data/manifests/sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (root/'data/manifests/acquisition_failures.json').write_text(json.dumps(failures,indent=2)+'\n')
    # Near duplicates are linked by lexical shingles, conservatively without claiming independence.
    for i,s in enumerate(segments):
        words=s['text'].lower().split();shingles=set(tuple(words[k:k+4]) for k in range(max(0,len(words)-3)))
        for prior in segments[:i]:
            pwords=prior['text'].lower().split();other=set(tuple(pwords[k:k+4]) for k in range(max(0,len(pwords)-3)))
            if shingles and len(shingles&other)/max(1,len(shingles|other))>.7:
                s['cluster_id']=prior['cluster_id'];break
    (root/'data/derived/segments.private.jsonl').write_text(''.join(json.dumps(s,ensure_ascii=False)+'\n' for s in segments))
    public=[{k:v for k,v in s.items() if k!='text'} for s in segments]
    (root/'data/derived/segment_index.json').write_text(json.dumps(public,indent=2)+'\n')
    freeze={'version':'tv-plot-v1','sources':len(manifest),'segments':len(segments),'manifest_sha256':sha(json.dumps(manifest,sort_keys=True)),
            'segments_sha256':sha(json.dumps(segments,sort_keys=True)),'continuity':'HBO television only',
            'primary_material_status':'HBO synopsis and Fandom access attempts failed; episode summaries explicitly secondary.'}
    (root/'data/manifests/corpus_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    return freeze


if __name__=='__main__':
    import sys
    print(build(sys.argv[1] if len(sys.argv)>1 else '.'))
