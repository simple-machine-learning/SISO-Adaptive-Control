from matplotlib.pyplot import *
from numpy import *
import builtins

from shared_plant_model import active_plant_display_name
from simulated_normalization import (load_normalized_uy, save_artifact_stats,
    denormalize_u, denormalize_y, denormalize_error)


from mrac_rollout_plant_training import refine_plant_weights
from project_setup import (mrac_plant_prediction_training, mrac_plant_rollout_length,
    mrac_plant_rollout_iterations, mrac_plant_rollout_max_windows,
    mrac_plant_rollout_discount)

#==setups
from project_setup import (
    uy_file,
    simulated_normalization_file,
    dt,
    tau_u,
    plant_n_y,
    plant_n_u,
    plant_batch_r_0,
    plant_batch_mu_w_bibs,
    plant_batch_eps_bibs,
    plant_batch_plot_bibs_limit,
    plant_file_batch,
    bibs_plant_lnu_file_batch as bibs_plant_file,
)

n_y = plant_n_y
n_u = plant_n_u
r_0 = plant_batch_r_0

##==inits
n_u1 = int(tau_u/dt)
n_x_dyn = n_y + n_u
n_x = 1 + n_x_dyn   # canonical LNU plant regressor includes x_0=1
n_w = n_x

u, y, normalization = load_normalized_uy(uy_file, simulated_normalization_file)

N = len(y)
t = arange(N)*dt

x = zeros(n_x)
y_n = zeros(N)
e = zeros(N)

N_start = builtins.max(n_u1+n_u, n_y)

X = zeros((N-N_start, n_x))
Y = zeros(N-N_start)

#-BIBS monitoring arrays
mu_w = plant_batch_mu_w_bibs  # normalized plant-weight BIBS learning-rate constant, must be < 2
eps_bibs = plant_batch_eps_bibs  # regularization for eta_w(k)
plot_bibs_limit = plant_batch_plot_bibs_limit
eta_w = full(N, nan)
A2_w = full(N, nan)       # ||A_w(k)||_2, weight-update local dynamics
Rho_w = full(N, nan)      # rho(A_w(k))
A2_y = full(N, nan)       # ||A_y(k)||_2, LNU output autoregressive dynamics
Rho_y = full(N, nan)      # rho(A_y(k))

##==Build regression matrix
for k in range(N_start, N):

    x[0] = 1.0
    x[1:1+n_y] = y[k-n_y:k][::-1]
    x[1+n_y:1+n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]

    X[k-N_start, :] = x
    Y[k-N_start] = y[k]

    # BIBS monitoring of hypothetical normalized gradient weight dynamics
    # A_w(k) = I - eta_w(k) x(k) x(k)^T.
    # The final plant weights are still identified below by batch Ridge.
    eta_w[k] = mu_w/(x @ x + eps_bibs)
    A_w = eye(n_w) - eta_w[k]*outer(x, x)
    A2_w[k] = linalg.norm(A_w, 2)
    Rho_w[k] = max(abs(linalg.eigvals(A_w)))

##==Batch Ridge learning
    
#w = linalg.solve(X.T @ X + rho*eye(n_x), X.T @ Y)
XT = X.T
R = XT @ X            # autocorrelation matrix
P = XT @ Y            # cross-correlation vector
A = R + r_0*eye(n_x)
A_inv = linalg.inv(A)
w = A_inv @ P

# BIBS/stability monitoring of the identified LNU output dynamics
# y(k) = w_y^T [y(k-1), ..., y(k-n_y)] + forced input terms.
# A_y is the companion matrix of the autoregressive part.
A_y = zeros((n_y, n_y))
A_y[0, :] = w[1:1+n_y]
if n_y > 1:
    A_y[1:, :-1] = eye(n_y-1)
A2_y[:] = linalg.norm(A_y, 2)
Rho_y[:] = max(abs(linalg.eigvals(A_y)))


# Optional MRAC-specific recurrent rollout refinement.  The existing identifier
# supplies the initial one-step weights; each rollout is reinitialised from
# measured history and feeds back predicted y only within N_r steps.
w, rollout_info = refine_plant_weights(
    w, y, u, model="LNU", ny=n_y, nu=n_u, delay=n_u1,
    enabled=(str(mrac_plant_prediction_training).lower() == "recursive_rollout"),
    horizon=int(mrac_plant_rollout_length),
    iterations=int(mrac_plant_rollout_iterations),
    max_windows=int(mrac_plant_rollout_max_windows),
    discount=float(mrac_plant_rollout_discount), ridge=float(r_0),
)

##==Evaluation
SSE = 0.0

for k in range(N_start, N):

    x[0] = 1.0
    x[1:1+n_y] = y[k-n_y:k][::-1]
    x[1+n_y:1+n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]

    y_n[k] = w @ x
    e[k] = y[k] - y_n[k]

    SSE += e[k]**2

print("w =", w)
print(f"SSE = {SSE:.6f}")
print(f"max ||A_w(k)||_2 = {nanmax(A2_w):.6f}")
print(f"max Rho(A_w(k)) = {nanmax(Rho_w):.6f}")
print(f"||A_y||_2 = {nanmax(A2_y):.6f}")
print(f"Rho(A_y) = {nanmax(Rho_y):.6f}")

# Physical copies for presentation only; identification and diagnostics stay normalized.
u_plot = denormalize_u(u, normalization)
y_plot = denormalize_y(y, normalization)
y_n_plot = denormalize_y(y_n, normalization)
e_plot = denormalize_error(e, normalization)

##==Plots
fig, ax = subplots(5, 1, sharex=True)

fig.suptitle(active_plant_display_name() + "\n" + r"Plant LNU batch Ridge, $r_0$="+str(r_0)+r", BIBS spectral radii")

ax[0].plot(t, u_plot, 'b')
ax[0].set_ylabel("u")

ax[1].plot(t, y_plot, 'b')
ax[1].plot(t, y_n_plot, 'g')
ax[1].set_ylabel("y, y_n")

ax[2].plot(t, e_plot, 'r')
ax[2].set_ylabel("e")

ax[3].plot(t, Rho_w, 'k')
if plot_bibs_limit:
    ax[3].axhline(1.0, linestyle='--')
ax[3].set_ylabel(r"$\rho(A_w)$")

ax[4].plot(t, Rho_y, 'k')
if plot_bibs_limit:
    ax[4].axhline(1.0, linestyle='--')
ax[4].set_ylabel(r"$\rho(A_y(k))$")

for a in ax:
    a.grid(True)

ax[4].set_xlabel(f"t [sec], dt={dt} [sec]")

tight_layout()

import os as _os
if _os.environ.get("HONU_GUI_NO_MPL") != "1":
    show()

#saving trained LNU
data = [dt, tau_u, n_u, n_u1, n_y, *w]
savetxt(
    plant_file_batch,
    data,
#    fmt="%.9"
)
save_artifact_stats(plant_file_batch, normalization, "HONU plant")

#saving BIBS monitoring
bibs_data = column_stack((t, eta_w, A2_w, Rho_w, A2_y, Rho_y))
savetxt(
    bibs_plant_file,
    bibs_data,
    header="t eta_w A2_w Rho_Aw A2_y Rho_Ay"
)



