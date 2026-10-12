"""Clustered evaluation: SCMs, not questions or paraphrases, are the units."""
import collections,csv,itertools,json,math
from pathlib import Path
import numpy as np
from .structural_programs import SCM,evaluate as expression_value
from .attribution import select_paths,coalitions,evidence_priority
from .budget import atomic_json


def ci(values,seed=2027,repeats=2000):
    values=np.asarray(values,dtype=float)
    if len(values)==0:return [None,None]
    rng=np.random.RandomState(seed)
    means=np.mean(values[rng.randint(0,len(values),size=(repeats,len(values)))],axis=1)
    return [float(x) for x in np.percentile(means,[2.5,97.5])]


def answer_map(method):
    if not isinstance(method,dict):return {}
    answers=method.get('answers',[])
    if isinstance(answers,dict):answers=[dict(id=k,values=v if isinstance(v,list) else [v]) for k,v in answers.items()]
    if not isinstance(answers,list):return {}
    return {a['id']:a for a in answers if isinstance(a,dict) and 'id' in a}


def score(case,method):
    predictions=answer_map(method);valid=[];identified=[];uncertain=[];cf=[]
    for q in case['queries']:
        answer=predictions.get(q['id'],{});values=answer.get('values');abstain=answer.get('abstain') is True or ('values' in answer and values is None)
        if isinstance(values,(int,bool)):values=[int(values)]
        if not isinstance(values,list):values=[]
        values=set(v for v in values if isinstance(v,(int,bool)) and v in (0,1));gold=set(q['gold_possible'])
        if q['identified']:
            correct=int(not abstain and values==gold);identified.append(correct)
            if q['kind'] in ('intervention','counterfactual','joint'):cf.append(correct)
        else:
            # A missing/failed answer is not an explicit uncertainty judgment.
            expressed=q['id'] in predictions and ('values' in answer or answer.get('abstain') is True)
            correct=int(expressed and (abstain or values=={0,1}));uncertain.append(correct)
        valid.append(correct)
    return {'score':float(np.mean(valid)),'identified_accuracy':float(np.mean(identified)) if identified else None,
            'uncertainty_handling':float(np.mean(uncertain)) if uncertain else None,
            'intervention_accuracy':float(np.mean(cf)) if cf else None,'answered':len(predictions),'query_count':len(case['queries'])}


def ndcg(ranking,relevant,k=5):
    gains=[relevant.get(x['segment_id'],0) for x in ranking[:k]]
    best=sorted(relevant.values(),reverse=True)[:k]
    dcg=sum(g/math.log2(i+2) for i,g in enumerate(gains));ideal=sum(g/math.log2(i+2) for i,g in enumerate(best))
    return dcg/ideal if ideal else None


