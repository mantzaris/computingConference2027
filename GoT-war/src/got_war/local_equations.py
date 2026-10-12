"""Generate one typed local mechanism against explicit formal input slots."""
import copy,hashlib,json
from .budget import atomic_json
from .structural_programs import SCM,InvalidModel,equation,evaluate


def bind_expression(expr,bindings,noise):
    if not isinstance(expr,dict):raise InvalidModel('Every expression/argument must be a typed JSON object')
    if set(expr)=={'ref'}:
        if expr['ref'] not in bindings:raise InvalidModel('Allowed parent slots are '+str(list(bindings)))
        return {'ref':bindings[expr['ref']]}
    if set(expr)=={'noise'}:
        if not noise or expr['noise']!='U':raise InvalidModel('Only a root may use its declared background slot U')
        return {'noise':noise}
    if set(expr)=={'const'}:return dict(expr)
    if set(expr)!={'op','args'} or not isinstance(expr['args'],list):raise InvalidModel('Use an object leaf or {op,args} expression')
    return {'op':expr['op'],'args':[bind_expression(a,bindings,noise) for a in expr['args']]}


def check_local(child,parents,expression):
    nodes=[];background={}
    for parent in parents:
        root=copy.deepcopy(parent);uid='CONTEXT_'+root['id'];root.update(parents=[],noise=[uid],expr={'noise':uid})
        background[uid]={k:root[k] for k in ('type','values','bounds','observed') if k in root};nodes.append(root)
    target=copy.deepcopy(child);target['expr']=expression;target['noise']=[] if parents else ['U_'+child['id']]
    for uid in target['noise']:background[uid]={k:child[k] for k in ('type','values','bounds','observed') if k in child}
    nodes.append(target)
    try:SCM({'nodes':nodes,'background':background,'outcome':target['id']})
    except InvalidModel as error:
        factual={p['id']:p['observed'] for p in parents};u={k:v['observed'] for k,v in background.items()}
        try:actual=evaluate(expression,factual,u)
        except Exception:actual='not evaluable'
        raise InvalidModel(str(error)+'. Concrete factual check: inputs='+json.dumps(factual)+', required target='+json.dumps(child['observed'])+', expression output='+json.dumps(actual)+'. The target is its recorded state at its stated time, not its eventual later state.') from error


