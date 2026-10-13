"""Curated v4 records: offline calculation/rendering, no model or full transcripts.

--pack needs the retained private campaign. Default verifies all calculations.
--render regenerates SVG/PDF/PNG and the gallery; --expand-gallery is browser-free.
--source-check verifies retained private scene locations when available.
"""
import argparse
import base64
import copy
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v3.core import build_family, fingerprint, query, check_claims, verify_reported_result
from got_war.v4.report import accounting, render
from got_war.v4.figures import model_hash

ARCHIVE=ROOT/'results/v4/reproduction.json.xz'

def clean(x):
    if isinstance(x,list):return [clean(v) for v in x]
    if isinstance(x,dict):
        if 'models' in x and 'local' in x and 'functions' in x:
            return {'functions':clean(x['functions']),'coverage':x['coverage'],'exhaustive':x['exhaustive'],
                'models_sha256':fingerprint(x['models'])}
        r={k:clean(v) for k,v in x.items() if k not in ('quote','models','worlds')}
        if 'quote' in x:r['quote_sha256']=hashlib.sha256(x['quote'].encode()).hexdigest()
        return r
    return x


def pack():
    cfg=json.loads((ROOT/'configs/v4_campaign.json').read_text());run=ROOT/'runs/application_v4_20261013'
    records=[];drafts={};retrieval={};packets={}
    for c in cfg['cases']:
        p=ROOT/'.private/v4'/c['id'];r=json.loads((run/c['id']/'validated.json').read_text())
        r['original_display_sha256']=model_hash(r);records.append(clean(r))
        full=clean(json.loads((p/'draft.json').read_text()))
        drafts[c['id']]={'scenarios':full['scenarios'],'retained_full_draft':str((p/'draft.json').relative_to(ROOT))}
        retrieval[c['id']]=json.loads((p/'retrieval.json').read_text())
        pkt=json.loads((p/'construction_packet.json').read_text());packets[c['id']]={'sha256':pkt['packet_sha256'],'segments':[s['id'] for s in pkt['segments']]}
    qwen=[]
    for p in sorted((run/'qwen').glob('*/pass*.json')):
        r=json.loads(p.read_text());raw=r.get('raw',{});choice=raw.get('choices',[{}])[0]
        prompt=p.with_name(p.name.replace('pass_','prompt_'))
        request=json.loads(prompt.read_text());request['messages'][-1]['content']=request['messages'][-1]['content'].split('\n[')[0]
        qwen.append({'file':str(p.relative_to(ROOT)),'case':r['case'],'passage_ids':r['passage_ids'],'request_sha256':r['request_sha256'],
            'request_without_passage_text':request,'content_sha256':hashlib.sha256(choice.get('message',{}).get('content','').encode()).hexdigest(),
            'raw_content_retained_locally':True,'finish_reason':choice.get('finish_reason'),
            'usage':raw.get('usage'),'elapsed_seconds':r['elapsed_seconds'],'json_valid':r.get('parsed') is not None})
    data={'version':4,'records':records,'generation_drafts':drafts,'qwen':qwen,'retrieval':retrieval,'packets':packets,
        'source_acquisition':json.loads((run/'acquisition.json').read_text()),'usage':accounting(ROOT),
        'campaign_budget':json.loads((ROOT/'configs/budget_v4.json').read_text()),
        'source_check_limit':'Public references retain offsets/hashes/support judgments, not full quote text. Private packets or hash-matching reacquisition are required for source verification.',
        'generation_instructions':(ROOT/'.private/v4/blackwater/generation_instructions.txt').read_text()}
    raw=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode();ARCHIVE.write_bytes(lzma.compress(raw,preset=9))
    manifest={'sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),'bytes':ARCHIVE.stat().st_size,'expanded_bytes':len(raw),
        'cases':[c['id'] for c in cfg['cases']],'qwen_attempts':len(qwen),'scope':data['source_check_limit']}
    (ARCHIVE.parent/'reproduction_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return data


def load():
    raw=ARCHIVE.read_bytes();m=json.loads((ARCHIVE.parent/'reproduction_manifest.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=m['sha256']:raise ValueError('Archive hash mismatch')
    return json.loads(lzma.decompress(raw))


def restore_models(record):
    record=copy.deepcopy(record);r=record['representation']
    for container,key in [(record,'partial_family')]+[(s,'family') for s in record['scenarios']]:
        old=container[key];new=build_family(r,{'functions':old['functions']})
        if any(old[k]!=new[k] for k in ('coverage','exhaustive')) or fingerprint(new['models'])!=old['models_sha256']:
            raise ValueError('Family failed exact reproduction')
        container[key]=new
    if model_hash(record)!=record['original_display_sha256']:raise ValueError('Figure/model identity changed')
    return record


def verify(data,source_check=False):
    records=[];counts={'cases':0,'queries':0,'scenario_queries':0,'source_locations':0,'formal_claims':0}
    corpus=json.loads((ROOT/'.private/v4/corpus.json').read_text()) if source_check else None
    ps={s['id']:s for s in corpus['segments']} if corpus else {}
    for compact in data['records']:
        r=restore_models(compact);rep=r['representation'];draft=data['generation_drafts'][r['case']]
        for q in r['queries']:
            if not verify_reported_result(rep,r['partial_family'],q['do'],q['partial_result'])['passed']:raise ValueError('Partial answer differs')
            counts['queries']+=1
            for a in q['conditional']:
                s=next(s for s in r['scenarios'] if s['id']==a['scenario'])
                if not verify_reported_result(rep,s['family'],q['do'],a['result'])['passed']:raise ValueError('Scenario answer differs')
                counts['scenario_queries']+=1
        for s,spec in zip(r['scenarios'],draft['scenarios']):
            checks=check_claims(rep,s['family'],spec['claims'])
            if checks!=s['claims']:raise ValueError('Formal claim checks differ')
            counts['formal_claims']+=len(checks)
        if source_check:
            seen=set()
            for obj in rep['variables']+rep['edges']+rep['mechanisms']:
                for ref in obj['evidence']:
                    key=(ref['passage_id'],ref['start'],ref['end'],ref['quote_sha256'])
                    if key in seen:continue
                    seen.add(key);text=ps[ref['passage_id']]['text']
                    if hashlib.sha256(text.encode()).hexdigest()!=ref['passage_sha256']:raise ValueError('Passage changed')
                    if hashlib.sha256(text[ref['start']:ref['end']].encode()).hexdigest()!=ref['quote_sha256']:raise ValueError('Quote location changed')
                    counts['source_locations']+=1
        records.append(r);counts['cases']+=1
    return records,counts


def expand_gallery():
    path=ROOT/'results/v4/GALLERY.html';data=re.search(r'<script id="portfolio-data"[^>]*>(.*?)</script>',path.read_text()).group(1)
    path.with_name('GALLERY_EXPANDED.html').write_bytes(gzip.decompress(base64.b64decode(data)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('pack','render','source-check','expand-gallery'):p.add_argument('--'+flag,action='store_true')
    a=p.parse_args();data=pack() if a.pack else load();records,counts=verify(data,a.source_check)
    if a.render:render(ROOT,records,data['usage'])
    if a.expand_gallery:expand_gallery()
    print(json.dumps(counts,indent=2))
