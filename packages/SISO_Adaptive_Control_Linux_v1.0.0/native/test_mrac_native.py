from __future__ import annotations
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from common.mrac_native import adaptive_update, native_enabled

def reference(v,g,e,r0,gr,mu_v,mu_r,eps,rmin,rmax,ngd,dvp=None,drp=0.,av=1.,ar=1.,vmax=0.):
    g2=float(g@g)
    ev=mu_v/(eps+g2) if ngd else mu_v
    er=mu_r/(eps+gr*gr) if ngd else mu_r
    raw=-ev*e*g
    dv=av*raw+(1-av)*(np.zeros_like(v) if dvp is None else dvp)
    vn=v+dv
    if vmax>0 and np.linalg.norm(vn)>vmax: vn*=vmax/np.linalg.norm(vn)
    dr=ar*(-er*e*gr)+(1-ar)*drp
    rn=float(np.clip(r0+dr,rmin,rmax))
    rank=1-ev*g2
    return vn,dv,rn,dr,max(1.,abs(rank)),max(1.,abs(rank)),abs(1-er*gr*gr)

assert native_enabled(), 'MRAC native module unavailable'
rng=np.random.default_rng(4)
for n in (5,21,66):
  for ngd in (False,True):
    for smooth in (False,True):
      v=rng.normal(size=n); g=rng.normal(size=n); dvp=rng.normal(size=n)*.01
      kw=dict(v=v,g_v=g,e=.37,r0=.9,g_r0=-.42,mu_v=.08,mu_r0=.03,eps=1e-7,r0_min=.1,r0_max=2.,learning='NGD' if ngd else 'GD',dv_prev=dvp if smooth else None,dr_prev=.02 if smooth else 0.,alpha_v=.2 if smooth else 1.,alpha_r0=.3 if smooth else 1.,v_norm_max=3. if smooth else 0.)
      got=adaptive_update(**kw)
      ref=reference(v,g,.37,.9,-.42,.08,.03,1e-7,.1,2.,ngd,dvp if smooth else None,.02 if smooth else 0.,.2 if smooth else 1.,.3 if smooth else 1.,3. if smooth else 0.)
      for a,b in zip(got,ref): np.testing.assert_allclose(a,b,rtol=2e-13,atol=2e-13)

n=66; reps=20000; v=rng.normal(size=n); g=rng.normal(size=n)
t=time.perf_counter()
for _ in range(reps): reference(v,g,.2,1.,.3,.05,.02,1e-8,.1,2.,True)
py=time.perf_counter()-t
t=time.perf_counter()
for _ in range(reps): adaptive_update(v,g,.2,1.,.3,.05,.02,1e-8,.1,2.,'NGD')
cpp=time.perf_counter()-t
print('MRAC native numerical equivalence: PASS')
print(f'Python reference: {1e6*py/reps:.3f} us/step')
print(f'C++ native:       {1e6*cpp/reps:.3f} us/step')
print(f'Speedup:          {py/cpp:.2f}x')
