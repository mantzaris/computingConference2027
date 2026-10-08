"""O(d²) integer edit descriptors, without O(d²) constructed DAG objects."""
import numpy as np
import networkx as nx
from sem_update.graphs import DAG

def edit_descriptors(graph,max_indegree):
    net=graph.networkx();edges=set(graph.edges);indegree=[len(graph.parents(j)) for j in range(graph.d)]
    descendants={j:nx.descendants(net,j) for j in range(graph.d)};moves=[]
    for a in range(graph.d):
        for b in range(graph.d):
            if a==b:continue
            if (a,b) in edges:
                moves.append(('delete',a,b,(b,)))
                # Reversal is legal iff no other a -> ... -> b path remains.
                if indegree[a]<max_indegree and not any(c!=b and (c==b or b in descendants[c]) for c in net.successors(a)):
                    moves.append(('reverse',a,b,(a,b)))
            elif indegree[b]<max_indegree and a not in descendants[b]:moves.append(('add',a,b,(b,)))
    return moves

def apply(graph,move):
    op,a,b,affected=move;edges=set(graph.edges)
    if op in ('delete','reverse'):edges.remove((a,b))
    if op=='add':edges.add((a,b))
    if op=='reverse':edges.add((b,a))
    return DAG(graph.d,tuple(edges))

def corrupt(truth,fraction,seed,max_indegree):
    rng=np.random.default_rng(seed);ops=np.array(['delete','add','reverse']);rng.shuffle(ops)
    graph=truth;seen={truth.key};history=[];last=None
    for k in range(max(1,round(len(truth.edges)*fraction)) if fraction else 0):
        moves=edit_descriptors(graph,max_indegree);rng.shuffle(moves)
        moves.sort(key=lambda m:m[0]!=ops[k%3]);chosen=None
        for move in moves:
            # Do not immediately undo an operation, including reversed endpoint order.
            if last and set(move[1:3])==set(last[1:3]):continue
            candidate=apply(graph,move)
            if candidate.key not in seen:chosen=(move,candidate);break
        if chosen is None:break
        last,graph=chosen;history.append(list(last));seen.add(graph.key)
    return graph,history
