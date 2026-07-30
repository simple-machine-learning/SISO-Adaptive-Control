"""Smoke test for MRAC plant-HONU recurrent rollout refinement."""
import numpy as np
from mrac_rollout_plant_training import refine_plant_weights, rollout_rmse


def run(model):
    rng=np.random.default_rng(4)
    n=220; u=rng.normal(scale=.25,size=n); y=np.zeros(n)
    for k in range(2,n):
        y[k]=0.72*y[k-1]-0.12*y[k-2]+0.25*u[k-1]+0.04*y[k-1]**2
    ny=2; nu=1; delay=0
    if model=='LNU':
        theta=np.array([0.0,0.55,0.0,0.12])
    else:
        # qnu feature length for augmented [1,y1,y2,u1] is 14 in this project basis
        from honu_basis import qnu_feature_count
        theta=np.zeros(qnu_feature_count(1+ny+nu)); theta[1]=0.45; theta[2]=-0.02; theta[3]=0.1
    before=rollout_rmse(theta,y,u,model=model,ny=ny,nu=nu,delay=delay,horizon=6,max_windows=60)
    refined,info=refine_plant_weights(theta,y,u,model=model,ny=ny,nu=nu,delay=delay,
        enabled=True,horizon=6,iterations=8,max_windows=60,discount=1.0,ridge=1e-5)
    after=rollout_rmse(refined,y,u,model=model,ny=ny,nu=nu,delay=delay,horizon=6,max_windows=60)
    assert np.all(np.isfinite(refined))
    assert after <= before*1.001, (model,before,after)
    print(model, before, after, info)

run('LNU')
run('QNU')
print('MRAC rollout plant training: OK')
