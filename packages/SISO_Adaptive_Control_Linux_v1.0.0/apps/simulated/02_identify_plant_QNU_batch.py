from matplotlib.pyplot import *
from numpy import *
from honu_basis import qnu_feature_count, qnu_features_and_jacobian
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
    plant_qnu_batch_r_0,
    plant_qnu_batch_stability_guard,
    plant_qnu_batch_rho_target,
    plant_qnu_batch_lambda_growth,
    plant_qnu_batch_lambda_max,
    plant_batch_mu_w_bibs,
    plant_batch_eps_bibs,
    plant_batch_plot_bibs_limit,
    plant_qnu_file_batch as plant_file_batch,
    bibs_plant_qnu_file_batch as bibs_plant_file,
)

n_y = plant_n_y
n_u = plant_n_u
r_0_requested = float(plant_qnu_batch_r_0)

##==inits
n_u1 = int(tau_u/dt)
n_x = n_y + n_u
n_xi = 1 + n_x
n_phi = qnu_feature_count(n_xi)
n_w = n_phi

u, y, normalization = load_normalized_uy(uy_file, simulated_normalization_file)

N = len(y)
t = arange(N)*dt

x = zeros(n_x)
y_n = zeros(N)
e = zeros(N)

N_start = builtins.max(n_u1+n_u, n_y)

X = zeros((N-N_start, n_phi))
Y = zeros(N-N_start)

#-BIBS monitoring arrays
mu_w = plant_batch_mu_w_bibs
eps_bibs = plant_batch_eps_bibs
plot_bibs_limit = plant_batch_plot_bibs_limit
eta_w = full(N, nan)
A2_w = full(N, nan)
Rho_w = full(N, nan)
A2_y = full(N, nan)
Rho_y = full(N, nan)


def qnu_phi_and_jacobian_x(x):
    x_aug = ones(n_xi)
    x_aug[1:] = x
    phi, J_aug = qnu_features_and_jacobian(x_aug)
    return phi, J_aug[:, 1:]


def qnu_local_output_metrics(candidate_w, store=False):
    """Return max local rho(A_y); optionally store the full BIBS traces."""
    max_rho = 0.0
    max_a2 = 0.0
    for k in range(N_start, N):
        x[:n_y] = y[k-n_y:k][::-1]
        x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
        _, J_x = qnu_phi_and_jacobian_x(x)
        grad_x_y = candidate_w @ J_x
        A_y = zeros((n_y, n_y))
        A_y[0, :] = grad_x_y[:n_y]
        if n_y > 1:
            A_y[1:, :-1] = eye(n_y-1)
        if not all(isfinite(A_y)):
            return inf, inf
        a2 = linalg.norm(A_y, 2)
        rho = builtins.max(abs(linalg.eigvals(A_y)))
        max_a2 = builtins.max(max_a2, float(a2))
        max_rho = builtins.max(max_rho, float(rho))
        if store:
            A2_y[k] = a2
            Rho_y[k] = rho
    return max_rho, max_a2


##==Build regression matrix
for k in range(N_start, N):
    x[:n_y] = y[k-n_y:k][::-1]
    x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
    phi, _ = qnu_phi_and_jacobian_x(x)
    X[k-N_start, :] = phi
    Y[k-N_start] = y[k]

    # BIBS monitoring of hypothetical normalized gradient weight dynamics
    # A_w(k) = I - eta_w(k) phi_Q(k) phi_Q(k)^T.
    eta_w[k] = mu_w/(phi @ phi + eps_bibs)
    # A_w is a rank-one correction of I.  Its spectral norm and radius are
    # available analytically, avoiding a dense 77x77 eigendecomposition.
    gradient_eigenvalue = 1.0 - eta_w[k]*(phi @ phi)
    A2_w[k] = builtins.max(1.0, abs(gradient_eigenvalue))
    Rho_w[k] = A2_w[k]

##==Batch Ridge learning with QNU local-stability guard
XT = X.T
R = XT @ X
P = XT @ Y


def solve_ridge(lambda_value):
    lambda_value = float(lambda_value)
    if lambda_value < 0.0 or not isfinite(lambda_value):
        raise ValueError("QNU Ridge lambda must be a finite non-negative value")
    if lambda_value == 0.0:
        # The original QNU basis contains lower-order terms together with
        # bias-product duplicates, so X can be rank deficient at lambda=0.
        return linalg.lstsq(X, Y, rcond=None)[0]
    return linalg.solve(R + lambda_value*eye(n_phi), P)


r_0_effective = r_0_requested
w = solve_ridge(r_0_effective)
max_rho_candidate, _ = qnu_local_output_metrics(w, store=False)

if plant_qnu_batch_stability_guard:
    rho_target = float(plant_qnu_batch_rho_target)
    growth = float(plant_qnu_batch_lambda_growth)
    lambda_max = float(plant_qnu_batch_lambda_max)
    if not (0.0 < rho_target < 1.0):
        raise ValueError("plant_qnu_batch_rho_target must be between 0 and 1")
    if growth <= 1.0:
        raise ValueError("plant_qnu_batch_lambda_growth must be larger than 1")
    if lambda_max <= 0.0:
        raise ValueError("plant_qnu_batch_lambda_max must be positive")

    while max_rho_candidate > rho_target and r_0_effective < lambda_max:
        if r_0_effective <= 0.0:
            r_0_effective = builtins.min(1.0e-12, lambda_max)
        else:
            r_0_effective = builtins.min(r_0_effective*growth, lambda_max)
        w = solve_ridge(r_0_effective)
        max_rho_candidate, _ = qnu_local_output_metrics(w, store=False)

    if max_rho_candidate > rho_target:
        raise RuntimeError(
            "QNU Ridge stability guard could not reach the requested local "
            f"rho(A_y) target {rho_target:.6g} before lambda_max={lambda_max:.6g}."
        )

