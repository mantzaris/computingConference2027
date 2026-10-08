"""Compact coverage, actual device accounting and sensitivity evidence."""
import json
from pathlib import Path
import sqlite3
import time
import numpy as np
import pandas as pd
from sem_update.phase3.runtime import root,RESULTS,read_json,atomic_json,file_hash,snapshot,freeze_guard
from sem_update.phase3.reporting import bootstrap,METHODS

def main():
    protocol=freeze_guard();frozen=read_json(RESULTS/'frozen_selections.json');cfg=protocol['config']
    frame=pd.read_csv(RESULTS/'metrics.csv');assert 'endpoint' not in frame
    primary=frame[frame.sensitivity=='primary'];coverage=[]
    for resource in ('fixed','adjusted'):
        for (d,family,profile),tasks in pd.DataFrame(protocol['tasks']).groupby(['d','family','profile']):
            tasks=tasks[tasks.get('sensitivity',pd.Series('primary',index=tasks.index)).fillna('primary')=='primary']
            for method in METHODS+['fixed','random','oracle']:
                eligible=tasks[tasks.oracle] if method=='oracle' else tasks
                rows=primary[(primary.d==d)&(primary.family==family)&(primary.profile==profile)&(primary.resource==resource)&(primary.method==method)]
                coverage.append({'d':d,'family':family,'profile':profile,'resource':resource,'method':method,
                    'planned_scms':len(eligible),'observed_scms':rows.scm.nunique(),'planned_conditions':len(eligible)*len(cfg['corruptions']),
                    'valid_predictions':len(rows),'strict_converged':int((rows.status=='converged').sum()) if method=='M2' else None,
                    'valid_capped_predictions':int((rows.status=='valid_capped_prediction').sum()),
                    'legacy_stop_not_strict':int((rows.status=='valid_legacy_stop_not_strict').sum()),
                    'missing_predictions':len(eligible)*len(cfg['corruptions'])-len(rows)})
    pd.DataFrame(coverage).to_csv(RESULTS/'coverage.csv',index=False)
    # Preserve the actual relation between soft acyclicity, threshold projection
    # and valid prediction; never turn an implementation failure into a loss.
    discoveries=[]
    for p in sorted((root()/'runs').glob('*-discovery.json')):
        v=read_json(p);task=v['identity']['task'] if 'task' in v.get('identity',{}) else None
        # Stage wrappers retain the discoverer's identity; infer source task from
        # the pipeline completion manifests, without reading hidden outcomes.
        matches=[t for t in protocol['tasks'] if f"-s{t['seed']}-B{t.get('budget',cfg['budget_per_target'])}-discovery.json" in p.name]
        if not matches:continue
        t=matches[0]
        discoveries.append({'scm':t['seed'],'d':t['d'],'family':t['family'],'profile':t['profile'],
            'budget':t.get('budget',cfg['budget_per_target']),'sensitivity':t.get('sensitivity','primary'),
            'seconds':v['seconds'],'steps':v['optimization_steps'],'status':v['status'],'stop_reason':v.get('stop_reason'),
            'h_per_node':v['h_per_node'],'h_legacy':v['h_normalized'],'threshold_acyclic':v.get('threshold_acyclic'),
            'threshold_edges':v.get('threshold_edges'),'projected_edges':len(v['graph']['edges']),
            'removed_cycles':sum(e['reason']=='cycle' for e in v.get('projection_details',[])),
            'removed_indegree':sum(e['reason']=='indegree' for e in v.get('projection_details',[])),
            'stage_peak_bytes':v['stage_peak_bytes']})
    pd.DataFrame(discoveries).to_csv(RESULTS/'discovery.csv',index=False,float_format='%.7g')
    execution=[]
    for (scm,budget),rows in frame.groupby(['scm','budget']):
        stages={}
        for p in (root()/'runs').glob(f'*-s{scm}-B{budget}-*.json'):
            value=read_json(p)
            if 'stage_seconds' not in value:continue
            suffix=p.stem.split(f'-B{budget}-',1)[1]
            category=('selection_all_controls' if suffix.endswith('-select') else
                'diagnostic_banks' if suffix.endswith('-diagnostic') else
                'random_banks' if suffix.endswith('-random') else
                'discovery' if suffix=='discovery' else 'common_refit' if suffix=='dcdi-refit' else 'other')
            stages[category]=stages.get(category,0.)+value['stage_seconds']
        unique=rows.drop_duplicates('prediction_key')
        execution.append({'scm':scm,'budget':budget,'d':int(rows.d.iloc[0]),'profile':rows.profile.iloc[0],
            **{'actual_stage_'+k+'_seconds':v for k,v in stages.items()},
            'actual_unique_prediction_generation_seconds':unique.inference_seconds.sum(),
            'actual_unique_prediction_metric_seconds':unique.metric_seconds.sum(),
            'unique_selected_predictions':len(unique),
            **{'logical_'+method+'_seconds':rows[rows.method==method].logical_seconds.sum() for method in ('M3','M4','M5')},
            'policy_conditions':len(rows[rows.method=='M3']),
            'bank_charge_per_repair_method_seconds':(rows[rows.method=='M3'].logical_seconds-rows[rows.method=='M3'].selection_seconds).sum()})
    pd.DataFrame(execution).to_csv(RESULTS/'execution_sharing.csv',index=False,float_format='%.7g')
    # Projection sensitivity uses the same generated observations, on the
    # prespecified oracle/first-replicate subset only.
    projections=[]
    for (d,profile,method),rows in primary[(primary.resource=='adjusted')&primary.method.isin(METHODS+['fixed','oracle'])].groupby(['d','profile','method']):
        rows=rows.dropna(subset=['sw1_64','sw1_1024'])
        if not len(rows):continue
        projections.append({'d':d,'profile':profile,'method':method,'scms':rows.scm.nunique(),'conditions':len(rows),
            'SW64':rows.sw1_64.mean(),'SW256':rows.sw1.mean(),'SW1024':rows.sw1_1024.mean(),
            'mean_abs_change64':(rows.sw1_64-rows.sw1).abs().mean(),'mean_abs_change1024':(rows.sw1_1024-rows.sw1).abs().mean()})
    pd.DataFrame(projections).to_csv(RESULTS/'projection_sensitivity.csv',index=False,float_format='%.7g')
    sensitivity=frame[frame.sensitivity!='primary'];paired=[]
    for r in sensitivity.itertuples():
        match=primary[(primary.scm==r.scm)&(primary.corruption==r.corruption)&(primary.resource==r.resource)&(primary.method==r.method)]
        if len(match)!=1:continue
        b=match.iloc[0];paired.append({'scm':r.scm,'d':r.d,'method':r.method,'resource':r.resource,'corruption':r.corruption,
            'fixed_total_budget':r.intervention_rows,'primary_budget':b.intervention_rows,
            'fixed_total_sw1':r.sw1,'primary_sw1':b.sw1,'delta':r.sw1-b.sw1,'fixed_total_descendant_w1':r.descendant_w1,
            'primary_descendant_w1':b.descendant_w1})
    pd.DataFrame(paired).to_csv(RESULTS/'budget_sensitivity.csv',index=False,float_format='%.7g')
    # One-device union accounting, versus summed overlapping per-job wall time.
    book=snapshot();db=sqlite3.connect(root()/'ledger.sqlite')
    intervals=pd.read_sql_query("SELECT job,start,end FROM intervals WHERE job LIKE 'phase3-%'",db);db.close()
    assert intervals.end.notna().all(),'Final accounting requires quiescent GPU jobs'
    failures=[r for r in book['jobs'] if r['status']!='complete']
    failed_attempts=[]
    for path in sorted((root()/'logs').glob('failure-*.json')):
        value=read_json(path)
        failed_attempts.append({'job':value['job'],'utc':value.get('utc'),
            'error':value['traceback'].strip().splitlines()[-1],
            'artifact':str(path.relative_to(root())),'sha256':file_hash(path)})
    telemetry=root()/'logs/device_telemetry.csv';physical={}
    if telemetry.exists():
        gpu=pd.read_csv(telemetry)
        physical={'samples':len(gpu),'period_seconds':15,'maximum_observed_used_mib':float(gpu.used_mib.max()),
            'median_gpu_utilization_percent':float(gpu.gpu_percent.median()),'p95_gpu_utilization_percent':float(gpu.gpu_percent.quantile(.95)),
            'scope':'Sampled device-wide usage including CUDA contexts and concurrent jobs; not an exact continuous peak'}
    actual={'historical_device_hours':book['historical_gpu_seconds']/3600,'phase3_device_hours':book['phase3_gpu_seconds']/3600,
        'cumulative_device_hours':book['cumulative_gpu_seconds']/3600,'additional_cap_hours':book['additional_cap_seconds']/3600,
        'summed_overlapping_interval_hours':float((intervals.end-intervals.start).sum()/3600),
        'wall_span_hours_including_idle_gaps':float((intervals.end.max()-intervals.start.min())/3600),
        'completed_jobs':sum(r['status']=='complete' for r in book['jobs']),'failures':failures,'device_telemetry':physical,
        'retained_failed_attempts':failed_attempts,
        'retried_jobs':[{'id':r['id'],'attempts':r['attempts'],'final_status':r['status']} for r in book['jobs'] if r['attempts']>1],
        'main_training_failure_records':frozen['failure_records'],
        'logical_cost':'Each M3/M4/M5 includes its entire canonical bank plus own selection/audit; inference and metric time are separate columns.',
        'grouped_fit_cost':'Measured group time apportioned by active optimizer updates, reused once per unique node/parent set; not hypothetical serial execution time.',
        'concurrency':'Single physical device; overlapping intervals unioned. Per-job wall times can include contention.',
        'peak_allocation_bytes':int(frame.peak_vram_bytes.max()),'incomplete_tasks':frozen['incomplete_tasks']}
    atomic_json(RESULTS/'compute.json',actual)
    # Strict-convergence sensitivity can be empty; preserve that limitation.
    strict=primary[(primary.method=='M2')&(primary.status=='converged')][['scm','corruption','resource']]
    matched=primary.merge(strict,on=['scm','corruption','resource'])
    rows=[]
    for (d,resource,method),part in matched.groupby(['d','resource','method']):
        mean,lo,hi,n=bootstrap(part,'sw1');rows.append({'d':d,'resource':resource,'method':method,'scms':n,'conditions':len(part),'mean':mean,'low':lo,'high':hi})
    pd.DataFrame(rows,columns=['d','resource','method','scms','conditions','mean','low','high']).to_csv(RESULTS/'strict_dcdi_sensitivity.csv',index=False,float_format='%.7g')
    print(json.dumps({'completed_scms':primary.scm.nunique(),'completed_conditions':len(primary[primary.method=='M0'])//2,
        'phase3_device_hours':actual['phase3_device_hours'],'incomplete_tasks':len(frozen['incomplete_tasks'])},indent=2))

if __name__=='__main__':main()
