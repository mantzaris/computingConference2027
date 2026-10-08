"""Summarize measured complete pilot costs without reading predictive outcomes."""
import json
from sem_update.phase3.runtime import root,RESULTS,read_json,atomic_json,file_hash

def main():
    pilots=read_json(RESULTS/'pilots.json');rows=[]
    for pilot in pilots:
        t=pilot['task'];tag=f"{t['profile']}-{t['family']}-d{t['d']}-s{t['seed']}-B400"
        record=read_json(root()/pilot['records'][0]['adjusted']);condition=record['condition']
        stages={}
        for p in sorted((root()/'runs').glob(tag+'*.json')):
            value=read_json(p)
            if 'stage_seconds' in value:stages[p.stem[len(tag)+1:]]={'seconds':value['stage_seconds'],'peak_bytes':value['stage_peak_bytes']}
        banks={}
        for policy in ('diagnostic','random'):
            bank=read_json(root()/'runs'/(condition+'-'+policy)/'bank.json')
            banks[policy]={'candidates':len(bank['candidates']),'fixed_prefix_count':bank['fixed_count'],
                'cost':bank['cost'],'stage_wall_seconds':stages['c0.5-'+policy]['seconds'],
                'accepted_search_moves':sum(e['accepted'] for e in bank['edits']),
                'peak_bytes':bank['peak_vram_bytes']}
        dcdi=read_json(root()/'runs'/(tag+'-discovery.json'))
        rows.append({'task':t,'complete_wall_seconds':pilot['wall_seconds'],'stages':stages,'banks':banks,
            'discovery':{k:dcdi[k] for k in ('seconds','optimization_steps','status','h_per_node','legacy_converged')},
            'evaluation':pilot['evaluation'],'six_main_methods':all(k in record['methods'] for k in ('M0','M1','M2','M3','M4','M5')),
            'source_hash':record['source_hash'],'artifact_record':pilot['records']})
    source=root()/'archives/pilot_source.tar.gz'
    value={'pilots':rows,'pilot_source_archive':'archives/pilot_source.tar.gz','pilot_source_sha256':file_hash(source),
        'pilot_config_sha256':file_hash(RESULTS.parent/'configs/pilot.json'),
        'scope':'Development timing and validity, not main-study performance or tuning on final outcomes'}
    atomic_json(RESULTS/'pilot_provenance.json',value);print(json.dumps(value,indent=2))

if __name__=='__main__':main()
