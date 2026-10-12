"""Bounded typed AST evaluation. Generated text is never Python code."""
import itertools, math, random, time
import networkx as nx

class InvalidModel(ValueError):
    pass

OPS = {'and':(2,8),'or':(2,8),'xor':(2,2),'not':(1,1),
       'add':(2,8),'sub':(2,2),'mul':(2,8),'div':(2,2),
       'min':(2,8),'max':(2,8),'eq':(2,2),'ne':(2,2),
       'lt':(2,2),'le':(2,2),'gt':(2,2),'ge':(2,2),
       'if':(3,3),'clip':(3,3),'sigmoid':(1,1)}
NUMERIC={'bool','int','float'}


def valid_value(value, spec):
    kind=spec['type']
    if kind=='bool': return isinstance(value,(bool,int)) and value in (0,1)
    if kind=='category': return isinstance(value,str) and value in spec['values']
    if kind=='int' and (isinstance(value,bool) or not isinstance(value,int)): return False
    if kind=='float' and (isinstance(value,bool) or not isinstance(value,(float,int))): return False
    return kind in ('int','float') and math.isfinite(value) and spec['bounds'][0]<=value<=spec['bounds'][1]


def domain(spec, sampled=False):
    if spec['type']=='bool': return [0,1]
    if spec['type']=='category': return spec['values']
    lo,hi=spec['bounds']
    if spec['type']=='int' and hi-lo<=15: return list(range(lo,hi+1))
    values=[lo,(lo+hi)/2,hi]
    return list(dict.fromkeys(int(x) if spec['type']=='int' else x for x in values))


def check_spec(spec):
    if spec.get('type') not in ('bool','int','float','category'): raise InvalidModel('Invalid state type')
    if spec['type']=='category':
        values=spec.get('values',[])
        if not 2<=len(values)<=32 or not all(isinstance(x,str) for x in values) or len(set(values))!=len(values):
            raise InvalidModel('Invalid categorical domain')
    elif spec['type'] in ('int','float'):
        bounds=spec.get('bounds',[])
        if len(bounds)!=2 or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in bounds) or bounds[0]>=bounds[1]:
            raise InvalidModel('Invalid bounds')
        if spec['type']=='int' and not all(isinstance(x,int) for x in bounds): raise InvalidModel('Integer bounds required')


def ast_info(expr, specs, noises, depth=0, count=None):
    if count is None: count=[0]
    count[0]+=1
    if count[0]>192 or depth>16: raise InvalidModel('AST complexity limit')
    if not isinstance(expr,dict): raise InvalidModel('Expression must be a JSON object')
    if set(expr)=={'const'}:
        x=expr['const']
        if isinstance(x,str): return 'category',set(),set()
        if isinstance(x,(int,float)) and math.isfinite(x): return ('bool' if x in (0,1) else 'int' if isinstance(x,int) else 'float'),set(),set()
        raise InvalidModel('Invalid literal')
    if set(expr)=={'ref'}:
        key=expr['ref']
        if key not in specs: raise InvalidModel('Undeclared parent '+str(key))
        return specs[key]['type'],{key},set()
    if set(expr)=={'noise'}:
        key=expr['noise']
        if key not in noises: raise InvalidModel('Undeclared background '+str(key))
        return noises[key]['type'],set(),{key}
    if set(expr)!={'op','args'} or expr['op'] not in OPS: raise InvalidModel('Unknown AST operator/field')
    op=expr['op']; args=expr['args'];lo,hi=OPS[op]
    if not isinstance(args,list) or not lo<=len(args)<=hi: raise InvalidModel('Invalid arity for '+op)
    infos=[ast_info(x,specs,noises,depth+1,count) for x in args]
    types=[x[0] for x in infos]
    if op=='if':
        if types[0] not in NUMERIC: raise InvalidModel('Non-numeric condition')
        if types[1]!=types[2] and not set(types[1:])<=NUMERIC: raise InvalidModel('Incompatible conditional branches')
        out=types[1] if types[1]==types[2] else 'float' if 'float' in types[1:] else 'int'
    elif op in ('eq','ne'):
        if types[0]!=types[1] and not set(types)<=NUMERIC: raise InvalidModel('Incompatible comparison')
        out='bool'
    else:
        if not set(types)<=NUMERIC: raise InvalidModel('Numeric/logical operator on category')
        out='bool' if op in ('and','or','xor','not','lt','le','gt','ge') else 'float' if op in ('div','sigmoid') or 'float' in types else 'int'
    return out,set().union(*(x[1] for x in infos)),set().union(*(x[2] for x in infos))


