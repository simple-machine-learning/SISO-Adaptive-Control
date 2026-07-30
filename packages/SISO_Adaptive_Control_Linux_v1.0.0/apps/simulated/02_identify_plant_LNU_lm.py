# -*- coding: utf-8 -*-
"""Levenberg-Marquardt identification of the simulated LNU HONU plant."""
from matplotlib.pyplot import *
from numpy import *
import builtins, os
from shared_plant_model import active_plant_display_name
from simulated_normalization import (load_normalized_uy, save_artifact_stats,
    denormalize_u, denormalize_y, denormalize_error)
from lm_identification import solve_linear_lm
from project_setup import (uy_file, simulated_normalization_file, dt, tau_u,
    plant_n_y, plant_n_u, plant_lm_epochs, plant_lm_lambda,
    plant_batch_mu_w_bibs, plant_batch_eps_bibs, plant_batch_plot_bibs_limit,
    plant_lnu_file_lm as plant_file, bibs_plant_lnu_file_lm as bibs_file,
    plant_lnu_lm_trace_file as trace_file, line_width)


from mrac_rollout_plant_training import refine_plant_weights
from project_setup import (mrac_plant_prediction_training, mrac_plant_rollout_length,
    mrac_plant_rollout_iterations, mrac_plant_rollout_max_windows,
    mrac_plant_rollout_discount)

n_y=int(plant_n_y); n_u=int(plant_n_u); n_u1=int(round(float(tau_u)/float(dt)))
u,y,normalization=load_normalized_uy(uy_file, simulated_normalization_file)
N=len(y); t=arange(N)*dt; N_start=builtins.max(n_y,n_u1+n_u)
if N<=N_start: raise ValueError(f"Dataset too short: N={N}, N_start={N_start}")
n_x=1+n_y+n_u
X=zeros((N-N_start,n_x)); Y=y[N_start:].copy()
for row,k in enumerate(range(N_start,N)):
    X[row,0]=1.0
    X[row,1:1+n_y]=y[k-n_y:k][::-1]
    X[row,1+n_y:]=u[k-n_u1-n_u:k-n_u1][::-1]
w,W_hist,sse_hist,lambda_hist=solve_linear_lm(X,Y,iterations=int(plant_lm_epochs),damping=float(plant_lm_lambda))

# Optional MRAC-specific recurrent rollout refinement.  The existing identifier
# supplies the initial one-step weights; each rollout is reinitialised from
# measured history and feeds back predicted y only within N_r steps.
w, rollout_info = refine_plant_weights(
    w, y, u, model="LNU", ny=n_y, nu=n_u, delay=n_u1,
    enabled=(str(mrac_plant_prediction_training).lower() == "recursive_rollout"),
    horizon=int(mrac_plant_rollout_length),
    iterations=int(mrac_plant_rollout_iterations),
    max_windows=int(mrac_plant_rollout_max_windows),
    discount=float(mrac_plant_rollout_discount), ridge=float(plant_lm_lambda),
)

y_n=zeros(N); e=zeros(N); y_n[N_start:]=X@w; e[N_start:]=y[N_start:]-y_n[N_start:]
eta_w=full(N,nan); A2_w=full(N,nan); Rho_w=full(N,nan)
for row,k in enumerate(range(N_start,N)):
    norm2=float(X[row]@X[row]); eta_w[k]=plant_batch_mu_w_bibs/(norm2+plant_batch_eps_bibs)
    directional=1.0-eta_w[k]*norm2; A2_w[k]=builtins.max(1.0,abs(directional)); Rho_w[k]=A2_w[k]
A_y=zeros((n_y,n_y)); A_y[0,:]=w[1:1+n_y]
if n_y>1: A_y[1:,:-1]=eye(n_y-1)
A2_y=full(N,linalg.norm(A_y,2)); Rho_y=full(N,builtins.max(abs(linalg.eigvals(A_y))))
u_plot=denormalize_u(u, normalization)
y_plot=denormalize_y(y, normalization)
y_n_plot=denormalize_y(y_n, normalization)
e_plot=denormalize_error(e, normalization)
print('w =',w); print(f'SSE = {sse_hist[-1]:.12g}'); print(f'Rho(A_y) = {Rho_y[0]:.12g}')
savetxt(plant_file,[dt,tau_u,n_u,n_u1,n_y,*w])
save_artifact_stats(plant_file, normalization, "HONU plant")
savetxt(bibs_file,column_stack((t,eta_w,A2_w,Rho_w,A2_y,Rho_y)),header='t eta_w A2_w Rho_Aw A2_y Rho_Ay')
savetxt(trace_file,column_stack((arange(1,int(plant_lm_epochs)+1),sse_hist,lambda_hist,W_hist)),header='epoch SSE lambda weights')
fig,ax=subplots(7,1,figsize=(10,12)); fig.suptitle(active_plant_display_name()+"\n"+f'Plant LNU Levenberg-Marquardt, lambda_0={plant_lm_lambda:g}')
ax[0].plot(t,u_plot,'b',linewidth=line_width); ax[0].set_ylabel('u')
ax[1].plot(t,y_plot,'k',linewidth=line_width); ax[1].plot(t,y_n_plot,'g',linewidth=line_width); ax[1].set_ylabel('y, y_n')
ax[2].plot(t,e_plot,'r',linewidth=line_width); ax[2].set_ylabel('e')
it=arange(1,int(plant_lm_epochs)+1)
ax[3].plot(it,sse_hist,'k',linewidth=line_width); ax[3].set_ylabel('SSE')
ax[4].semilogy(it,lambda_hist,'k',linewidth=line_width); ax[4].set_ylabel(r'$\lambda$')
ax[5].plot(t,Rho_w,'k',linewidth=line_width); ax[5].set_ylabel(r'$\rho(A_w)$')
ax[6].plot(t,Rho_y,'k',linewidth=line_width); ax[6].set_ylabel(r'$\rho(A_y(k))$'); ax[6].set_xlabel(f't [sec], dt={dt} [sec]')
for a in ax: a.grid(True)
if plant_batch_plot_bibs_limit:
    ax[5].axhline(1.0,linestyle='--'); ax[6].axhline(1.0,linestyle='--')
tight_layout()
if os.environ.get('HONU_GUI_NO_MPL')!='1': show()
