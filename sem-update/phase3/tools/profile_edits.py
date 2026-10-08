"""CPU graph bookkeeping profile, including exact legal-neighborhood agreement."""
import json
import time
from sem_update.phase3.runtime import RESULTS,atomic_json
from sem_update.phase3.data import System
from sem_update.phase3.graphs import edit_descriptors,apply

rows=[]
for d in (20,50,100):
    graph=System(d,'nonlinear','sparse',392000+d).graph
    start=time.perf_counter();old={g.key for _,g in graph.valid_edits(max_indegree=3)};old_seconds=time.perf_counter()-start
    start=time.perf_counter();descriptors=edit_descriptors(graph,3);new_seconds=time.perf_counter()-start
    assert old=={apply(graph,e).key for e in descriptors}
    rows.append({'d':d,'valid_edits':len(old),'historical_enumeration_seconds':old_seconds,
        'descriptor_enumeration_seconds':new_seconds,'avoided_full_DAG_constructions':len(old),
        'scope':'CPU graph bookkeeping only; not a claimed end-to-end GPU speedup'})
atomic_json(RESULTS/'edit_profile.json',rows);print(json.dumps(rows,indent=2))
