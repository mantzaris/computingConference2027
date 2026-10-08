"""Audit frozen graph/seed design on CPU without drawing or opening outcomes."""
import json
from collections import defaultdict
import numpy as np
import pandas as pd
import torch
from sem_update.phase3.data import System,graph_stats,seed_for,ROLES
from sem_update.phase3.runtime import freeze_guard,RESULTS,atomic_json,file_hash

def main():
    if torch.cuda.is_available():raise RuntimeError('Hide CUDA for this graph-only audit')
    protocol=freeze_guard();tasks=[t for t in protocol['tasks'] if not t.get('sensitivity')]
    streams=defaultdict(list);graphs=[];keys=set();rows=[]
    for task in tasks:
        seed,d=task['seed'],task['d'];system=System(d,task['family'],task['profile'],seed)
        graph=system.graph;stats=graph_stats(graph)
        assert stats['weak_components']==1 and stats['largest_component']==d
        assert graph.key not in keys;keys.add(graph.key)
        cap=8 if task['profile']=='dense' else 6 if task['profile']=='hub' else 3
        assert stats['max_indegree']<=cap and any(a>b for a,b in graph.edges)
        assert stats['edges']==(sum(min(k,7) for k in range(d)) if task['profile']=='dense' else 2*d-3)
        if task['profile']=='deep':assert stats['depth']==d-1
        seen=sorted(map(int,np.random.default_rng(seed_for(seed,'visible')).choice(d,round(.2*d),replace=False)))
        unseen=sorted(set(range(d))-set(seen))
        withheld=sorted(map(int,np.random.default_rng(seed_for(seed,'T3-targets')).choice(unseen,len(seen),replace=False)))
        assert not set(seen)&set(withheld)
        labels=[(role,'obs') for role in ROLES]+[(role,j) for role in ROLES for j in seen]
        labels += [(endpoint,j) for endpoint,targets in [('T1',seen),('T2',seen),('T3',withheld)] for j in targets]
        labels += [('final-obs',),('graph',),('mechanisms',),('visible',),('T3-targets',)]
        for label in labels:streams[seed_for(seed,*label)].append([seed,*label])
        graphs.append({'scm':seed,'d':d,'family':task['family'],'profile':task['profile'],
                       'graph_hash':graph.key,'visible_targets':seen,'withheld_targets':withheld})
        rows.append({**task,**stats,'visible_count':len(seen)})
    collisions=[v for v in streams.values() if len(v)>1]
    frame=pd.DataFrame(rows);cells=[]
    for (d,family,profile),part in frame.groupby(['d','family','profile']):
        cells.append({'d':int(d),'family':family,'profile':profile,'independent_scms':len(part),
            'edges':sorted(map(int,part.edges.unique())),'mean_indegree_range':[float(part.mean_indegree.min()),float(part.mean_indegree.max())],
            'depth_range':[int(part.depth.min()),int(part.depth.max())],
            'maximum_outdegree_range':[int(part.max_outdegree.min()),int(part.max_outdegree.max())],
            'top_decile_outgoing_fraction_range':[float(part.top_decile_outgoing_fraction.min()),float(part.top_decile_outgoing_fraction.max())]})
    value={'passed':not collisions,'protocol_sha256':file_hash(RESULTS/'protocol.json'),
           'scope':'Frozen structural design and seed streams only; no observational/interventional outcomes sampled or inspected',
           'independent_scms':len(tasks),'unique_graphs':len(keys),'unique_streams':len(streams),
           'stream_collisions':collisions,'cells':cells,'graphs':graphs,'source_sha256':file_hash(__file__)}
    atomic_json(RESULTS/'design_audit.json',value)
    print(json.dumps({k:v for k,v in value.items() if k not in ('graphs','cells')},indent=2))
    raise SystemExit(bool(collisions))

if __name__=='__main__':main()
