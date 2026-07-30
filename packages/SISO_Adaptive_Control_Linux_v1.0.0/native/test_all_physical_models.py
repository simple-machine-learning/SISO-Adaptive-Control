from __future__ import annotations
import os, sys, time
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps'/'simulated'))
sys.path.insert(0,str(ROOT/'common'))
import shared_plant_model as spm

solver=SimpleNamespace(method='Radau',rtol=1e-8,atol=1e-10,dt_sim=1e-3,max_step_factor=0.1)
rows=[]
for name in spm.available_models():
    par=spm.default_params(name)
    x0=np.asarray(spm.initial_state(par),float)
    u=0.1
    dt=0.01
    os.environ['SISO_ODE_BACKEND']='rk4'
    t0=time.perf_counter()
    x=x0.copy()
    ok=True; err=''
    try:
        for _ in range(20): x=spm.simulate_sample_period_zoh(x,u,dt,par,solver)
        tf=time.perf_counter()-t0
        if not np.all(np.isfinite(x)): raise ValueError('non-finite RK4 state')
        os.environ['SISO_ODE_BACKEND']='scipy'
        t0=time.perf_counter(); xr=x0.copy()
        for _ in range(20): xr=spm.simulate_sample_period_zoh(xr,u,dt,par,solver)
        ts=time.perf_counter()-t0
        abs_err=float(np.max(np.abs(x-xr)))
        scale=max(1.0,float(np.max(np.abs(xr))))
        rel_err=abs_err/scale
    except Exception as exc:
        ok=False; tf=ts=abs_err=rel_err=float('nan'); err=str(exc)
    rows.append((name,ok,tf,ts,ts/tf if ok and tf>0 else float('nan'),abs_err,rel_err,err))

print(f"{'model':48s} {'ok':>3s} {'fast ms':>10s} {'scipy ms':>10s} {'speedup':>9s} {'rel.err':>11s}")
for r in rows:
    print(f"{r[0]:48s} {str(r[1]):>3s} {1e3*r[2]:10.3f} {1e3*r[3]:10.3f} {r[4]:9.2f} {r[6]:11.3e}")
    if r[7]: print('  ',r[7])
failed=[r for r in rows if not r[1]]
if failed: raise SystemExit(f'{len(failed)} models failed')
print(f'All {len(rows)} models passed. Median speedup: {np.median([r[4] for r in rows]):.2f}x')
