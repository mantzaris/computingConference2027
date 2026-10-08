"""Reproducible prospective forecast from full pilots, without outcome metrics."""
import argparse
import json
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--consumed-hours',type=float,required=True)
    parser.add_argument('--throughput-gain',type=float,default=2.5);args=parser.parse_args()
    phase=Path(__file__).resolve().parents[1]
    cfg=json.loads((phase/'configs/main.json').read_text())
    pilots=json.loads((phase/'results/pilot_provenance.json').read_text())['pilots'];estimates=[]
    for pilot in pilots:
        d=pilot['task']['d'];stages=pilot['stages'];ratio=cfg['adjusted_candidates'][str(d)]/pilot['banks']['diagnostic']['candidates']
        common=sum(v['seconds'] for k,v in stages.items() if not k.startswith('c0.5') and k!='oracle')
        condition=sum(v['seconds']*(ratio if k.endswith(('-diagnostic','-random','-adjusted-select')) else 1)
                      for k,v in stages.items() if k.startswith('c0.5'))
        estimates.append({'d':d,'common_solo_seconds':common,'two_corruption_solo_seconds':common+2*condition,
            'candidate_multiplier_from_pilot':ratio,'pilot_profile':pilot['task']['profile']})
    serial=sum(r['two_corruption_solo_seconds']*{20:10,50:25,100:10}[r['d']] for r in estimates)
    oracle=sum(next(p['stages']['oracle']['seconds'] for p in pilots if p['task']['d']==d)*n for d,n in [(20,2),(50,5),(100,2)])
    optional=sum(r['two_corruption_solo_seconds']+next(p['stages']['oracle']['seconds'] for p in pilots if p['task']['d']==r['d'])
                 for r in estimates if r['d'] in (50,100)) if cfg['fixed_total_sensitivity'] else 0.
    value={'scope':'Prospective device-wall forecast; no main final outcomes inspected','pilot_estimates':estimates,
        'full_primary_serial_fitting_hours':(serial+oracle)/3600,'optional_sensitivity_serial_hours':optional/3600,
        'conservative_assumed_full_pipeline_throughput_gain':args.throughput_gain,
        'primary_fitting_device_hours':(serial+oracle)/3600/args.throughput_gain,
        'optional_fitting_device_hours':optional/3600/args.throughput_gain,
        'reserved_final_device_hours':cfg['final_reserve_seconds']/3600,
        'already_consumed_phase3_device_hours':args.consumed_hours,
        'projected_phase3_total_hours':args.consumed_hours+(serial+oracle+optional)/3600/args.throughput_gain+cfg['final_reserve_seconds']/3600,
        'uncertainty':'Extrapolates single-task complete pilots. The parallel density probe is not a whole-pipeline speed guarantee. Primary replication precedes profiles and optional sensitivity; the runtime guard reserves final evaluation.'}
    (phase/'results/runtime_forecast.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps(value,indent=2))

if __name__=='__main__':main()
