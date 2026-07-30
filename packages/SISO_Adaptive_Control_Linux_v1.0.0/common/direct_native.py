from __future__ import annotations
import os
import numpy as np
try:
    from . import _direct_mpc_native as _native
except ImportError:
    try:
        import _direct_mpc_native as _native
    except ImportError:
        _native=None
NATIVE_AVAILABLE=_native is not None

def native_enabled():
    return NATIVE_AVAILABLE and os.environ.get('SISO_DIRECT_NATIVE','1').strip().lower() not in {'0','false','no','off'}

def predict_sequence_and_jacobian(candidate_u,y_hist,u_hist,local,compute_jacobian=True):
    if not native_enabled():
        raise RuntimeError('Native direct multi-horizon backend unavailable or disabled')
    model=str(local['model']).upper()
    if model=='MLP':
        prep=local['mlp_preprocess']; hidden=[int(v) for v in local.get('hidden_layers',[])]
        nin=int(np.asarray(prep['P']).shape[1])+int(local['ny'])+int(local['nu'])-int(prep['history_dim'])+int(local['horizon'])
        sizes=np.asarray([nin,*hidden,int(local['horizon'])],dtype=np.int64)
        return _native.predict_mlp_direct(
            np.ascontiguousarray(candidate_u,float),np.ascontiguousarray(y_hist,float),np.ascontiguousarray(u_hist,float),
            np.ascontiguousarray(local['W'],float),sizes,np.ascontiguousarray(prep['history_mean'],float),
            np.ascontiguousarray(prep['history_std'],float),np.ascontiguousarray(prep['P'],float),
            np.ascontiguousarray(prep['future_mean'],float),np.ascontiguousarray(prep['future_std'],float),
            int(local['ny']),int(local['nu']),int(local.get('delay_u',0)),int(prep['history_dim']),float(local['target_scale']),
            str(local.get('prediction_target','delta')).lower()=='delta',bool(compute_jacobian))
    return _native.predict_honu_direct(
        np.ascontiguousarray(candidate_u,float),np.ascontiguousarray(y_hist,float),np.ascontiguousarray(u_hist,float),
        np.ascontiguousarray(local['W'],float),np.ascontiguousarray(local['pca']['P'],float),int(local['ny']),int(local['nu']),
        int(local.get('delay_u',0)),int(model=='QNU'),str(local.get('prediction_target','absolute')).lower()=='delta',bool(compute_jacobian))
