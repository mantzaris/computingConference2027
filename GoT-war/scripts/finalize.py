"""Create measured results, content hashes and usage accounting from durable records."""
import collections,csv,hashlib,itertools,json,math,os,platform,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from got_war.evaluation import evaluate
from got_war.diagnostics import analyze
from got_war.application_analysis import analyze as application_analysis
from got_war.seed_analysis import analyze as seed_analysis
from got_war.budget import atomic_json
from got_war.structural_programs import SCM,domain,evaluate as eval_expression
from got_war.attribution import coalitions
ROOT=Path(__file__).resolve().parents[1]

def summarize():
    summary=evaluate(ROOT);diagnostic=analyze(ROOT);app_audit=application_analysis(ROOT);seed_results=seed_analysis(ROOT);budget=json.loads((ROOT/'configs/budget.json').read_text());run=ROOT/'runs'/budget['campaign_id']
    # The compact release includes request timing/count metadata, without the
    # bulky raw response log. Both ledgers produce the same usage aggregates.
    ledger=run/'usage_ledger.jsonl'
    logs=[json.loads(s) for s in (ledger if ledger.exists() else run/'requests.jsonl').read_text().splitlines() if s]
    roles=collections.defaultdict(lambda:{'requests':0,'seconds':0.,'input_tokens':0,'output_tokens':0,'failed':0})
    latencies=collections.defaultdict(list);decode_rates=collections.defaultdict(list)
    for r in logs:
        s=roles[r['role']];s['requests']+=1;s['seconds']+=r['elapsed_seconds'];s['input_tokens']+=r['input_tokens'];s['output_tokens']+=r['output_tokens'];s['failed']+=bool(r['error'])
        latencies[r['role']].append(r['elapsed_seconds'])
        if r.get('decode_tokens_per_second'):decode_rates[r['role']].append(r['decode_tokens_per_second'])
    for role,s in roles.items():
        s['latency_p50_seconds']=float(np.median(latencies[role]));s['latency_p90_seconds']=float(np.percentile(latencies[role],90))
        s['median_decode_tokens_per_second']=float(np.median(decode_rates[role])) if decode_rates[role] else None
    samples=[]
    if (run/'gpu_samples.jsonl').exists():
        for line in (run/'gpu_samples.jsonl').read_text().splitlines():
            try:
                item=json.loads(line);values=[float(v.strip()) for v in item['sample'].split(',')];samples.append((datetime.fromisoformat(item['at']).timestamp(),*values))
            except (ValueError,KeyError):pass
    active_hours=0
    for i in range(1,len(samples)):
        dt=min(120,samples[i][0]-samples[i-1][0]);active_hours+=dt*(samples[i-1][2]+samples[i][2])/200/3600
    registry=json.loads((run/'processes.json').read_text());servers=[x for x in registry if x['label']=='model_server_ready']
    now=datetime.now(timezone.utc)
    completion=run/'completion.json'
    finished=json.loads(completion.read_text())['finished_at'] if completion.exists() else now.isoformat()
    end=datetime.fromisoformat(finished)
    inference_end=run/'inference_finished.json'
    service_end=datetime.fromisoformat(json.loads(inference_end.read_text())['service_stopped_at']) if inference_end.exists() else end
    usage={'started_at':budget['started_at'],'measured_through':end.isoformat(),'elapsed_hours':(end-datetime.fromisoformat(budget['started_at'])).total_seconds()/3600,
           'requests':len(logs),'input_tokens':sum(r['input_tokens'] for r in logs),'output_tokens':sum(r['output_tokens'] for r in logs),
           'sum_request_hours':sum(r['elapsed_seconds'] for r in logs)/3600,'request_hours_warning':'Overlapping request durations are not additive GPU wall time.',
           'model_service_resident_hours':(service_end-datetime.fromisoformat(servers[0]['started_at'])).total_seconds()/3600 if servers else None,
           'sampled_utilization_weighted_gpu_hours':active_hours,'utilization_sampling_note':'Approximate trapezoidal integration of nvidia-smi utilization; gaps capped at 120 s. Not billed GPU hours.',
           'peak_sampled_vram_mib':max((s[1] for s in samples),default=None),'gpu_samples':len(samples),'roles':dict(roles),'billing_cost':None,
           'failed_requests':sum(bool(r['error']) for r in logs),'deadline_status':'within immutable ceiling' if end<=datetime.fromisoformat(budget['hard_deadline']) else 'deadline exceeded'}
    counter_path=run/'service_counters.json'
    if counter_path.exists():
        counters=json.loads(counter_path.read_text())
        usage['server_counters']=counters
        usage['total_output_tokens_from_server']=counters['values'].get('vllm:generation_tokens_total')
        usage['output_token_caveat']='Completed response usage undercounts interrupted streams; the project server cumulative counter is the preferred total when available.'
    atomic_json(ROOT/'results/usage.json',usage)
    # Fixed-seed paired MC error and structural variability are retained per model.
    model_files=sorted((run/'application').glob('*/alternative_*.json'))
    diversity=collections.defaultdict(list)
    for path in model_files:
        record=json.loads(path.read_text());scm=SCM(record['model']);signature=[];exact=True
        for ident in scm.order:
            node=scm.nodes[ident];parents=node['parents'];noises=node.get('noise',[])
            specs=[scm.nodes[p] for p in parents]+[scm.background[u] for u in noises]
            exact &= all(s['type'] in ('bool','category') or (s['type']=='int' and s['bounds'][1]-s['bounds'][0]<=15) for s in specs)
            domains=[domain(s) for s in specs]
            outputs=[]
            if math.prod(len(d) for d in domains)>4096:
                exact=False;outputs=[node['expr']]
            else:
                for values in itertools.product(*domains):outputs.append(eval_expression(node['expr'],dict(zip(parents,values[:len(parents)])),dict(zip(noises,values[len(parents):]))))
            signature.append([ident,parents,noises,outputs])
        diversity[record['case']['id']].append({'alternative':record['model']['alternative'],'signature_sha256':hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest(),'exhaustive_local_domains':bool(exact)})
    atomic_json(ROOT/'results/model_diversity.json',[{'case':case,'accepted_generations':len(items),'distinct_function_signatures':len({x['signature_sha256'] for x in items}),'models':items,'interpretation':'Repeated identical mechanisms are not independent models or independent evidence.'} for case,items in diversity.items()])
    sensitivities=[]
    for path in model_files:
        r=json.loads(path.read_text());scm=SCM(r['model'])
        boundary_do={n:scm.nodes[n]['reference'] for n in r['selection']['source_boundary']}
        reference_world=scm.solve(interventions=boundary_do)
        coherent=coalitions(scm,r['selection']['paths'],references={(a,b):reference_world[a] for a,b in scm.graph.edges},exact=r['attribution']['method']=='exact')
        sensitivities.append({'case':r['case']['id'],'alternative':r['model']['alternative'],'model':r['model']['id'],'paths':r['selection']['paths'],'phi':r['attribution']['phi'],'mc_se':r['attribution']['mc_se'],'reference_phi':r['reference_sensitivity']['domain_endpoint_alternative']['phi'],
                              'coherent_boundary_reference':{'boundary_intervention':boundary_do,'reference_states':reference_world,'attribution':coherent,'interpretation':'Inactive-edge reference inputs are taken from the model world obtained by jointly setting source-boundary events to their declared references. Coalition execution still uses the original factual background. This is a model-derived comparison policy, not an observed historical alternative.'},
                              'weakest_link_priority':r['evidence_priority']['segments'],'uniform_priority':r['uniform_priority']['segments'],'geometric_priority':r['geometric_priority']['segments'],'raw_score_priority':r.get('raw_score_priority',{}),'disjoint_groups':r['disjoint_groups'],'recombined_routes':r['attribution']['recombined_routes']})
    atomic_json(ROOT/'results/sensitivity.json',sensitivities)
    path_rows=[];segment_rows=[];unsupported=[]
    for path in model_files:
        record=json.loads(path.read_text());model=record['model'];names={n['id']:n['label'] for n in model['nodes']}
        for i,p in enumerate(record['evidence_priority']['paths']):
            row={'case':record['case']['id'],'alternative':model['alternative'],'path_id':p['path_id'],'nodes':' > '.join(p['nodes']),'labels':' > '.join(names[x] for x in p['nodes']),
                 'weakest_link_support':p['evidence_support'],'signed_contribution':p['signed_contribution'],'permutation_mc_se':record['attribution']['mc_se'][i],
                 'reference_outcome':record['attribution']['baseline'],'full_outcome':record['attribution']['full'],'source_segments':';'.join(p['segment_allocation']),
                 'allocation':json.dumps(p['segment_allocation'],sort_keys=True),
                 'unsupported_or_unassessed_edges':';'.join(a+'>'+b for a,b in zip(p['nodes'],p['nodes'][1:]) if record['edge_evidence'].get(a+'>'+b,{}).get('status','unassessed') in ('unsupported','unassessed'))}
            path_rows.append(row)
            if abs(p['signed_contribution'])>1e-12 and (p['evidence_support']<.5 or row['unsupported_or_unassessed_edges']):unsupported.append(row)
        for row in record['evidence_priority']['segments']:segment_rows.append(dict(case=record['case']['id'],alternative=model['alternative'],**row))
    for name,data in [('causal_paths.csv',path_rows),('segment_priorities.csv',segment_rows),('influential_weak_support.csv',unsupported)]:
        with open(ROOT/'results'/name,'w',newline='') as file:
            if data:
                writer=csv.DictWriter(file,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)

    stability=[]
    by_case=collections.defaultdict(list)
    for item in sensitivities:by_case[item['case']].append(item)
    for case,items in by_case.items():
        canonical={tuple(p):[] for item in items for p in item['paths']}
        for item in items:
            for path,value in zip(item['paths'],item['phi']):canonical[tuple(path)].append(value)
        envelopes=[{'path':list(path),'min':min(values),'max':max(values),'models':len(values)} for path,values in canonical.items() if len(values)==len(items)]
        rank_changes=[]
        for item in items:
            weighted={x['segment_id'] for x in item['weakest_link_priority'][:5] if x['priority']>0}
            uniform={x['segment_id'] for x in item['uniform_priority'][:5] if x['priority']>0}
            geometric={x['segment_id'] for x in item['geometric_priority'][:5] if x['priority']>0}
            rank_changes.append({'alternative':item['alternative'],'weighted_ranking_informative':bool(weighted),'uniform_top5_jaccard':len(weighted&uniform)/max(1,len(weighted|uniform)) if weighted else None, 'geometric_top5_jaccard':len(weighted&geometric)/max(1,len(weighted|geometric)) if weighted else None})
        stability.append({'case':case,'accepted_generations':len(items),'distinct_function_signatures':len({x['signature_sha256'] for x in diversity[case]}),'aligned_model_count':len(items),'aligned_path_envelopes':envelopes,'ranking_sensitivity':rank_changes,'interpretation':'Envelopes over retained generated mechanisms, not confidence intervals or probabilities. Identical functions do not supply independent model diversity.'})
    atomic_json(ROOT/'results/stability.json',stability)
    rows=[r for r in summary['method_comparison'] if r['split']=='test' and r['condition']=='all']
    lines=['# Measured results','',f"Completed {summary['records_completed']} text/seed records from {summary['unique_scms']} independent generating SCMs. Test variants are averaged within SCM before bootstrap; missing/failed models count as failures.",'', '| Method | Test SCMs | Mean query score | 95% SCM bootstrap interval |','| --- | ---: | ---: | --- |']
    for row in rows:lines.append('| {method} | {independent_scms} | {score:.4f} | [{ci_low:.4f}, {ci_high:.4f}] |'.format(**row))
    lines+=['','Scores combine identified-query correctness and appropriate uncertainty handling on incomplete records. They are not narrative probability estimates. Separate intervention accuracy and uncertainty metrics are in metrics.csv.','',f"Admissible generation: {summary['first_valid']} initial, {summary['eventual_valid']} after bounded repairs, out of {summary['records_completed']} records.",'','## Paired differences']
    for row in summary['paired_test_differences']:
        if row['condition']=='all':lines.append('- %s: %.4f, 95%% interval [%.4f, %.4f], %d SCMs.'%(row['comparison'],row['difference'],*row['ci'],row['n_scms']))
    lines+=['','The overall P–B0 interval includes zero. These data do not establish overall superiority to direct prompting. Mechanism completeness changes the result:']
    for row in summary['paired_test_differences']:
        if row['comparison']=='B2-B0' and row['condition']!='all':lines.append('- %s: B2–B0 %.4f [%.4f, %.4f].'%(row['condition'],row['difference'],*row['ci']))
    lines+=['',f"A1 evidence weighting had mean nDCG@5 difference {diagnostic['A1']['paired_ndcg5_difference']:.4f} versus uniform weights; its interval includes zero. Labels measure rule availability conditional on generated paths, not gold causal importance.",
            f"A2 naive path summation failed to reconstruct the contrast on {diagnostic['A2']['nonzero_naive_residual']}/{diagnostic['A2']['admitted_test_texts']} admissible test texts; maximum absolute residual {diagnostic['A2']['max_absolute_naive_residual']:.1f}. Coalition efficiency residuals were zero in this controlled evaluation.",
            'Post-hoc query diagnostics expose a benchmark weakness: all 43 identified structural queries in the incomplete condition retain the factual outcome; 47 further queries are ambiguous. Factual carry-forward is perfect on that identified subset. This is a different denominator from the main score and was not a predeclared baseline.',
            '',f"Seed sensitivity: {seed_results['completed_records']}/{seed_results['planned_records']} planned original-text records across {seed_results['planned_scms']} SCMs and three seeds are available. {seed_results['fully_repeated_scms']} SCMs have all seeds. See seed_robustness_summary.json; these repetitions do not increase the number of independent SCMs."]
    lines+=['','## Application construction and attribution','', '| Conflict / alternative | Nodes | Edges | Paths | Reference → full | Sum of shares | Naive sum |','| --- | ---: | ---: | ---: | --- | ---: | ---: |']
    for row in summary['application']:lines.append('| {case} / {alternative} | {nodes} | {edges} | {paths} | {baseline:.3f} → {full:.3f} | {sum_phi:.3f} | {naive_sum:.3f} |'.format(**row))
    lines+=['','Only the Five Kings network reaches ten nodes. The northern and Daenerys models contain eight and three nodes. Accepted generations yield only one distinct functional model per case; the two Five Kings generations are equivalent. Three diverse alternatives per case were not obtained.',
            'All principal paths have zero weakest-link support because each includes an unsupported mechanism. Consequently all weighted segment priorities are zero; alphabetical zero-score ties are not a meaningful ranking. Exact path allocation remains an accounting property of assumed equations.',
            '', '| Case | Unsupported edges | Positive-support paths | Trace-audit passes |','| --- | ---: | ---: | ---: |']
    for row in app_audit['cases']:
        unsupported_count=sum(row['mechanism_assessments'].get(s,0) for s in ('unsupported','unassessed'))
        lines.append('| %s | %d/%d | %d | %d/%d |'%(row['case'],unsupported_count,row['edges'],row['positively_supported_paths'],row['explanations_passing_automatic_check'],row['explanations_audited']))
    lines+=['','The northern model generates “Edmure Tully (the Blackfish)” although that personal name is absent from its entire frozen packet. The same-model reviewer accepted it. The retained alias flag demonstrates a grounding/audit failure; no corrected identity or new causal rule was supplied by the analyst. Source critiques also leave chronology and reference-state questions unresolved. Failed prose is withheld; numerical execution traces remain available.']
    lines+=['','Literary values are fixed-background model contrasts. They do not measure war probabilities, natural path-specific effects, or objective responsibility. Source spans are mechanically verified; event entailment and counterfactual mechanisms have not received independent human review. Mechanism support is assessed separately from event support.','',
            'Reference, evidence-summary, uniform-weight, model-alternative and disjoint-group results are retained in sensitivity.json and individual model records. Path IDs must only be compared across alternatives when their node sequences align. No averaging across incompatible path collections is performed.','',
            '## Runtime and failures','',f"Elapsed campaign time through {usage['measured_through']}: {usage['elapsed_hours']:.3f} hours. GPU service residency: {usage['model_service_resident_hours']:.3f} hours. Peak sampled VRAM: {usage['peak_sampled_vram_mib']} MiB. Requests: {usage['requests']}; completed-response output tokens: {usage['output_tokens']}; server cumulative generated tokens: {usage.get('total_output_tokens_from_server', 'unavailable')}. The latter includes interrupted streams where counted. Billing cost unavailable.",'',
            f"{usage['failed_requests']} API/JSON requests failed; validation failures are additionally preserved with candidates. Startup failures involved tokenizer compatibility and an inherited optional downloader setting. The initial application blueprint protocol failed; its results remain in application_v1, and both the constrained-schema and modular revisions are documented in DECISIONS.md.",'',
            '## Limitations and unfinished work','',
            '- Robert\'s Rebellion was replaced with the northern campaign against Bolton rule at the source gate; accessible evidence did not establish enough onset mechanisms.',
            '- Sources are secondary television episode summaries from one dependent editorial family; no full primary transcript corpus was available.',
            '- No human review, reader study, probability calibration, or paid external inference was used.',
            '- A second model, full independent application seed repetitions, evidence-guided selection ablation, and an interactive explorer were not run. The controlled seed subset is reported above.',
            '- Twelve canonical intervention questions per retained Five Kings/northern model were executed; the three-node Daenerys model provides only three distinct single/pair interventions and falls short of the question target.',
            '- The benchmark is a bounded Boolean family with explicit deterministic prose. It does not prove identification or open-domain causal reasoning.',
            '- Free-form generated explanations remain subject to semantic review even where structured number/path checks pass.',
            '- The anonymous manuscript is a researcher-review scaffold and must not be submitted without human scientific responsibility and conference-policy review.']
    (ROOT/'results/RESULTS.md').write_text('\n'.join(lines)+'\n')
    # Never scan local archives into a public manifest. The release checker
    # supplies the explicitly staged paths; this run manifest stays local.
    release=ROOT/'results/artifact_manifest.json'
    public=json.loads(release.read_text())['files'] if release.exists() else {}
    checks={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in public if (ROOT/name).is_file()}
    try:code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:code_commit=None
    manifest={'campaign_id':budget['campaign_id'],'budget':budget,'environment':json.loads((run/'environment.json').read_text()) if (run/'environment.json').exists() else None,
              'usage':usage,'code_commit':code_commit,'artifact_sha256':checks,
              'seed_policy':'Primary controlled seed 2027; per-repair deterministic offsets; application schema-revision seeds 2127-2129 and mechanism alternatives 2027-2029, all request-level seeds retained.',
              'source_corpus':json.loads((ROOT/'data/manifests/corpus_freeze.json').read_text()),'finished':completion.exists()}
    atomic_json(run/'manifest.json',manifest)
    return usage

if __name__=='__main__':print(json.dumps(summarize(),indent=2))