def evaluate(expr, parents, background):
    if 'const' in expr: return expr['const']
    if 'ref' in expr: return parents[expr['ref']]
    if 'noise' in expr: return background[expr['noise']]
    op=expr['op'];args=expr['args']
    if op=='if': return evaluate(args[1] if evaluate(args[0],parents,background) else args[2],parents,background)
    v=[evaluate(a,parents,background) for a in args]
    if op=='and': return int(all(v))
    if op=='or': return int(any(v))
    if op=='xor': return int(bool(v[0])!=bool(v[1]))
    if op=='not': return int(not v[0])
    if op=='add': return sum(v)
    if op=='sub': return v[0]-v[1]
    if op=='mul': return math.prod(v)
    if op=='div': return v[0]/v[1]
    if op=='min': return min(v)
    if op=='max': return max(v)
    if op=='clip': return min(max(v[0],v[1]),v[2])
    if op=='sigmoid': return 1/(1+math.exp(-min(60,max(-60,v[0]))))
    if op=='eq': return int(v[0]==v[1])
    if op=='ne': return int(v[0]!=v[1])
    if op=='lt': return int(v[0]<v[1])
    if op=='le': return int(v[0]<=v[1])
    if op=='gt': return int(v[0]>v[1])
    if op=='ge': return int(v[0]>=v[1])
    raise InvalidModel('Unknown operator')


def equation(expr):
    if 'const' in expr: return repr(expr['const'])
    if 'ref' in expr: return expr['ref']
    if 'noise' in expr: return expr['noise']
    return expr['op']+'('+', '.join(equation(x) for x in expr['args'])+')'


