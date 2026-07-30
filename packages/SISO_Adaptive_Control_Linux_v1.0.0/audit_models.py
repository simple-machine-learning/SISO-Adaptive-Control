import sys, importlib, pathlib, numpy as np
from scipy.integrate import solve_ivp
root=pathlib.Path(__file__).resolve().parent
models_dir=root/'apps'/'simulated'/'plant_models'
sys.path.insert(0,str(root/'apps'/'simulated'))
from model_recommended_presets import MODEL_RECOMMENDED_PRESETS

def rk4(rhs,x,u,dt,h,par):
    n=max(1,int(np.ceil(dt/h))); h=dt/n; x=np.array(x,float)
    for _ in range(n):
        k1=np.asarray(rhs(0,x,u,par),float); k2=np.asarray(rhs(0,x+h*k1/2,u,par),float)
        k3=np.asarray(rhs(0,x+h*k2/2,u,par),float); k4=np.asarray(rhs(0,x+h*k3,u,par),float)
        x=x+h*(k1+2*k2+2*k3+k4)/6
    return x

rows=[]
for p in sorted(models_dir.glob('*.py')):
    if p.name=='__init__.py': continue
    name=p.stem
    try:
        m=importlib.import_module('plant_models.'+name)
        par=m.default_params(); x0=np.asarray(m.initial_state(par),float)
        preset=MODEL_RECOMMENDED_PRESETS.get(name,{})
        dt=float(preset.get('dt_sim',0.01))
        u=float(preset.get('u_max',1.0))*0.7
        f0=np.asarray(m.rhs(0,x0,u,par),float)
        sol=solve_ivp(lambda t,x:m.rhs(t,x,u,par),(0,dt),x0,method='Radau',rtol=1e-10,atol=1e-12)
        xr=rk4(m.rhs,x0,u,dt,dt,par)
        xr10=rk4(m.rhs,x0,u,dt,dt/10,par)
        ref=sol.y[:,-1]
        scale=max(1.0,float(np.linalg.norm(ref,np.inf)))
        e1=float(np.linalg.norm(xr-ref,np.inf)/scale)
        e10=float(np.linalg.norm(xr10-ref,np.inf)/scale)
        rows.append((name,dt,np.all(np.isfinite(f0)),sol.success,e1,e10,''))
    except Exception as e:
        rows.append((name,np.nan,False,False,np.nan,np.nan,repr(e)))
print('model\tdt\tf0\tradau\terr_rk4_dt\terr_rk4_dt10\terror')
for r in rows: print('\t'.join(map(str,r)))