if not all(isfinite(w)):
    raise FloatingPointError("QNU batch identification produced non-finite weights")


# Optional MRAC-specific recurrent rollout refinement.  The existing identifier
# supplies the initial one-step weights; each rollout is reinitialised from
# measured history and feeds back predicted y only within N_r steps.
w, rollout_info = refine_plant_weights(
    w, y, u, model="QNU", ny=n_y, nu=n_u, delay=n_u1,
    enabled=(str(mrac_plant_prediction_training).lower() == "recursive_rollout"),
    horizon=int(mrac_plant_rollout_length),
    iterations=int(mrac_plant_rollout_iterations),
    max_windows=int(mrac_plant_rollout_max_windows),
    discount=float(mrac_plant_rollout_discount), ridge=float(r_0_effective),
)

##==Evaluation and local QNU output-dynamics monitoring
SSE = 0.0
for k in range(N_start, N):
    x[:n_y] = y[k-n_y:k][::-1]
    x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
    phi, _ = qnu_phi_and_jacobian_x(x)
    y_n[k] = w @ phi
    e[k] = y[k] - y_n[k]
    SSE += e[k]**2

max_rho_final, max_a2_final = qnu_local_output_metrics(w, store=True)
rmse = sqrt(SSE/(N-N_start))

print("w =", w)
print(f"QNU Ridge lambda requested = {r_0_requested:.12g}")
print(f"QNU Ridge lambda effective = {r_0_effective:.12g}")
if r_0_effective != r_0_requested:
    print(
        "QNU stability guard increased lambda because the requested model "
        f"exceeded rho(A_y) target {plant_qnu_batch_rho_target:.6g}."
    )
print(f"SSE = {SSE:.6f}")
print(f"RMSE = {rmse:.9g}")
print(f"max ||A_w(k)||_2 = {nanmax(A2_w):.6f}")
print(f"max Rho(A_w(k)) = {nanmax(Rho_w):.6f}")
print(f"max ||A_y(k)||_2 = {max_a2_final:.6f}")
print(f"max Rho(A_y(k)) = {max_rho_final:.6f}")
print("Note: ||A_y||_2 may exceed 1 because the companion matrix contains unit delay-shift rows; use rho(A_y) for local pole stability.")

u_plot = denormalize_u(u, normalization)
y_plot = denormalize_y(y, normalization)
y_n_plot = denormalize_y(y_n, normalization)
e_plot = denormalize_error(e, normalization)

fig, ax = subplots(5, 1, sharex=True)
fig.suptitle(
    active_plant_display_name() + "\n" + r"Plant QNU batch Ridge, $\lambda_{req}$=" + str(r_0_requested) +
    r", $\lambda_{eff}$=" + str(r_0_effective) +
    r", BIBS spectral radii"
)
ax[0].plot(t, u_plot, 'b'); ax[0].set_ylabel("u")
ax[1].plot(t, y_plot, 'b', label="y"); ax[1].plot(t, y_n_plot, 'g', label="y_QNU"); ax[1].set_ylabel("y, y_QNU"); ax[1].legend(loc="best")
ax[2].plot(t, e_plot, 'r'); ax[2].set_ylabel("e")
ax[3].plot(t, Rho_w, 'k'); ax[3].set_ylabel(r"$\rho(A_w)$")
ax[4].plot(t, Rho_y, 'k'); ax[4].set_ylabel(r"$\rho(A_y(k))$")
if plot_bibs_limit:
    for i in range(3, 5):
        ax[i].axhline(1.0, linestyle='--')
for a in ax:
    a.grid(True)
ax[4].set_xlabel(f"t [sec], dt={dt} [sec]")

tight_layout()

# saving trained QNU plant
# layout remains backward compatible: dt, tau_u, n_u, n_u1, n_y, n_xi,
# n_phi, w...  The effective lambda is stored in the BIBS header only.
data = [dt, tau_u, n_u, n_u1, n_y, n_xi, n_phi, *w]
savetxt(plant_file_batch, data)
save_artifact_stats(plant_file_batch, normalization, "HONU plant")

bibs_data = column_stack((t, eta_w, A2_w, Rho_w, A2_y, Rho_y))
metadata = (
    f"requested_lambda={r_0_requested:.12g}, "
    f"effective_lambda={r_0_effective:.12g}, "
    f"rmse={rmse:.12g}, max_local_rho={max_rho_final:.12g}"
)
savetxt(
    bibs_plant_file,
    bibs_data,
    header=metadata + "\n" + "t eta_w A2_w Rho_Aw A2_y Rho_Ay"
)

import os as _os
if _os.environ.get("HONU_GUI_NO_MPL") != "1":
    show()
