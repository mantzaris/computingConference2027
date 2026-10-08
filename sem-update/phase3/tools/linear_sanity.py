"""GPU numerical sanity at all primary sizes; not extra research-method cells."""
import json
import math
import numpy as np
import torch
from sem_update.phase3.runtime import setup,require_cuda,job,RESULTS,atomic_json,scientific_hash
from sem_update.phase3.data import System,seed_for

def main():
    setup();require_cuda();result=[]
    with job('linear-numerical-sanity',{'source':scientific_hash(),'sizes':[20,50,100],'rows':100000}) as active:
        if not active:return
        for d in (20,50,100):
            system=System(d,'linear','sparse',391000+d);a=np.zeros((d,d));intercept=[];sigma=[]
            for j,spec in enumerate(system.nodes):
                intercept.append(spec['intercept']);sigma.append(spec['sigma'])
                for p,w in zip(spec['parents'],spec['weights']):a[j,p]=.65*w/math.sqrt(len(spec['parents']))
            target=system.graph.order()[2];assigned=1.7;aa=a.copy();aa[target]=0
            bb=np.array(intercept);bb[target]=assigned;scales=np.array(sigma);scales[target]=0
            transform=np.linalg.inv(np.eye(d)-aa);mean=transform@bb;cov=(transform*scales[None,:])@(transform*scales[None,:]).T
            x=system.sample(100000,seed_for(d,'linear-sanity'),{target:{'kind':'fixed','value':assigned}})
            observed=x.mean(0).cpu().numpy();observed_cov=torch.cov(x.T).cpu().numpy();se=np.sqrt(np.diag(cov)/len(x))
            z=np.abs(observed-mean)/np.maximum(se,1e-5);max_cov=float(np.abs(observed_cov-cov).max())
            assert z.max()<6 and max_cov<.04 and torch.all(x[:,target]==assigned)
            result.append({'d':d,'seed':system.seed,'rows':len(x),'target':int(target),'max_mean_standard_errors':float(z.max()),
                'max_covariance_absolute_error':max_cov,'device':str(x.device),'passed':True})
        atomic_json(RESULTS/'linear_sanity.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
