"""Paired literary baselines are descriptive: no counterfactual ground truth exists."""
import hashlib,json
from pathlib import Path
from .generation import Generator
from .budget import atomic_json


def run(root):
    gen=Generator(root)
    for folder in sorted((gen.run/'application').glob('*')):
        files=sorted(folder.glob('alternative_*.json'))
        if not files:continue
        record=json.loads(files[0].read_text());model=record['model'];nodes={n['id']:n for n in model['nodes']}
        signature=hashlib.sha256(json.dumps({'model':model,'queries':record['queries']},sort_keys=True).encode()).hexdigest()
        existing=folder/'baselines.json'
        if existing.exists():
            prior=json.loads(existing.read_text())
            if prior.get('model_query_signature')==signature:continue
            archive=folder/'prior_baselines';archive.mkdir(exist_ok=True)
            existing.rename(archive/(hashlib.sha256(existing.read_bytes()).hexdigest()[:16]+'.json'))
        packet=json.loads((gen.root/'.private/packets'/(record['case']['id']+'.json')).read_text())
        questions=[]
        for q in record['queries']:
            desc=', '.join(nodes[k]['label']+' set to '+str(v)+' ('+nodes[k]['reference_meaning']+')' for k,v in q['intervention'].items())
            questions.append({'id':q['id'],'text':'In the factual background, intervene: '+desc+'. Would the specified war outcome still hold? State uncertainty; this has no observable gold outcome.'})
        questions += [{'id':'factual_outcome','text':'Does the source packet describe the specified war outcome as occurring?'},
                      {'id':'factual_boundary','text':'List two source-backed events in this packet, with segment IDs.'},
                      {'id':'structural_assumptions','text':'Which proposed causal links or counterfactual mechanisms are not identified by these documents?'},
                      {'id':'structural_alternative','text':'Give a competing mechanism consistent with these observations, without claiming it is verified.'}]
        common='Answer only from this evidence. Distinguish occurrence, character reports, and unidentifiable counterfactuals. Return {"answers":[{"id":"question id","possible_outcome":[0,1],"text":"concise explanation","segments":["source id"]}]}. Use [0,1] for unresolved binary outcomes. Do not invoke memory.\nOUTCOME: '+record['case']['outcome']+'\nQUESTIONS: '+json.dumps(questions)+'\nPACKET:\n'+packet['packet_text']
        responses={}
        for method in ('B0','B1'):
            prompt=common
            if method=='B1':prompt+='\nEXTRACTED GRAPH (no structural expressions): '+json.dumps([{'id':n['id'],'label':n['label'],'parents':n['parents']} for n in model['nodes']])
            try:responses[method]=gen.call('application_'+method,prompt,2048,2027)
            except Exception as e:responses[method]={'error':str(e)}
        atomic_json(folder/'baselines.json',{'questions':questions,'methods':responses,'shared_packet_sha256':packet['packet_sha256'],'model_trace':record['queries'],'model_query_signature':signature,
                                           'evaluation':'Descriptive agreement/uncertainty only; model-generated counterfactuals are not gold labels.'})

if __name__=='__main__':
    import sys
    run(sys.argv[1] if len(sys.argv)>1 else '.')