def synthesize_local(gen,packet,blueprint,alternative):
    from .application import packet_for_nodes
    nodes=copy.deepcopy(blueprint['nodes']);mapping={n['id']:n for n in nodes};failures=[]
    folder=gen.run/'application'/packet['case']['id']/'local_equations';folder.mkdir(parents=True,exist_ok=True)
    contract=(gen.root/'prompts/ast_contract.txt').read_text()
    for node in nodes:
        parents=[mapping[p] for p in node['parents']];bindings={'P%d'%i:p['id'] for i,p in enumerate(parents)}
        parent_schema=[dict(slot='P%d'%i,**{k:p[k] for k in ('label','definition','type','values','bounds','observed','reference','time') if k in p}) for i,p in enumerate(parents)]
        target={k:node[k] for k in ('label','definition','type','values','bounds','observed','reference','time') if k in node}
        if node['id']=='W':target['definition']=packet['case']['outcome']
        prompt=contract+'\nGenerate ONE fixed local structural expression for the TARGET. Runtime inputs are ONLY the listed parent slots P0, P1, etc. Use {"ref":"P0"}, never story variable IDs, inside expressions. A root with no parents must use {"noise":"U"}; nonroots have no background/residual. Every listed parent must affect the function on some valid input. The function must match the supplied factual parent and target states and remain in the target domain. No narrative text is a hidden runtime argument. Return {"expr":{...},"assumptions":["what the documents do not identify"],"explanation":"brief description of this precise expression"}. Alternative '+str(alternative+1)+' of three: where evidence underdetermines the combination, propose a defensible alternative interaction or redundancy; do not invent probability estimates.\nTARGET: '+json.dumps(target)+'\nPARENT INPUTS: '+json.dumps(parent_schema)+'\nSOURCE EVIDENCE:\n'+packet_for_nodes(packet,[node]+parents,6500)
        prompt+='\nThe factual input vector is '+json.dumps({'P%d'%i:p['observed'] for i,p in enumerate(parents)})+' and the REQUIRED target output at its stated time is '+json.dumps(node['observed'])+'. Do not substitute the character/event state from a later scene. A counterfactual rule must first satisfy this concrete observed row.'
        previous=[]
        for earlier in range(alternative):
            prior=folder/('alt%d_%s.json'%(earlier,node['id']))
            if prior.exists():previous.append(json.loads(prior.read_text())['generation'])
        if parents and previous:
            prompt+='\nPREVIOUSLY ACCEPTED LOCAL PROPOSALS FOR THESE SAME INPUT SLOTS: '+json.dumps(previous)+'\nCritically assess whether the evidence permits a functionally different alternative. If so, generate it and state the different assumption. Merely rearranging the same expression is not a different mechanism. If no defensible alternative exists, retain the same rule and explicitly explain why; do not force diversity or invent a story fact.'
        if not parents:
            prompt='This variable is a declared external boundary condition in an SCM, not an endogenous event to explain here. Generate its typed identity expression from its explicit background input U. The valid leaf syntax is {"noise":"U"}. The supplied factual value fixes U for this scenario; do not replace the expression with a constant or invent a causal mechanism. Return {"expr":{...},"assumptions":["boundary/background interpretation"],"explanation":"brief identity explanation"}. VARIABLE: '+json.dumps(target)
        accepted=folder/('alt%d_%s.json'%(alternative,node['id']))
        contract_hash=hashlib.sha256(prompt.encode()).hexdigest()
        for attempt in range(3):
            response=None
            try:
                cached=json.loads(accepted.read_text()) if attempt==0 and accepted.exists() else None
                response=cached['generation'] if cached and cached.get('contract_hash')==contract_hash else gen.call('application_local_equation_v6' if not attempt else 'application_local_equation_repair_v6',prompt,3072 if parents else 1024,2027+alternative+attempt,thinking=bool(parents))
                expression=bind_expression(response['expr'],bindings,None if parents else 'U_'+node['id'])
                check_local(node,parents,expression)
                atomic_json(accepted,{'generation':response,'bindings':bindings,'expression':expression,'contract_hash':contract_hash,'validation':'Typed/domain/dependency/factual checks over declared local inputs; no semantic causal identification.'})
                node.update(expr=expression,noise=[] if parents else ['U_'+node['id']],assumptions=response.get('assumptions',[]),explanation=response.get('explanation',equation(expression)),equation_protocol='local-slots-v1')
                break
            except Exception as e:
                failure={'node':node['id'],'alternative':alternative,'attempt':attempt,'error':str(e),'response':response}
                failures.append(failure);atomic_json(folder/('alt%d_%s_failed_%d.json'%(alternative,node['id'],attempt)),failure)
                if attempt==2:raise InvalidModel('Local equation exhausted two repairs: '+node['id']+': '+str(e))
                prompt=prompt.split('\nREPAIR:')[0]+'\nREPAIR: '+str(e)+'\nPrevious expression: '+json.dumps(response)+'\nUse only the declared input slots, no extra cause or residual.'
    background={}
    for node in nodes:
        for uid in node['noise']:background[uid]={k:node[k] for k in ('type','values','bounds','observed') if k in node}
    model={'id':packet['case']['id']+'_alt%d'%alternative,'outcome':blueprint['outcome'],'nodes':nodes,'background':background,
           'outcome_definition':packet['case']['outcome'],'packet_sha256':packet['packet_sha256'],'alternative':alternative,
           'background_interpretation':'Fixed factual context; no identified probability measure','assumptions':blueprint.get('assumptions',[]),
           'construction_protocol':blueprint.get('protocol_version','legacy'),
           'principal_figure_size_target_met':len(nodes)>=10,
           'equation_protocol':'Per-node formal inputs; names substituted mechanically after generated AST validation.'}
    scm=SCM(model)
    return model,scm.diagnostics,failures
