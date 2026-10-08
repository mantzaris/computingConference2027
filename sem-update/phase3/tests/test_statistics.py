import numpy as np
import pandas as pd
import pytest
from sem_update.phase3.reporting import bootstrap,holm,sign_test

def test_conditions_are_not_independent_systems():
    rows=pd.DataFrame({'family':['a']*6,'scm':[1,1,2,2,3,3],'x':[0.,0.,1.,1.,3.,3.]})
    first=bootstrap(rows,'x');duplicated=bootstrap(pd.concat([rows]*9),'x')
    assert first==duplicated and first[3]==3
    assert first[0]==pytest.approx(4/3)

def test_sign_randomization_and_holm_family():
    assert sign_test([1.]*5)==pytest.approx(2/32)
    assert sign_test([0.]*5)==1.
    assert sign_test([1.,-1.])==1.
    np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])

def test_stratified_bootstrap_keeps_family_composition():
    rows=pd.DataFrame({'family':['a','a','b','b'],'scm':[1,2,3,4],'x':[0.,0.,10.,10.]})
    assert bootstrap(rows,'x')==(5.,5.,5.,4)
