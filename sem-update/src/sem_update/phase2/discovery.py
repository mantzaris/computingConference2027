"""Pinned official DCDI-DSF density with the validated historical optimizer adapter."""
import sys
import torch
from sem_update import dcdi as legacy
from .runtime import root,file_hash

def official_dsf(d,config):
    # This also verifies the revision and installs the device-correct Gumbel
    # sampler already used by the validated historical DCDI-G implementation.
    unused=legacy.official_model(d,config);del unused
    from dcdi.models.flows import DeepSigmoidalFlowModel
    class DeviceDSF(DeepSigmoidalFlowModel):
        def _log_likelihood(self,x,density_params):
            # The original source allocates two torch.zeros tensors on CPU.
            # Device context fixes allocation only; the density/Jacobian is
            # the unchanged upstream DSF implementation.
            with torch.device(x.device):
                return super()._log_likelihood(x,density_params)
    model=DeviceDSF(d,config['layers'],config['width'],'leaky-relu',
        config.get('flow_layers',2),config.get('flow_width',8),
        intervention=True,intervention_type='perfect',intervention_knowledge='known').cuda()
    model.adjacency=model.adjacency.cuda()
    return model

def discover(data,config,roots=()):
    cfg={**config,'variant':'DSF','phase2_adapter_sha256':file_hash(__file__)}
    original=legacy.official_model
    # Single process, no concurrent model factories. Avoid editing or copying
    # the historical optimizer, its checkpoints, or historical result labels.
    def factory(d,c):
        legacy.official_model=original
        try:return official_dsf(d,c)
        finally:legacy.official_model=factory
    legacy.official_model=factory
    try:result=legacy.discover(data,cfg,roots)
    finally:legacy.official_model=original
    return {**result,'implementation':'official DCDI-DSF density; historical CUDA augmented-Lagrangian adapter',
        'primary_method_label':'DCDI-DSF + common flows','upstream_revision':legacy.REVISION,
        'flow_layers':cfg.get('flow_layers',2),'flow_width':cfg.get('flow_width',8)}
