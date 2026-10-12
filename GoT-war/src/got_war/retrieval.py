"""Lexical source-bounded retrieval and source-packet freezing."""
import collections, hashlib, json, math, re
from pathlib import Path


def tokens(text):return re.findall(r'[a-z]{3,}',text.lower())

def retrieve(segments,query,max_chars=10000):
    documents=[tokens(s['text']) for s in segments];length=sum(map(len,documents))/max(1,len(documents));counts=collections.Counter(t for d in documents for t in set(d));query=set(tokens(query));ranked=[]
    for segment,document in zip(segments,documents):
        freq=collections.Counter(document);score=0
        for term in query:
            f=freq[term]
            score+=math.log(1+(len(documents)-counts[term]+.5)/(counts[term]+.5))*f*2.2/(f+1.2*(.25+.75*len(document)/max(1,length)))
        ranked.append((score,segment))
    ranked.sort(key=lambda x:(-x[0],x[1]['id']));chosen=[];used=0
    for score,segment in ranked:
        if score<=0:continue
        if used+len(segment['text'])+len(segment['id'])+6>max_chars:continue
        chosen.append(dict(segment,retrieval_score=score));used+=len(segment['text'])+len(segment['id'])+6
    return sorted(chosen,key=lambda s:s['id'])


def freeze_packets(root):
    root=Path(root);config=json.loads((root/'configs/experiment.json').read_text());segments=[json.loads(x) for x in (root/'data/derived/segments.private.jsonl').read_text().splitlines()];records=[]
    for case in config['cases']:
        pool=[s for s in segments if s['source_id'] in case['source_episodes']]
        packet=retrieve(pool,case['retrieval_query'])
        text='\n'.join('['+s['id']+'] '+s['text'] for s in packet)
        content={'case':case,'segments':packet,'packet_text':text,'packet_sha256':hashlib.sha256(text.encode()).hexdigest(),'retrieval':'BM25-style lexical ranking within frozen television episode pool; same packet for every method/alternative','max_chars':10000}
        private=root/'.private/packets';private.mkdir(parents=True,exist_ok=True);(private/(case['id']+'.json')).write_text(json.dumps(content,indent=2))
        public={k:v for k,v in content.items() if k not in ('segments','packet_text')};public['segment_ids']=[s['id'] for s in packet]
        (root/'data/manifests'/(case['id']+'_packet.json')).write_text(json.dumps(public,indent=2)+'\n');records.append((case['id'],len(packet),len(text)))
    return records

if __name__=='__main__':
    import sys
    print(freeze_packets(sys.argv[1]))
