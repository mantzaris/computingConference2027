"""Shared-edge path-coalition game, exact or paired permutation allocation."""
import itertools, math, random
import networkx as nx
import numpy as np


def select_paths(scm, maximum=8, sources=None):
    target=scm.model['outcome']
    sources=sources or scm.model.get('source_boundary') or [n for n in scm.order if scm.graph.in_degree(n)==0]
    candidates=[]
    for source in sources:
        if source==target: continue
        for p in nx.all_simple_paths(scm.graph,source,target,cutoff=32):
            candidates.append(tuple(p))
            if len(candidates)>=10000: break
    # Source-balanced, shortest-first round robin. No post-outcome tuning.
    candidates=sorted(set(candidates),key=lambda p:(len(p),p))
    chosen=[]
    groups={s:[p for p in candidates if p[0]==s] for s in sorted(sources)}
    while len(chosen)<maximum:
        added=False
        for source,paths in groups.items():
            if paths and len(chosen)<maximum: chosen.append(paths.pop(0));added=True
        if not added: break
    covered=set(e for p in chosen for e in zip(p,p[1:]))
    return {'paths':[list(p) for p in chosen],'all_paths':[list(p) for p in candidates],
            'source_boundary':sources,'selection':'source-balanced shortest-first round-robin; lexicographic ties; K=8',
            'edge_coverage':len(covered)/max(1,scm.graph.number_of_edges()),
            'omitted_edges':[list(e) for e in scm.graph.edges if e not in covered],
            'enumeration_capped':len(candidates)>=10000}


def coalitions(scm, paths, backgrounds=None, references=None, permutations=64, seed=4321, exact=None, groups=None):
    path_edges=[frozenset(zip(p,p[1:])) for p in paths]
    players=path_edges if groups is None else [frozenset().union(*(path_edges[j] for j in group)) for group in groups]
    focus=frozenset().union(*players) if players else frozenset()
    backgrounds=backgrounds or [scm.u]
    # A finite list is an explicitly equal-weight scenario ensemble, not a fitted posterior.
    target=scm.model['outcome'];k=len(players);cache={}
    def value(indices):
        active=frozenset().union(*(players[i] for i in indices)) if indices else frozenset()
        if active not in cache:
            outcomes=[scm.solve(background=u,inactive_edges=focus-active,references=references)[target] for u in backgrounds]
            if not all(isinstance(x,(int,float)) for x in outcomes): raise ValueError('Attribution requires a declared numeric outcome encoding')
            cache[active]=float(np.mean(outcomes))
        return cache[active]
    baseline=value([]);full=value(range(k));phi=np.zeros(k);se=np.zeros(k)
    exact=(k<=6) if exact is None else exact
    if exact:
        for i in range(k):
            others=[j for j in range(k) if j!=i]
            for size in range(k):
                weight=math.factorial(size)*math.factorial(k-size-1)/math.factorial(k)
                for subset in itertools.combinations(others,size): phi[i]+=weight*(value(list(subset)+[i])-value(subset))
        method='exact'
    else:
        rng=random.Random(seed);samples=[]
        for _ in range(permutations):
            order=list(range(k));rng.shuffle(order);before=[];previous=baseline;row=np.zeros(k)
            for i in order:
                before.append(i);after=value(before);row[i]=after-previous;previous=after
            samples.append(row)
        if samples:
            array=np.asarray(samples);phi=array.mean(axis=0)
            se=array.std(axis=0,ddof=1)/math.sqrt(len(array)) if len(array)>1 else np.zeros(k)
        method='sampled permutations'
    standalone=[value([i])-baseline for i in range(k)]
    # Edge unions may enable a route that is not a member of the selected collection.
    graph=nx.DiGraph();graph.add_edges_from(focus)
    recombined=[]
    for source in sorted({p[0] for p in paths}):
        if source not in graph or target not in graph: continue
        for p in nx.all_simple_paths(graph,source,target):
            if list(p) not in paths: recombined.append(p)
    return {'baseline':baseline,'full':full,'contrast':full-baseline,'phi':phi.tolist(),'mc_se':se.tolist(),
            'efficiency_residual':abs(full-baseline-float(phi.sum())), 'naive_standalone':standalone,
            'naive_sum':sum(standalone),'naive_residual':sum(standalone)-(full-baseline),
            'unique_edge_masks':len(cache),'players':k,'method':method,'permutations':0 if exact else permutations,
            'background_count':len(backgrounds),'background_interpretation':'fixed factual background' if len(backgrounds)==1 else 'declared equal-weight scenarios',
            'recombined_routes':recombined,'references':{a+'>'+b:(references or {}).get((a,b),scm.nodes[a]['reference']) for a,b in sorted(focus)}}


def disjoint_mechanism_groups(paths):
    """Connected components of path overlap partition the focused mechanisms."""
    graph=nx.Graph();graph.add_nodes_from(range(len(paths)))
    edges=[set(zip(p,p[1:])) for p in paths]
    for i in range(len(paths)):
        for j in range(i):
            if edges[i]&edges[j]: graph.add_edge(i,j)
    return [sorted(c) for c in nx.connected_components(graph)]


def evidence_priority(paths, attribution, edge_records, segment_clusters=None, uniform=False, summary='minimum'):
    segment_clusters=segment_clusters or {};scores={};records=[]
    for i,path in enumerate(paths):
        records_e=[edge_records.get(a+'>'+b,{'score':0,'segments':[]}) for a,b in zip(path,path[1:])]
        values=[float(r.get('score',0)) for r in records_e]
        support=(1.0 if uniform else min(values,default=0))
        if not uniform and summary=='geometric' and values: support=math.prod(values)**(1/len(values))
        ids=sorted(set(seg for r in records_e for seg in r.get('segments',[])))
        clusters={}
        for seg in ids: clusters.setdefault(segment_clusters.get(seg,seg),[]).append(seg)
        allocations={seg:1/(len(clusters)*len(members)) for members in clusters.values() for seg in members}
        for seg,amount in allocations.items(): scores[seg]=scores.get(seg,0)+amount*support*abs(attribution['phi'][i])
        records.append({'path_id':'p%d'%(i+1),'nodes':path,'evidence_support':support,'signed_contribution':attribution['phi'][i],
                        'segment_allocation':allocations,'allocation_rationale':'Equal allocation over distinct supporting clusters, split within cluster; unsupported paths receive no fabricated segment.'})
    return {'segments':sorted([{'segment_id':s,'priority':v} for s,v in scores.items()],key=lambda x:(-x['priority'],x['segment_id'])), 'paths':records}
