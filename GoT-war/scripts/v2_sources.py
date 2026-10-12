"""Bounded public TV transcript acquisition; full text stays private/local."""
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/v2';RAW.mkdir(parents=True,exist_ok=True)
PRIVATE=ROOT/'.private/v2';PRIVATE.mkdir(parents=True,exist_ok=True)
MANIFEST=ROOT/'data/manifests/v2_sources.json'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    started=time.monotonic();sources=[];segments=[];failures=[]
    home='https://screenscripts.com/game-of-thrones/'
    response=requests.get(home,timeout=30);response.raise_for_status()
    (RAW/'index.html').write_bytes(response.content)
    soup=BeautifulSoup(response.content,'html.parser')
    links=sorted({urljoin(home,a['href']) for a in soup.find_all('a',href=True) if re.search(r'/s01e\d\d_',a['href'])})
    if len(links)!=10:raise RuntimeError('Expected the ten Season 1 episode pages, found '+str(len(links)))
    for url in links:
        if time.monotonic()-started>3600:raise RuntimeError('Bounded source acquisition timeout')
        episode=re.search(r's01e\d\d',url).group();ident='screen_'+episode
        raw=RAW/(ident+'.html');access=datetime.now(timezone.utc).isoformat()
        try:
            if raw.exists():data=raw.read_bytes();status=200
            else:
                page=requests.get(url,timeout=30);status=page.status_code;page.raise_for_status();data=page.content;raw.write_bytes(data)
            parsed=BeautifulSoup(data,'html.parser');scenes=parsed.select('.scene-container')
            if not scenes:raise ValueError('No structured scene containers')
            text_parts=[];local=[];offset=0
            for scene in scenes:
                lines=[]
                for line in scene.find_all(id=re.compile(r'^S\d+L\d+$')):
                    for button in line.find_all('button'):button.decompose()
                    text=' '.join(line.stripped_strings)
                    if text:lines.append((line['id'],text))
                # Segment by scene, splitting long scenes with a single-line overlap.
                chunks=[];current=[];length=0
                for line in lines:
                    if current and length+len(line[1])>6500:
                        chunks.append(current);current=current[-1:];length=sum(len(x[1])+1 for x in current)
                    current.append(line);length+=len(line[1])+1
                if current:chunks.append(current)
                for chunk_index,chunk in enumerate(chunks):
                    text='\n'.join(x[1] for x in chunk);sid=ident+'_'+scene['id'].lower()+'_'+str(chunk_index)
                    local.append({'id':sid,'source_id':ident,'episode':episode,'scene':scene['id'],'first_line':chunk[0][0],'last_line':chunk[-1][0],
                        'start':offset,'end':offset+len(text),'text':text,'source_type':'unofficial dialogue/stage-direction transcription',
                        'dependence_cluster':'aired_'+episode,'url':url+'#'+chunk[0][0]})
                    text_parts.append(text);offset+=len(text)+2
            normalized='\n\n'.join(text_parts)
            sources.append({'id':ident,'url':url,'title':parsed.title.get_text() if parsed.title else episode,'episode':episode,
                'continuity':'HBO aired television; transcription fidelity not independently verified','source_type':'unofficial attributed dialogue and stage-direction transcription',
                'publisher_family':'ScreenScripts','dependence_cluster':'aired_'+episode,'accessed_at':access,'http_status':status,
                'html_sha256':sha(data),'normalized_sha256':sha(normalized.encode()),'characters':len(normalized),'segments':len(local),
                'license_note':'Publicly accessible; no full-text redistribution permission inferred. Raw HTML and parsed text excluded from Git.',
                'limitations':['Speaker/scene annotations are supplied by the transcription site, not independently authenticated.','Dialogue may report beliefs, deception or retrospective claims; its content is not automatically an established event.','Other summaries/transcriptions of this episode are dependent evidence.']})
            segments.extend(local)
            print(episode,'segments',len(local),'characters',len(normalized),flush=True)
        except Exception as error:
            failures.append({'url':url,'accessed_at':access,'error':type(error).__name__+': '+str(error)})
        manifest={'version':2,'scope':'Ten first-season aired episodes for the Five Kings flagship; no manually selected story causes.',
            'acquisition_limits':{'max_episode_pages':10,'max_wall_seconds':3600,'per_request_timeout_seconds':30},
            'sources':sources,'failures':failures,'candidate_exclusions':[{'url':'https://www.tv-calling.com/scripts/TV_Dramas/Game_Of_Thrones_1x01.pdf','reason':'Pilot draft requires aired-version concordance; excluded rather than mixing draft and aired continuity.'}],
            'independent_corroboration_claimed':False}
        MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
        (PRIVATE/'five_kings_segments.json').write_text(json.dumps(segments,ensure_ascii=False)+'\n')
    packet={'sources':sources,'segments':segments,'packet_sha256':sha(json.dumps(segments,sort_keys=True,ensure_ascii=False).encode())}
    (PRIVATE/'five_kings_packet.json').write_text(json.dumps(packet,ensure_ascii=False)+'\n')
    print('Frozen',len(sources),'sources',len(segments),'segments; full text private')


if __name__=='__main__':main()
