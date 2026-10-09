"""Descriptive unit/direction summaries from frozen predictions; no model selection."""
import json
import numpy as np
import pandas as pd
from app_runtime import ROOT,RESULTS,read_json

def main():
    observed=pd.read_csv(RESULTS/'observed_effects.csv')
    effects=pd.read_csv(RESULTS/'effects.csv');costs=pd.read_csv(RESULTS/'costs.csv')
    protocol=read_json(RESULTS/'protocol.json')
    primary=[r['run'] for r in protocol['final_design'] if r['panel']=='primary']
    methods=['M0','M1','M2','fixed','random','M3','M4','M5']
    scales=read_json(ROOT/'data/processed/main/manifest.json')
    scales=dict(zip(scales['variables'],scales['standardization']['std']))
    rows=[]
    for method in methods:
        for outcome in protocol['primary_outcomes']:
            sub=effects[(effects.method==method)&(effects.outcome==outcome)&effects.run.isin(primary)]
            obs=observed[(observed.outcome==outcome)&observed.run.isin(primary)].set_index('run')
            targets=[];signs=[]
            for target in ('load_in','load_out','hatch'):
                names=obs[obs.target==target].index
                targets.append(sub[sub.run.isin(names)].absolute_error.mean())
            for r in sub.itertuples():
                o=obs.loc[r.run]
                if o.ci_low*o.ci_high>0:signs.append(np.sign(r.pred_effect)==np.sign(o.effect))
            rows.append({'method':method,'outcome':outcome,'unit':obs.unit.iloc[0],
                'equal_target_mae':np.mean(targets),'standardized_mae':np.mean(targets)/scales[outcome],
                'direction_matches':sum(signs),'contrasts_with_block_ci_excluding_zero':len(signs)})
    pd.DataFrame(rows).to_csv(RESULTS/'engineering_summary.csv',index=False,float_format='%.8g')
    speed=[]
    for method in methods:
        path=costs[costs.method==method].prediction_artifact.iloc[0]
        with np.load(ROOT/path) as arrays:
            for run in primary:
                for j,outcome in [(3,'rpm_in'),(4,'rpm_out')]:
                    delta=arrays[run+'_1'][:,j].mean()-arrays[run+'_0'][:,j].mean()
                    o=observed[(observed.run==run)&(observed.outcome==outcome)].iloc[0]
                    speed.append({'method':method,'run':run,'outcome':outcome,'predicted_change_rpm':delta,
                                  'observed_change_rpm':o.effect,'absolute_error_rpm':abs(delta-o.effect)})
    pd.DataFrame(speed).to_csv(ROOT/'reports/speed_predictions.csv',index=False,float_format='%.10g')
    # Display-ready graph edges map exactly to recorded, immutable node IDs.
    graphs=read_json(RESULTS/'graphs.json');freq=pd.read_csv(RESULTS/'edge_frequency.csv')
    names=read_json(ROOT/'data/processed/main/manifest.json')['variables']
    initial=set(map(tuple,graphs['M3']['initial']['edges']))
    selected=set(map(tuple,graphs['M3']['selected']['graph']['edges']))
    edges=[]
    for a,b in sorted(initial|selected):
        f=freq[(freq.source==a)&(freq.target==b)].selection_frequency.iloc[0]
        edges.append({'source':names[a],'target':names[b],
                      'status':'retained' if (a,b) in initial&selected else 'added' if (a,b) in selected else 'removed',
                      'selection_frequency':f,'evidence':'predictive model edge; randomized total effects do not establish directness'})
    pd.DataFrame(edges).to_csv(RESULTS/'process_edges.csv',index=False,float_format='%.6g')
    manifest=read_json(ROOT/'data/processed/main/manifest.json')
    with np.load(ROOT/'data/processed/main/learner.npz') as arrays:
        x=np.concatenate([arrays[r['array']] for r in manifest['splits']['fit']])
    x=x*np.array(manifest['standardization']['std'])+np.array(manifest['standardization']['mean'])
    support=[]
    for r in protocol['final_design']:
        if r['panel']!='primary':continue
        for arm in (0,1):
            commands={**r['nuisance'],r['target']:r['high'] if arm else r['low']}
            point=np.array([commands[k] for k in names[:3]])
            near=np.all(np.abs(x[:,:3]-point)<=np.array([.1,.1,5]),axis=1)
            support.append({'run':r['run'],'arm':arm,'fit_rows_near_joint_commands':int(near.sum()),
                'fitting_rows':len(x),'fan_tolerance':.1,'hatch_tolerance_degrees':5,
                'scope':'descriptive support check; not a new eligibility or selection rule'})
    pd.DataFrame(support).to_csv(RESULTS/'operating_support.csv',index=False)
    print(json.dumps({'main_methods':len(methods),'primary_unit_summaries':len(rows),'supplementary_speed_predictions':len(speed),'process_edges':len(edges)}))

if __name__=='__main__':main()
