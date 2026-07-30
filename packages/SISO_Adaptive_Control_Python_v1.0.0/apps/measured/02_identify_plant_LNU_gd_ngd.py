from matplotlib.pyplot import *
from numpy import *
import builtins

from simulated_normalization import (load_normalized_uy, save_artifact_stats,
    denormalize_u, denormalize_y, denormalize_error)

#==setups
from project_setup import (
    uy_file,
    simulated_normalization_file,
    dt,
    tau_u,
    plant_n_y,
    plant_n_u,
    mu_w,
    plant_gd_ngd_learning,
    plant_gd_ngd_epochs,
    plant_gd_ngd_eps,
    plant_file_gd_ngd,
    bibs_plant_lnu_file_gd_ngd as bibs_plant_file,
)

uy = uy_file
n_y = plant_n_y
n_u = plant_n_u
mu = mu_w
learning = plant_gd_ngd_learning
epochs = plant_gd_ngd_epochs
eps = plant_gd_ngd_eps

##==inits
n_u1=int(tau_u/dt)
n_x_dyn=n_y+n_u
n_x=1+n_x_dyn  # canonical LNU plant regressor includes x_0=1
n_w=n_x  # for LNU
w=random.randn(n_w)/n_w
u, y, normalization = load_normalized_uy(uy_file, simulated_normalization_file, target_dt=dt)
N=len(y)
T_sim=N*dt
x=zeros(n_x)     #x=[1, y(k-1) y(k-2) ... y(k-ny) u(k-nu1-1) u(k-nu1-1) ... u(k-nu1-nu)]
y_n=zeros(N)
yreal=zeros(N)
e=zeros(N)
W=zeros((N,n_w))   #weights within one epoch
N_start=builtins.max(n_u1+n_u,n_y)
W[:N_start,:]=w
N_all=N*epochs
W_all=zeros((N_all,n_w))           #  for all epochs
A2_w=full(N_all, nan)              # ||A_w(k)||_2 for BIBS weight dynamics
Rho_w=full(N_all, nan)             # spectral radius rho(A_w(k))
A2_y=full(N_all, nan)              # ||A_y(k)||_2 for autonomous LNU output dynamics
Rho_y=full(N_all, nan)             # spectral radius rho(A_y(k))
y_n_all=zeros(N_all)         #  for all epochs
y_all=zeros(N_all)          #  for all epochs
e_all=zeros(N_all)
u_all=zeros(N_all)
t_all=arange(N_all)*dt

##==Plant LNU
k_all=N_start
for epoch in range(epochs):
    for k in range(N_start,N):  
        x[0]=1.0
        x[1:1+n_y]=y[k-n_y:k][::-1]  # [y(k-1), y(k-2) ,..,y(k-n_y)
        x[1+n_y:1+n_y+n_u]=u[k-n_u1-n_u:k-n_u1][::-1] # [u(k-n_u1-1), y(k-n_u1-2) ..]
        y_n[k]=w@x
        e[k]=y[k]-y_n[k]
        if learning=="GD":
            eta_w=mu
            dw=eta_w*e[k]*x
        elif learning=="NGD":
            eta_w=mu/(eps+x@x)
            dw=eta_w*e[k]*x

        # BIBS monitoring of local weight-update dynamics for LNU
        # w(k+1) = A_w(k) w(k) + eta_w(k) x(k) y(k)
        # A_w(k) = I - eta_w(k) x(k) x(k)^T
        A_w=eye(n_w)-eta_w*outer(x,x)
        A2_w[k_all]=linalg.norm(A_w,2)
        Rho_w[k_all]=max(abs(linalg.eigvals(A_w)))

        w=w+dw

        # BIBS monitoring of autonomous LNU output dynamics
        # y_n(k) = w_y1*y_n(k-1) + ... + w_yny*y_n(k-n_y) + forced terms from u
        # A_y(k) is the companion matrix of the y-recursive part.
        A_y=zeros((n_y,n_y))
        A_y[0,:]=w[1:1+n_y]
        if n_y>1:
            A_y[1:,:-1]=eye(n_y-1)
        A2_y[k_all]=linalg.norm(A_y,2)
        Rho_y[k_all]=max(abs(linalg.eigvals(A_y)))
        W[k,:]=w

        W_all[k_all,:]=w
        y_n_all[k_all]=y_n[k]
        y_all[k_all]=y[k]
        e_all[k_all]=e[k]
        u_all[k_all]=u[k]
        k_all+=1

print(f"max ||A_w(k)||_2 = {nanmax(A2_w):.6f}")
print(f"max Rho(A_w(k)) = {nanmax(Rho_w):.6f}")
print(f"max ||A_y(k)||_2 = {nanmax(A2_y):.6f}")
print(f"max Rho(A_y(k)) = {nanmax(Rho_y):.6f}")

fig, ax = subplots(6, 1, sharex=True)
fig.suptitle("Measured dataset" + "\n" + "Plant LNU learning=" + learning + r" $\mu$=" + str(mu) + ", BIBS spectral radii")
ax[0].plot(t_all, denormalize_u(u_all, normalization), 'b')
ax[0].set_ylabel('u')
ax[1].plot(t_all, denormalize_y(y_all, normalization), 'b')
ax[1].plot(t_all, denormalize_y(y_n_all, normalization), 'g')
ax[1].set_ylabel('y, y_n')
ax[2].plot(t_all, denormalize_error(e_all, normalization), 'r')
ax[2].set_ylabel('e')
ax[3].plot(t_all, W_all)
ax[3].set_ylabel("w")

ax[4].plot(t_all, Rho_w, 'k')
ax[4].axhline(1.0, linestyle='--')
ax[4].set_ylabel(r"$\rho(A_w)$")

ax[5].plot(t_all, Rho_y, 'k')
ax[5].axhline(1.0, linestyle='--')
ax[5].set_ylabel(r"$\rho(A_y(k))$")

for a in ax:
    a.grid(True)

ax[5].set_xlabel(f"t [sec], dt={dt} [sec]")

# Save trained GD/NGD LNU plant in the same format as the batch Ridge plant.
# This is intentionally before show(), because show() can block in some Windows
# backends and the controller must be able to select this plant file.
save_data = r_[dt, tau_u, n_u, n_u1, n_y, w]
savetxt(plant_file_gd_ngd, save_data)
save_artifact_stats(plant_file_gd_ngd, normalization, "HONU plant")

#saving BIBS weight-dynamics monitoring
bibs_data=column_stack((t_all,A2_w,Rho_w,A2_y,Rho_y))
savetxt(
    bibs_plant_file,
    bibs_data,
    header="t A2_w Rho_Aw A2_y Rho_Ay"
)

import os as _os
if _os.environ.get("HONU_GUI_NO_MPL") != "1":
    show()


