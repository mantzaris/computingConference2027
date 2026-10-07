"""Prespecified supplementary comparisons; independent SCMs remain the units."""
import pandas as pd
from .runtime import PROJECT
from .evaluation import paired_results,cluster_interval

def supplementary_tables(frame):
    selected=frame[(frame.stage=='selected')&(frame.endpoint=='T2')]
    columns=['study','d','family','budget','corruption','metadata_variant','method']
    method=selected.groupby(columns,dropna=False).agg(
        independent_scms=('seed','nunique'),sw1_mean=('sw1','mean'),sw1_sd=('sw1','std'),
        sw1_min=('sw1','min'),sw1_max=('sw1','max'),candidate_mean=('candidate_count','mean'),
        wall_seconds_mean=('wall_seconds','mean'),canonical_updates_mean=('canonical_optimizer_updates','mean'),
        mean_effect_rmse=('mean_effect_rmse','mean'),coverage_90=('coverage_90','mean'),width_90=('width_90','mean')).reset_index()
    method.to_csv(PROJECT/'results/curated/method_summary.csv',index=False)
    rows=[]
    semantic=frame[frame.study=='semantic']
    for variant in ('coherent','anonymous','shuffled'):
        pairs=paired_results(semantic[semantic.metadata_variant==variant],comparator='llm_edit')
        rows.append({'comparison':f'diagnostic - llm_edit ({variant})','scope':'semantic, 5 independent SCMs',**cluster_interval(pairs)})
    cohort=selected[selected.study=='semantic']
    keys=['study','d','family','seed','budget']
    coherent=cohort[(cohort.method=='diagnostic')&(cohort.metadata_variant=='coherent')]
    for variant,method_name in [('anonymous','diagnostic'),('shuffled','diagnostic'),('none','data_only')]:
        comparison=cohort[(cohort.method==method_name)&(cohort.metadata_variant==variant)]
        pairs=coherent.merge(comparison,on=keys,suffixes=('_method','_comparison'),validate='one_to_one')
        pairs['delta']=pairs.sw1_method-pairs.sw1_comparison
        rows.append({'comparison':f'coherent diagnostic - {variant} {method_name}',
                     'scope':'semantic, 5 independent SCMs',**cluster_interval(pairs)})
    metadata=pd.DataFrame(rows)
    metadata.to_csv(PROJECT/'results/curated/metadata_comparisons.csv',index=False)
    ablation=frame[(frame.study=='controlled')&(frame.d==5)&(frame.family=='heteroscedastic')&
                   (frame.budget==100)&(frame.corruption==.5)]
    rows=[]
    for comparator in ('marginal','no_wasserstein','additive_repair'):
        pairs=paired_results(ablation,comparator=comparator)
        rows.append({'comparison':'diagnostic - '+comparator,**cluster_interval(pairs)})
    pd.DataFrame(rows).to_csv(PROJECT/'results/curated/ablation_comparisons.csv',index=False)
    pairs=paired_results(frame[(frame.study=='controlled')&(frame.corruption>0)],method='fixed',comparator='additive_fixed')
    pd.DataFrame([{'comparison':'fixed flow - fixed additive',**cluster_interval(pairs)}]).to_csv(
        PROJECT/'results/curated/flow_additive_comparison.csv',index=False)
    damage=paired_results(frame[(frame.study=='controlled')&(frame.corruption==0)])
    damage.to_csv(PROJECT/'results/curated/uncorrupted_repairs.csv',index=False)
    return metadata