def evaluate(root):
    root=Path(root);cases={c['id']:c for c in map(json.loads,(root/'benchmark/cases.jsonl').read_text().splitlines())}
    run=root/'runs'/json.loads((root/'configs/budget.json').read_text())['campaign_id']
    records=[json.loads(p.read_text()) for p in sorted((run/'benchmark').glob('*.json'))];rows=[];audit=[];attribution=[];extraction=[];ranking=[]
    for record in records:
        case=cases[record['id']]
        for name in ('B0','B1','B2','P'):
            s=score(case,record['methods'].get(name,{}))
            rows.append(dict(s,case_id=case['id'],scm_id=case['scm_id'],split=case['split'],size=case['size'],condition=case['condition'],variant=case['variant'],seed=record['seed'],method=name))
        attempts=record.get('attempts',[]);model=record['methods'].get('B2',{}).get('model')
        rate={'case_id':case['id'],'scm_id':case['scm_id'],'split':case['split'],'seed':record['seed'],'first_valid':bool(attempts and attempts[0].get('valid')),'eventual_valid':bool(model),'repairs':max(0,len(attempts)-1)}
        if model:
            gold_edges={(p,n['id']) for n in case['gold']['nodes'] for p in n['parents']};pred_edges={(p,n['id']) for n in model['nodes'] for p in n['parents']}
            rate.update(edge_precision=len(gold_edges&pred_edges)/max(1,len(pred_edges)),edge_recall=len(gold_edges&pred_edges)/max(1,len(gold_edges)),event_id_recall=len({n['id'] for n in model['nodes']}&{n['id'] for n in case['gold']['nodes']})/case['size'])
            # Source references are checked against frozen renderer segments, not trusted as event entailment.
            source_ids={s['id'] for s in case['segments']};citations=[s for n in model['nodes'] for s in n.get('segments',[])]
            rate['source_reference_validity']=sum(s in source_ids for s in citations)/max(1,len(citations))
            inferred=SCM(model);specified=[]
            for gold_node in case['gold']['nodes']:
                if not gold_node['parents'] or gold_node['id'] in case['hidden_nodes']:continue
                node=inferred.nodes[gold_node['id']]
                equivalent=set(node['parents'])==set(gold_node['parents']) and not node.get('noise')
                if equivalent:
                    for values in itertools.product((0,1),repeat=len(gold_node['parents'])):
                        setting=dict(zip(gold_node['parents'],values))
                        if expression_value(node['expr'],setting,inferred.u)!=expression_value(gold_node['expr'],setting,{}):
                            equivalent=False;break
                specified.append(equivalent)
            rate['specified_nonroot_function_agreement']=sum(specified)/max(1,len(specified))
            rate['unsupported_specified_rules']=len(specified)-sum(specified)
            rate['specified_nonroot_rules']=len(specified)
            rate['unexplained_internal_backgrounds']=sum(bool(n['parents'] and n.get('noise')) for n in model['nodes'])
            paths=record.get('paths',{}).get('paths',[]);attr=record.get('attribution')
            if attr:
                attribution.append({'case_id':case['id'],'scm_id':case['scm_id'],'split':case['split'],'seed':record['seed'],**{k:attr[k] for k in ['contrast','efficiency_residual','naive_sum','naive_residual','unique_edge_masks']}})
                edges={p+'>'+n['id']:{'score':0 if n.get('unknown') else 1,'segments':n.get('segments',[])} for n in model['nodes'] for p in n['parents']}
                weighted=evidence_priority(paths,attr,edges);uniform=evidence_priority(paths,attr,edges,uniform=True)
                # Controlled support labels: a source states an actual gold edge on an influential retained path.
                relevance={s['id']:0 for s in case['segments']}
                for path,value in zip(paths,attr['phi']):
                    if not value:continue
                    for a,b in zip(path,path[1:]):
                        if (a,b) in gold_edges and b not in case['hidden_nodes']:relevance['seg_'+b]=1
                ranking.append({'case_id':case['id'],'scm_id':case['scm_id'],'split':case['split'],'seed':record['seed'],'P_ndcg5':ndcg(weighted['segments'],relevance),'A1_ndcg5':ndcg(uniform['segments'],relevance),'interpretation':'Known support labels conditioned on generated influential paths; not a gold causal-importance ranking'})
        extraction.append(rate)
    summary=[]
    for split in ('development','calibration','test'):
        for condition in ('complete','incomplete','all'):
            for method in ('B0','B1','B2','P'):
                subset=[r for r in rows if r['split']==split and r['method']==method and r['seed']==2027 and (condition=='all' or r['condition']==condition)]
                clusters=collections.defaultdict(list)
                for row in subset:clusters[row['scm_id']].append(row['score'])
                means=[np.mean(v) for v in clusters.values()]
                if means:summary.append({'split':split,'condition':condition,'method':method,'independent_scms':len(means),'narratives':len(subset),'score':float(np.mean(means)),'ci_low':ci(means)[0],'ci_high':ci(means)[1]})
    paired=[]
    for condition in ('complete','incomplete','all'):
        for a,b in [('B2','B0'),('B2','B1'),('P','B0'),('P','B2')]:
            groups=collections.defaultdict(lambda:collections.defaultdict(list))
            for row in rows:
                if row['split']=='test' and row['seed']==2027 and (condition=='all' or row['condition']==condition):groups[row['scm_id']][row['method']].append(row['score'])
            diffs=[float(np.mean(v[a])-np.mean(v[b])) for v in groups.values() if a in v and b in v]
            if diffs:paired.append({'condition':condition,'comparison':a+'-'+b,'n_scms':len(diffs),'difference':float(np.mean(diffs)),'ci':ci(diffs)})
    def write_csv(path,data):
        with open(path,'w',newline='') as file:
            if data:
                keys=list(dict.fromkeys(k for r in data for k in r));w=csv.DictWriter(file,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(data)
    write_csv(root/'results/metrics.csv',rows);write_csv(root/'results/method_comparison.csv',summary)
    write_csv(root/'results/extraction.csv',extraction);write_csv(root/'results/path_diagnostics.csv',attribution);write_csv(root/'results/evidence_ranking.csv',ranking)
    application=[]
    for path in sorted((run/'application').glob('*/alternative_*.json')):
        record=json.loads(path.read_text());model=record['model'];attr=record['attribution'];case=record['case']['id'];nodes=model['nodes'];edges=record['edge_evidence']
        application.append({'case':case,'alternative':model['alternative'],'nodes':len(nodes),'principal_figure_size_target_met':len(nodes)>=10,'edges':sum(len(n['parents']) for n in nodes),'node_types':dict(collections.Counter(n['type'] for n in nodes)),
                            'paths':len(record['selection']['paths']),'path_edge_coverage':record['selection']['edge_coverage'],'baseline':attr['baseline'],'full':attr['full'],'sum_phi':sum(attr['phi']),'efficiency_residual':attr['efficiency_residual'],
                            'naive_sum':attr['naive_sum'],'naive_residual':attr['naive_residual'],'unsupported_edges':sum(e.get('status') in ('unsupported','unassessed') for e in edges.values()),'queries':len(record['queries']),
                            'alternative_reference_phi_l1':sum(abs(a-b) for a,b in zip(attr['phi'],record['reference_sensitivity']['domain_endpoint_alternative']['phi']))})
        for entry in record['source_audit']:
            audit.append(dict(case=case,alternative=model['alternative'],record_type='event',**entry))
        for edge_id,entry in edges.items():
            audit.append({'case':case,'alternative':model['alternative'],'record_type':'mechanism','edge_id':edge_id,'support_score':entry['score'],'segments':';'.join(entry.get('segments',[])),'status':entry.get('status'),
                          'event_support':entry.get('event_support'),'mechanism_support':entry.get('reason'),'mechanism_explicitness':entry.get('mechanism_explicitness'),'temporal_compatibility':entry.get('temporal_compatibility'),
                          'independent_corroboration':entry.get('independent_corroboration'),'contradiction':entry.get('contradiction')})
    write_csv(root/'results/source_audit.csv',audit);write_csv(root/'results/application_summary.csv',application)
    repeated=collections.defaultdict(dict)
    repeated_ids={r['scm_id'] for r in rows if r['seed']!=2027}
    for row in rows:
        if row['scm_id'] in repeated_ids and row['variant']==0:
            repeated[(row['scm_id'],row['method'])][row['seed']]=row['score']
    seed_rows=[{'scm_id':ident,'method':method,'seeds':len(scores),
                'mean_score':float(np.mean(list(scores.values()))),
                'min_score':min(scores.values()),'max_score':max(scores.values()),
                **{'seed_'+str(seed):value for seed,value in sorted(scores.items())}}
               for (ident,method),scores in sorted(repeated.items())]
    write_csv(root/'results/seed_robustness.csv',seed_rows)
    result={'method_comparison':summary,'paired_test_differences':paired,'records_completed':len(records),'unique_scms':len({r['scm_id'] for r in records}),'first_valid':sum(r['first_valid'] for r in extraction),'eventual_valid':sum(r['eventual_valid'] for r in extraction),'application':application,
            'bootstrap':'2000 percentile resamples of independent SCMs; both text variants averaged within SCM; seed=2027; primary inference seed only',
            'limitations':['Synthetic intervention accuracy does not validate literary causality.','Incomplete-query compatible families assume deterministic binary local mechanisms and declared parents.','Evidence weights are heuristic and not causal probabilities.','No human validation or comprehension study.']}
    atomic_json(root/'results/summary.json',result)
    return result

if __name__=='__main__':
    import sys
    r=evaluate(sys.argv[1] if len(sys.argv)>1 else '.');print('Evaluated',r['records_completed'],'records')
