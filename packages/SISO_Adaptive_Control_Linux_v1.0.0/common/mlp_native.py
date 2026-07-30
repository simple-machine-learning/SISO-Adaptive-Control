from __future__ import annotations
import os
import numpy as np
try:
    from . import _mlp_mpc_native as _native
except ImportError:
    try:
        import _mlp_mpc_native as _native
    except ImportError:
        _native=None
NATIVE_AVAILABLE=_native is not None
def native_enabled():
    return NATIVE_AVAILABLE and os.environ.get('SISO_MLP_NATIVE','1').strip().lower() not in {'0','false','no','off'}
def predict_sequence_and_jacobian(candidate_u,y_hist,u_hist,local,compute_jacobian=True):
    prep=local['mlp_preprocess']; hidden=[int(v) for v in local.get('hidden_layers',[])]; nin=int(np.asarray(prep['P']).shape[1])+int(local['ny'])+int(local['nu'])-int(prep['history_dim'])
    sizes=np.asarray([nin,*hidden,1],dtype=np.int64)
    return _native.predict_mlp_sequence_and_jacobian(np.ascontiguousarray(candidate_u,float),np.ascontiguousarray(y_hist,float),np.ascontiguousarray(u_hist,float),np.ascontiguousarray(local['c'],float),sizes,np.ascontiguousarray(prep['history_mean'],float),np.ascontiguousarray(prep['history_std'],float),np.ascontiguousarray(prep['P'],float),np.ascontiguousarray(prep['future_mean'],float),np.ascontiguousarray(prep['future_std'],float),int(local['ny']),int(local['nu']),int(local.get('delay_u',0)),int(prep['history_dim']),float(local['target_scale']),str(local.get('prediction_target','delta')).lower()=='delta',bool(compute_jacobian))
