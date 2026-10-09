import numpy as np
import pandas as pd
import pytest
import torch
from sem_update.graphs import DAG
from sem_update.data import Environment
from app_data import calibrated, eligible, NuisanceView, ACTUATORS, VARS, final_design, ROOTS
from app_methods import legal_edits, sample_joint
from sem_update.phase2.models import EmpiricalMarginals

def test_calibration_and_pressure_arithmetic():
    f=pd.DataFrame(np.ones((2,len(VARS))),columns=VARS)
    f['v_in']=f['v_out']=1.1; f['pressure_ambient']=100000;f['pressure_upwind']=100125
    x=calibrated(f)
    assert x[0,5]==pytest.approx(1.16/(1023*2))
    assert x[0,7]==125 and x[0,10]==100000

def test_command_filter_uses_elapsed_time_and_never_outcomes():
    f=pd.DataFrame({'timestamp':np.arange(100.),'load_in':np.r_[np.zeros(50),np.ones(50)],'load_out':0.,'hatch':0.})
    ids=eligible(f)
    assert not any(50<=i<59 for i in ids)
    assert min(ids)>=15 and np.min(np.diff(ids))>=3

def test_real_assignment_protocols_and_final_roles():
    rows=final_design()
    assert len([r for r in rows if r['panel']=='primary'])==5
    assert all(r['wait_ms']==10000 for r in rows if r['panel']=='primary')
    assert sum(r['arm_n'][0]+r['arm_n'][1] for r in rows)==sum(r['n'] for r in rows)
    assert next(r for r in rows if r['run']=='validate_load_out')['n']==49

def test_root_constraints_and_cycles():
    from sem_update.phase3.graphs import apply
    for move in legal_edits(DAG(11,((0,3),(3,4),(10,7))),3):
        graph=apply(DAG(11,((0,3),(3,4),(10,7))),move)
        assert all(not graph.parents(j) for j in ROOTS)

def test_joint_commands_are_not_independently_resampled():
    model=EmpiricalMarginals(torch.randn(100,11,device='cuda'))
    spec={'0':{'kind':'recorded_joint','values':[1.,2.,3.]},'1':{'kind':'recorded_joint','values':[10.,20.,30.]},'2':{'kind':'fixed','value':7.}}
    z=sample_joint(model,spec,300,812)
    torch.testing.assert_close(z[:,1],10*z[:,0]);assert (z[:,2]==7).all()

def test_assignment_nuisance_has_no_physical_training_loss():
    class D:
        d=11
        def get(self,role):return [Environment('real',torch.ones(4,11),{str(j):{} for j in ACTUATORS},(),())]
    envs=NuisanceView(D()).get('fit')
    assert set(envs[0].targets)==set(ACTUATORS)
    assert set(envs[1].targets)==set(range(3,11))
    assert torch.equal(envs[0].x,envs[1].x)

def test_block_contrasts_and_recorded_decisions():
    from app_evaluate import block_means,choose_arm,score_effect
    arms=np.tile([0,1],30);x=np.column_stack([arms*4.,arms*-2.])
    means=block_means(x,arms,40,712)
    np.testing.assert_allclose(means[:,1]-means[:,0],np.tile([4.,-2.],(40,1)))
    conditions=np.zeros((2,11));conditions[:,7]=[5,20];conditions[:,5]=[.1,.3]
    assert choose_arm(conditions,10)==1 and choose_arm(conditions,3)==0
    assert choose_arm(conditions,30)==1

def test_conditional_score_and_masked_assignment_law():
    from sem_update.phase3.flows import FastSCM
    from sem_update.flows import Mechanism
    from sem_update.phase3 import objectives
    from app_methods import sample_many
    original=objectives.sample_many
    graph=DAG(11,((0,3),(1,6)))
    model=FastSCM(graph,[Mechanism(graph.parents(j),16).cuda() for j in range(11)])
    envs=[Environment('a',torch.randn(20,11,device='cuda'),{str(j):{'kind':'fixed','value':0.} for j in ACTUATORS},(),()),
          Environment('b',torch.randn(20,11,device='cuda'),{str(j):{'kind':'fixed','value':1.} for j in ACTUATORS},(),())]
    try:
        objectives.sample_many=sample_many
        value=objectives.score(model,envs,{'samples':32,'projections':8})
        assert value['total']==pytest.approx(np.mean(value['environment_scores']))
        # Changing replaced root densities cannot change conditional likelihood.
        before=model.log_probability(envs[0].x,ACTUATORS)
        with torch.no_grad():
            for j in ACTUATORS:model.mechanisms[j].constant.add_(10)
        torch.testing.assert_close(model.log_probability(envs[0].x,ACTUATORS),before)
    finally:objectives.sample_many=original

def test_llm_metadata_serialization_preserves_proposed_edges():
    from app_llm import canonicalize_nodes
    nodes=[{'id':f'V{j}'} for j in range(11)]
    value={'nodes':nodes,'edges':[{'source':'V0','target':'V3','rationale':'physical hypothesis'}]}
    assert canonicalize_nodes(value,nodes).edges==((0,3),)
    invalid={**value,'nodes':list(reversed(nodes))}
    with pytest.raises(ValueError):canonicalize_nodes(invalid,nodes)
