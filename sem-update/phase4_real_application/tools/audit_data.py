"""Metadata/quality audit; measured outcome values are never returned to the learner."""
import csv
import json
from pathlib import Path
import numpy as np
import pandas as pd
from acquire import ROOT, sha

def main():
    records=[]
    settings=['config','pot_1','pot_2','osr_in','osr_out','osr_mic','osr_upwind','osr_downwind',
              'osr_ambient','osr_intake','res_in','res_out','v_in','v_out','v_mic','osr_1','osr_2','v_1','v_2']
    for p in sorted((ROOT/'raw').glob('*/*/*.csv')):
        columns=pd.read_csv(p,nrows=0).columns.tolist()
        f=pd.read_csv(p,usecols=['timestamp','counter','flag','intervention','load_in','load_out','hatch']+settings)
        summaries={c:sorted(f[c].unique().tolist()) for c in settings}
        summaries={c:v if len(v)<=16 else {'distinct':len(v),'min':min(v),'max':max(v)} for c,v in summaries.items()}
        # Missingness is a predeclared quality check only, not an outcome statistic.
        missing={c:0 for c in columns}
        for chunk in pd.read_csv(p,chunksize=10000):
            for c,n in chunk.isna().sum().items(): missing[c]+=int(n)
        t=f.timestamp.to_numpy(); resets=np.where(np.diff(f.counter)<0)[0]+1
        segments=np.split(np.arange(len(f)),resets)
        records.append({'dataset':p.parts[-3],'name':p.stem,'rows':len(f),'columns':columns,'sha256':sha(p),
            'bytes':p.stat().st_size,'settings':summaries,'missing':missing,'counter_resets':resets.tolist(),
            'recorded_counter_segments':[{'start':int(s[0]),'stop':int(s[-1]+1)} for s in segments],
            'dt_quantiles':np.quantile(np.diff(t),[0,.5,1]).tolist(),'timestamp_start':float(t[0]),'timestamp_end':float(t[-1]),
            'time_warning':'Recorded values are not plausible Unix epoch dates; elapsed differences only.',
            'flag_values':sorted(f.flag.unique().tolist()),'intervention_values':sorted(f.intervention.unique().tolist())})
    (ROOT/'dataset_audit_full.json').write_text(json.dumps(records,indent=2)+'\n')
    compact=Path(__file__).resolve().parents[1]/'results';compact.mkdir(exist_ok=True)
    with open(compact/'acquisitions.csv','w') as s:
        w=csv.writer(s);w.writerow(['dataset','experiment','rows','counter_segments','median_interval_s','missing','sha256'])
        for r in records:w.writerow([r['dataset'],r['name'],r['rows'],1+len(r['counter_resets']),round(r['dt_quantiles'][1],6),sum(r['missing'].values()),r['sha256']])
    print(json.dumps({'files':len(records),'rows':sum(r['rows'] for r in records),'counter_segments':sum(1+len(r['counter_resets']) for r in records)}))

if __name__=='__main__':main()