class SCM:
    def __init__(self, model, dependency_check=True):
        self.model=model
        nodes=model.get('nodes',[])
        if not 1<=len(nodes)<=128: raise InvalidModel('Node count outside bounds')
        self.nodes={v['id']:v for v in nodes}
        if len(self.nodes)!=len(nodes): raise InvalidModel('Duplicate node IDs')
        self.background=model.get('background',{})
        if len(self.background)>128: raise InvalidModel('Too many background inputs')
        for spec in list(self.nodes.values())+list(self.background.values()): check_spec(spec)
        self.graph=nx.DiGraph(); self.graph.add_nodes_from(self.nodes)
        self.diagnostics={'dependency_checks':{},'inactive_parents':[], 'unchecked_temporal_edges':[]}
        for ident,node in self.nodes.items():
            parents=node.get('parents',[]); noise=node.get('noise',[])
            if len(parents)!=len(set(parents)) or len(parents)>12: raise InvalidModel('Invalid parent list '+ident)
            if any(p not in self.nodes or p==ident for p in parents): raise InvalidModel('Unknown/self parent '+ident)
            if any(u not in self.background for u in noise): raise InvalidModel('Unknown noise '+ident)
            out,refs,used_noise=ast_info(node['expr'],{p:self.nodes[p] for p in parents},{u:self.background[u] for u in noise})
            if refs!=set(parents) or used_noise!=set(noise): raise InvalidModel('Graph/AST input mismatch '+ident)
            if out!=node['type'] and not (out in NUMERIC and node['type'] in NUMERIC): raise InvalidModel('Output type mismatch '+ident)
            if not valid_value(node['observed'],node) or not valid_value(node['reference'],node): raise InvalidModel('Invalid observation/reference '+ident)
            for parent in parents:
                a=self.nodes[parent].get('time');b=node.get('time')
                if a is None or b is None: self.diagnostics['unchecked_temporal_edges'].append([parent,ident])
                elif a>b: raise InvalidModel('Temporal reversal '+parent+' -> '+ident)
                self.graph.add_edge(parent,ident)
        if not nx.is_directed_acyclic_graph(self.graph): raise InvalidModel('Cyclic structural model')
        if model.get('outcome') not in self.nodes: raise InvalidModel('Missing outcome')
        self.order=list(nx.topological_sort(self.graph))
        self.u={u:s['observed'] for u,s in self.background.items()}
        if any(not valid_value(self.u[u],s) for u,s in self.background.items()): raise InvalidModel('Invalid background state')
        if dependency_check: self.check_dependencies()
        factual=self.solve()
        self.diagnostics['factual_mismatches']=[k for k,v in factual.items() if v!=self.nodes[k]['observed']]
        if self.diagnostics['factual_mismatches']: raise InvalidModel('Factual mismatch '+str(self.diagnostics['factual_mismatches']))

    def check_dependencies(self):
        rng=random.Random(8701)
        for ident,node in self.nodes.items():
            names=node['parents']+node.get('noise',[])
            specs=[self.nodes[k] if k in node['parents'] else self.background[k] for k in names]
            domains=[domain(s) for s in specs]
            total=math.prod(len(x) for x in domains)
            exact=total<=256 and all(s['type']!='float' and not (s['type']=='int' and s['bounds'][1]-s['bounds'][0]>15) for s in specs)
            contexts=list(itertools.product(*domains)) if total<=256 else [tuple(rng.choice(d) for d in domains) for _ in range(128)]
            active=set()
            for ctx in contexts:
                p=dict(zip(names,ctx));inputs={k:p[k] for k in node['parents']};u={k:p[k] for k in node.get('noise',[])}
                try: initial=evaluate(node['expr'],inputs,u)
                except (ArithmeticError,ValueError) as e: raise InvalidModel('Undefined mechanism '+ident+': '+str(e))
                if not valid_value(initial,node): raise InvalidModel('Out-of-domain mechanism '+ident+': '+str(initial))
                for j,parent in enumerate(node['parents']):
                    for alternate in domains[j]:
                        other=dict(inputs);other[parent]=alternate
                        val=evaluate(node['expr'],other,u)
                        if not valid_value(val,node): raise InvalidModel('Out-of-domain mechanism '+ident)
                        if val!=initial: active.add(parent)
            inactive=set(node['parents'])-active
            self.diagnostics['dependency_checks'][ident]='exhaustive' if exact else 'sampled'
            self.diagnostics['inactive_parents'] += [[p,ident] for p in sorted(inactive)]
        if self.diagnostics['inactive_parents']:
            raise InvalidModel('Inactive declared edges '+str(self.diagnostics['inactive_parents']))

    def solve(self, background=None, interventions=None, inactive_edges=None, references=None):
        u=dict(self.u if background is None else background)
        if set(u)!=set(self.background) or any(not valid_value(u[k],s) for k,s in self.background.items()): raise InvalidModel('Invalid shared background')
        do=interventions or {}; inactive=set(inactive_edges or []); refs=references or {};values={}
        if set(do)-set(self.nodes): raise InvalidModel('Unknown intervention target')
        for parent,child in inactive:
            if not self.graph.has_edge(parent,child): raise InvalidModel('Unknown inactive edge')
            ref=refs.get((parent,child),self.nodes[parent]['reference'])
            if not valid_value(ref,self.nodes[parent]): raise InvalidModel('Invalid edge reference')
        deadline=time.monotonic()+2
        for ident in self.order:
            if time.monotonic()>deadline: raise InvalidModel('Evaluation time limit')
            node=self.nodes[ident]
            if ident in do: value=do[ident]
            else:
                parents={p:refs.get((p,ident),self.nodes[p]['reference']) if (p,ident) in inactive else values[p] for p in node['parents']}
                value=evaluate(node['expr'],parents,{key:u[key] for key in node.get('noise',[])})
            if not valid_value(value,node): raise InvalidModel('Value outside declared state space '+ident)
            values[ident]=value
        return values
