"""Immutable DAGs: row is parent, column is child."""
from dataclasses import dataclass
import itertools
import numpy as np
import networkx as nx
from .runtime import digest

@dataclass(frozen=True)
class DAG:
    d: int
    edges: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        edges = tuple(sorted(tuple(map(int, e)) for e in self.edges))
        if len(set(edges)) != len(edges):
            raise ValueError('duplicate edge')
        if any(a == b or not (0 <= a < self.d and 0 <= b < self.d) for a,b in edges):
            raise ValueError('invalid edge')
        object.__setattr__(self, 'edges', edges)
        if not nx.is_directed_acyclic_graph(self.networkx()):
            raise ValueError('cyclic graph')

    def networkx(self):
        g = nx.DiGraph()
        g.add_nodes_from(range(self.d))
        g.add_edges_from(self.edges)
        return g

    def parents(self, j):
        return tuple(a for a,b in self.edges if b == j)

    def order(self):
        return tuple(nx.lexicographical_topological_sort(self.networkx()))

    @property
    def key(self):
        return digest(self.json())

    def json(self):
        return {'d': self.d, 'edges': [list(e) for e in self.edges]}

    @classmethod
    def from_json(cls, value):
        return cls(int(value['d']), tuple(tuple(e) for e in value['edges']))

    def valid_edits(self, max_indegree=3, root_nodes=()):
        existing = set(self.edges)
        for a,b in itertools.permutations(range(self.d), 2):
            moves = [('delete', existing-{(a,b)}, (b,))] if (a,b) in existing else [('add', existing|{(a,b)}, (b,))]
            if (a,b) in existing:
                moves.append(('reverse', (existing-{(a,b)})|{(b,a)}, (a,b)))
            for op, edges, affected in moves:
                if any(sum(v == j for _,v in edges) > max_indegree for j in range(self.d)):
                    continue
                if any(v in root_nodes for _,v in edges):
                    continue
                try:
                    g = DAG(self.d, tuple(edges))
                except ValueError:
                    continue
                yield {'operation': op, 'source': a, 'target': b, 'affected': affected}, g

def structural_metrics(estimate, truth):
    a,b = set(estimate.edges), set(truth.edges)
    tp = len(a & b)
    difference = a ^ b
    reversals = sum((y,x) in difference for x,y in difference) // 2
    return {'shd': len(difference)-reversals, 'precision': tp/len(a) if a else 0.,
            'recall': tp/len(b) if b else 0., 'f1': 2*tp/(len(a)+len(b)) if a or b else 1.}

def corrupt(truth, fraction, seed):
    rng = np.random.default_rng(seed)
    graph, history, seen = truth, [], {truth.key}
    operations = np.array(['delete', 'add', 'reverse'])
    rng.shuffle(operations)
    count = max(1, round(len(truth.edges)*fraction)) if fraction else 0
    for k in range(count):
        moves = [(e,g) for e,g in graph.valid_edits() if g.key not in seen]
        eligible = [(e,g) for e,g in moves if e['operation'] == operations[k%3]] or moves
        if not eligible:
            break
        edit,graph = eligible[int(rng.integers(len(eligible)))]
        history.append(edit)
        seen.add(graph.key)
    return graph, history

def linear_bic_start(x, max_moves=100, root_nodes=()):
    """Fit-observational data only; deterministic lexicographic ties."""
    x = np.asarray(x, dtype=float)
    n,d = x.shape
    cache = {}
    def node(j, parents):
        key = j,parents
        if key not in cache:
            design = np.column_stack([np.ones(n), x[:,parents]])
            residual = x[:,j] - design @ np.linalg.lstsq(design,x[:,j],rcond=None)[0]
            cache[key] = n*np.log(max(np.mean(residual**2),1e-8))+(len(parents)+2)*np.log(n)
        return cache[key]
    def score(g):
        return sum(node(j,g.parents(j)) for j in range(d))
    graph = DAG(d)
    value = score(graph)
    for _ in range(max_moves):
        options = sorted((score(g),g.key,g) for _,g in graph.valid_edits(root_nodes=root_nodes))
        if not options or options[0][0] >= value-1e-8:
            break
        value,_,graph = options[0]
    return graph
