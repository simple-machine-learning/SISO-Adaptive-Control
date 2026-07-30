"""Optional native acceleration for MRAC controller adaptation."""
from __future__ import annotations
import os
import numpy as np
try:
    from . import _honu_mpc_native as _native
except ImportError:
    try: import _honu_mpc_native as _native
    except ImportError: _native=None
NATIVE_AVAILABLE=_native is not None and hasattr(_native,'mrac_adaptive_update')
_reported=False

def native_enabled():
    return NATIVE_AVAILABLE and os.environ.get('SISO_MRAC_NATIVE','1').lower() not in {'0','false','no','off'}

def adaptive_update(v,g_v,e,r0,g_r0,mu_v,mu_r0,eps,r0_min,r0_max,learning='NGD',dv_prev=None,dr_prev=0.0,alpha_v=1.0,alpha_r0=1.0,v_norm_max=0.0):
    global _reported
    if not native_enabled(): raise RuntimeError('Native MRAC backend unavailable')
    out=_native.mrac_adaptive_update(np.ascontiguousarray(v,float),np.ascontiguousarray(g_v,float),float(e),float(r0),float(g_r0),float(mu_v),float(mu_r0),float(eps),float(r0_min),float(r0_max),str(learning).upper()=='NGD',None if dv_prev is None else np.ascontiguousarray(dv_prev,float),float(dr_prev),float(alpha_v),float(alpha_r0),float(v_norm_max))
    if not _reported:
        print('MRAC backend: C++ accelerated (adaptation update)')
        _reported=True
    return out
