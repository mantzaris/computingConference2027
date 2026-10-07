"""Statistical-unit and multiplicity checks, independent of experiment outcomes."""
import numpy as np
import pandas as pd
from sem_update.phase2.reporting import interval,sign_probability,holm,paired

def test_repeated_conditions_do_not_create_independent_scms():
    rows=[{'study':'controlled','family':'linear','d':5,'seed':seed,'error':value}
          for seed,value in [(1,1.),(2,3.),(3,5.)]]
    one=pd.DataFrame(rows);many=pd.concat([one]*100,ignore_index=True)
    assert interval(one,'error')==interval(many,'error')
    assert interval(many,'error')['independent_scms']==3

def test_sign_probability_uses_whole_independent_systems():
    assert sign_probability([1.,2.,3.,4.,5.])==2/32
    assert sign_probability([0.,0.,0.])==1.
    assert sign_probability([-2.,2.])==1.

def test_holm_adjustment_preserves_original_comparison_order():
    np.testing.assert_allclose(holm([.04,.001,.03]),[.06,.003,.06])

def test_pairing_uses_condition_identity_not_row_order():
    rows=[{'method':method,'task_id':task,'endpoint':'T2','stage':'selected','sw1':score}
          for method,task,score in [('M3','a',2.),('M3','b',4.),('M4','b',5.),('M4','a',1.)]]
    result=paired(pd.DataFrame(rows),'M3','M4').set_index('task_id')
    assert result.loc['a','delta']==1. and result.loc['b','delta']==-1.

def test_real_observations_are_not_counted_as_independent_scms():
    result=interval(pd.DataFrame({'study':['real']*100,'sw1':[.25]*100}))
    assert result=={'mean':.25,'low':None,'high':None,'independent_scms':0}
