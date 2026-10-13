"""Broad episode acquisition and revisable retrieval; no story mechanisms."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from ..retrieval import retrieve
from ..v3.study import packet


def sha(data):
    return hashlib.sha256(data).hexdigest()


def episode_time(episode, within=0):
    """Episode rank, not elapsed diegetic time; reports need separate event rank."""
    m = re.fullmatch(r's(\d{2})e(\d{2})', episode)
    if not m or not 1 <= int(m[2]) <= 20 or not 0 <= within < 1:
        raise ValueError('Use sNNeNN and a within-episode ordering in [0,1)')
    return int(m[1])*100+int(m[2])+within


def parse_page(data, url, episode):
    soup = BeautifulSoup(data, 'html.parser')
    segments = []
    offset = 0
    for scene in soup.select('.scene-container'):
        lines = []
        for line in scene.find_all(id=re.compile(r'^S\d+L\d+$')):
            for button in line.find_all('button'):
                button.decompose()
            text = ' '.join(line.stripped_strings)
            if text:
                lines.append((line['id'], text))
        if not lines:
            continue
        # Context is a complete scene, not a tiny quotation or a global packet cap.
        text = '\n'.join(t for _, t in lines)
        segments.append({'id': episode+'_'+scene['id'], 'source_id': episode,
            'episode': episode, 'scene': scene['id'], 'first_line': lines[0][0],
            'last_line': lines[-1][0], 'start': offset, 'end': offset+len(text),
            'text': text, 'line_ids': [a for a,_ in lines],
            'line_texts': [b for _,b in lines], 'url': url+'#'+lines[0][0],
            'dependence_cluster': 'aired_'+episode,
            'source_type': 'unofficial dialogue/stage-direction transcription'})
        offset += len(text)+2
    if not segments:
        raise ValueError('No structured scenes: '+url)
    return segments


def acquire(root, config):
    root = Path(root); raw = root/'data/raw/v4'; raw.mkdir(parents=True, exist_ok=True)
    dest = root/'.private/v4'; dest.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    index_url = 'https://screenscripts.com/game-of-thrones/'
    response = requests.get(index_url, timeout=25); response.raise_for_status()
    (raw/'index.html').write_bytes(response.content)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = {}
    for a in soup.find_all('a', href=True):
        url = urljoin(index_url, a['href']); m = re.search(r's\d\de\d\d', url)
        if m:
            links[m[0]] = url
    requested = sorted({ep for c in config['cases'] for ep in c['episodes']})

    def one(ep):
        url = links.get(ep)
        if not url:
            return {'episode': ep, 'error': 'Episode absent from accessible index'}, []
        try:
            if time.monotonic()-started > 3600:
                raise TimeoutError('Acquisition deadline')
            file = raw/(ep+'.html'); previous = root/'data/raw/v2'/('screen_'+ep+'.html')
            if file.exists():
                data = file.read_bytes(); origin = 'v4 cache'
            elif previous.exists():
                data = previous.read_bytes(); file.write_bytes(data); origin = 'preserved v2 raw cache'
            else:
                r = requests.get(url, timeout=25); r.raise_for_status()
                data = r.content; file.write_bytes(data); origin = 'HTTP 200'
            segs = parse_page(data, url, ep)
            return {'episode': ep, 'url': url, 'accessed_at': datetime.now(timezone.utc).isoformat(),
                'origin': origin, 'html_sha256': sha(data), 'scenes': len(segs),
                'normalized_sha256': sha('\n\n'.join(s['text'] for s in segs).encode()),
                'quality': 'Unofficial transcription of aired TV; stage directions and speaker attribution unverified',
                'dependence_cluster': 'aired_'+ep}, segs
        except Exception as e:
            return {'episode': ep, 'url': url, 'error': type(e).__name__+': '+str(e)}, []

    sources, segments = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for source, segs in pool.map(one, requested):
            sources.append(source); segments.extend(segs)
            print(source['episode'], len(segs), source.get('error', 'OK'), flush=True)
    manifest = {'sources': sources, 'elapsed_seconds': time.monotonic()-started,
        'requested_episodes': len(requested), 'acquired_scenes': len(segments),
        'independent_corroboration': False,
        'copyright': 'Full text stays private; access does not grant redistribution rights.'}
    (dest/'corpus.json').write_text(json.dumps({'segments': segments, 'sources': sources}, ensure_ascii=False))
    (root/'runs/application_v4_20261013/acquisition.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def search(root, case, question, max_chars=18000, context_scenes=1):
    """Every query searches the BROAD case corpus, not the current packet."""
    root = Path(root)
    data = json.loads((root/'.private/v4/corpus.json').read_text())
    pool = [s for s in data['segments'] if s['episode'] in case['episodes']]
    ranked = retrieve(pool, question, max_chars=max_chars)
    ids = {s['id'] for s in ranked}
    expanded = set(ids)
    for i, s in enumerate(pool):
        if s['id'] in ids:
            for t in pool[max(0,i-context_scenes):i+context_scenes+1]:
                if t['episode'] == s['episode']:
                    expanded.add(t['id'])
    chosen = [s for s in pool if s['id'] in expanded]
    folder = root/'.private/v4'/case['id']; folder.mkdir(parents=True, exist_ok=True)
    history = folder/'retrieval.json'
    records = json.loads(history.read_text()) if history.exists() else []
    old = folder/'packet.json'
    retained = {s['id'] for s in json.loads(old.read_text())['segments']} if old.exists() else set()
    records.append({'question': question, 'searched_scenes': len(pool),
        'ranked_ids': [s['id'] for s in ranked], 'context_ids': sorted(expanded-ids),
        'new_ids': sorted(expanded-retained), 'method': 'BM25 over full case corpus + neighboring scenes',
        'at': datetime.now(timezone.utc).isoformat()})
    history.write_text(json.dumps(records, indent=2)+'\n')
    retained.update(expanded)
    old.write_text(json.dumps(packet([s for s in pool if s['id'] in retained]), ensure_ascii=False))
    return chosen


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['acquire','search'])
    p.add_argument('--root', default='.'); p.add_argument('--case'); p.add_argument('--question')
    a=p.parse_args(); cfg=json.loads((Path(a.root)/'configs/v4_campaign.json').read_text())
    if a.action=='acquire':
        print(json.dumps(acquire(a.root,cfg)))
    else:
        c=next(c for c in cfg['cases'] if c['id']==a.case)
        for s in search(a.root,c,a.question):
            print('\n['+s['id']+'] '+s['url']+'\n'+s['text'])
