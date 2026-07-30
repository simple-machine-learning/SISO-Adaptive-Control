from matplotlib.pyplot import *
from numpy import *
from honu_basis import qnu_feature_count, qnu_features_and_jacobian
import builtins

from project_setup import (
    uy_file,
    simulated_normalization_file,
    dt,
    tau_u,
    plant_n_y,
    plant_n_u,
    plant_gd_ngd_learning,
    plant_gd_ngd_epochs,
    plant_qnu_mu_w,
    plant_qnu_gd_stability_guard,
    plant_qnu_gd_mu_safety,
    plant_qnu_ngd_mu_max,
    plant_gd_ngd_eps,
    plant_batch_plot_bibs_limit,
    plant_qnu_file_gd_ngd as plant_file_gd_ngd,
    bibs_plant_qnu_file_gd_ngd as bibs_plant_file,
)

n_y = plant_n_y
n_u = plant_n_u
learning = plant_gd_ngd_learning
mu_w_requested = float(plant_qnu_mu_w)
epochs = plant_gd_ngd_epochs
eps = plant_gd_ngd_eps
plot_bibs_limit = plant_batch_plot_bibs_limit

n_u1 = int(tau_u/dt)
n_x = n_y + n_u
n_xi = 1 + n_x
n_phi = qnu_feature_count(n_xi)
n_w = n_phi

u, y, normalization = load_normalized_uy(uy_file, simulated_normalization_file)
N = len(y)
t = arange(N)*dt
N_start = builtins.max(n_u1+n_u, n_y)
N_all = N*epochs
t_all = arange(N_all)*dt

w = zeros(n_w)
x = zeros(n_x)
y_n = zeros(N)
e = zeros(N)

W_all = zeros((N_all, n_w))
y_all = zeros(N_all)
y_n_all = zeros(N_all)
e_all = zeros(N_all)
eta_w_all = full(N_all, nan)
A2_w_all = full(N_all, nan)
Rho_w_all = full(N_all, nan)
A2_y_all = full(N_all, nan)
Rho_y_all = full(N_all, nan)


def qnu_phi_and_jacobian_x(x):
    x_aug = ones(n_xi)
    x_aug[1:] = x
    phi, J_aug = qnu_features_and_jacobian(x_aug)
    return phi, J_aug[:, 1:]


from shared_plant_model import active_plant_display_name
from simulated_normalization import (load_normalized_uy, save_artifact_stats,
    denormalize_u, denormalize_y, denormalize_error)

# Determine a QNU-safe effective learning-rate before the online epochs start.
# For plain GD/LMS the local update eigenvalue is 1 - mu*||phi||^2, hence
# mu*||phi||^2 < 2 is required.  The configured safety value defaults to 1.
max_phi_energy = 0.0
for k in range(N_start, N):
    x[:n_y] = y[k-n_y:k][::-1]
    x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
    phi, _ = qnu_phi_and_jacobian_x(x)
    max_phi_energy = builtins.max(max_phi_energy, float(phi @ phi))

if mu_w_requested < 0.0 or not isfinite(mu_w_requested):
    raise ValueError("QNU mu_w must be a finite non-negative value")

if learning == "GD":
    if plant_qnu_gd_stability_guard:
        safety = float(plant_qnu_gd_mu_safety)
        if not (0.0 < safety < 2.0):
            raise ValueError("plant_qnu_gd_mu_safety must be between 0 and 2")
        mu_limit = safety/(eps + max_phi_energy)
        mu_w_effective = builtins.min(mu_w_requested, mu_limit)
    else:
        mu_limit = inf
        mu_w_effective = mu_w_requested
elif learning == "NGD":
    ngd_limit = float(plant_qnu_ngd_mu_max)
    if not (0.0 < ngd_limit < 2.0):
        raise ValueError("plant_qnu_ngd_mu_max must be between 0 and 2")
    mu_limit = ngd_limit
    mu_w_effective = builtins.min(mu_w_requested, ngd_limit)
else:
    raise ValueError("learning must be 'GD' or 'NGD'")

print(f"QNU {learning} mu_w requested = {mu_w_requested:.12g}")
print(f"QNU {learning} mu_w effective = {mu_w_effective:.12g}")
if mu_w_effective != mu_w_requested:
    print(
        f"QNU {learning} stability guard limited mu_w to {mu_w_effective:.12g}; "
        f"limit={mu_limit:.12g}, max ||phi||^2={max_phi_energy:.12g}."
    )

k_all = 0
for epoch in range(epochs):
    y_n[:] = 0.0
    e[:] = 0.0
    for k in range(N_start, N):
        x[:n_y] = y[k-n_y:k][::-1]
        x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
        phi, J_x = qnu_phi_and_jacobian_x(x)

        y_n[k] = w @ phi
        e[k] = y[k] - y_n[k]

        if learning == "NGD":
            eta_w = mu_w_effective/(eps + phi @ phi)
        else:  # GD was validated above
            eta_w = mu_w_effective

        # A_w = I - eta*phi*phi^T is a rank-one correction of I.
        gradient_eigenvalue = 1.0 - eta_w*(phi @ phi)
        A2_w_all[k_all] = builtins.max(1.0, abs(gradient_eigenvalue))
        Rho_w_all[k_all] = A2_w_all[k_all]

        w = w + eta_w*e[k]*phi
        if not all(isfinite(w)):
            raise FloatingPointError(
                f"QNU {learning} produced non-finite weights at epoch={epoch+1}, sample={k}. "
                "Reduce mu_w or use NGD."
            )

        grad_x_y = w @ J_x
        A_y = zeros((n_y, n_y))
        A_y[0, :] = grad_x_y[:n_y]
        if n_y > 1:
            A_y[1:, :-1] = eye(n_y-1)
        A2_y_all[k_all] = linalg.norm(A_y, 2)
        Rho_y_all[k_all] = builtins.max(abs(linalg.eigvals(A_y)))

        W_all[k_all, :] = w
        y_all[k_all] = y[k]
        y_n_all[k_all] = y_n[k]
        e_all[k_all] = e[k]
        eta_w_all[k_all] = eta_w
        k_all += 1

    while k_all < (epoch + 1)*N:
        W_all[k_all, :] = w
        if k_all > 0:
            eta_w_all[k_all] = eta_w_all[k_all-1]
            A2_w_all[k_all] = A2_w_all[k_all-1]
            Rho_w_all[k_all] = Rho_w_all[k_all-1]
            A2_y_all[k_all] = A2_y_all[k_all-1]
            Rho_y_all[k_all] = Rho_y_all[k_all-1]
        k_all += 1


# Optional MRAC-specific recurrent rollout refinement.  The existing identifier
# supplies the initial one-step weights; each rollout is reinitialised from
# measured history and feeds back predicted y only within N_r steps.
w, rollout_info = refine_plant_weights(
    w, y, u, model="QNU", ny=n_y, nu=n_u, delay=n_u1,
    enabled=(str(mrac_plant_prediction_training).lower() == "recursive_rollout"),
    horizon=int(mrac_plant_rollout_length),
    iterations=int(mrac_plant_rollout_iterations),
    max_windows=int(mrac_plant_rollout_max_windows),
    discount=float(mrac_plant_rollout_discount), ridge=float(0.0),
)

# Final fixed-weight one-step validation.  This is what the GUI identification
# preview displays and is not mixed with within-epoch pre-update predictions.
y_final = zeros(N)
e_final = zeros(N)
A2_y_final = full(N, nan)
Rho_y_final = full(N, nan)
SSE = 0.0
for k in range(N_start, N):
    x[:n_y] = y[k-n_y:k][::-1]
    x[n_y:n_y+n_u] = u[k-n_u1-n_u:k-n_u1][::-1]
    phi, J_x = qnu_phi_and_jacobian_x(x)
    y_final[k] = w @ phi
    e_final[k] = y[k] - y_final[k]
    SSE += e_final[k]**2

    grad_x_y = w @ J_x
    A_y = zeros((n_y, n_y))
    A_y[0, :] = grad_x_y[:n_y]
    if n_y > 1:
        A_y[1:, :-1] = eye(n_y-1)
    A2_y_final[k] = linalg.norm(A_y, 2)
    Rho_y_final[k] = builtins.max(abs(linalg.eigvals(A_y)))

rmse = sqrt(SSE/(N-N_start))

print("w =", w)
print(f"final fixed-weight SSE = {SSE:.6f}")
print(f"final fixed-weight RMSE = {rmse:.9g}")
print(f"max ||A_w(k)||_2 = {nanmax(A2_w_all):.6f}")
print(f"max Rho(A_w(k)) = {nanmax(Rho_w_all):.6f}")
print(f"final max ||A_y(k)||_2 = {nanmax(A2_y_final):.6f}")
print(f"final max Rho(A_y(k)) = {nanmax(Rho_y_final):.6f}")
print("Note: ||A_y||_2 may exceed 1 because the companion matrix contains unit delay-shift rows; use rho(A_y) for local pole stability.")

fig, ax = subplots(6, 1, sharex=True)
fig.suptitle(
    active_plant_display_name() + "\n" + r"Plant QNU " + learning +
    r", $\mu_{req}$=" + str(mu_w_requested) +
    r", $\mu_{eff}$=" + str(mu_w_effective) +
    r", BIBS spectral radii, dt=" + str(dt) + " s"
)
ax[0].plot(t_all, denormalize_y(y_all, normalization), 'b'); ax[0].set_ylabel("y")
ax[1].plot(t_all, denormalize_y(y_n_all, normalization), 'g'); ax[1].set_ylabel("y_QNU")
ax[2].plot(t_all, denormalize_error(e_all, normalization), 'r'); ax[2].set_ylabel("e")
ax[3].plot(t_all, W_all); ax[3].set_ylabel("w")
ax[4].plot(t_all, Rho_w_all, 'k'); ax[4].set_ylabel(r"$\rho(A_w)$")
ax[5].plot(t_all, Rho_y_all, 'k'); ax[5].set_ylabel(r"$\rho(A_y(k))$")
if plot_bibs_limit:
    for i in range(4, 6):
        ax[i].axhline(1.0, linestyle='--')
for a in ax:
    a.grid(True)
ax[5].set_xlabel(f"t [sec], dt={dt} [sec]")

tight_layout()

# Backward-compatible QNU plant file format.
data = [dt, tau_u, n_u, n_u1, n_y, n_xi, n_phi, *w]
savetxt(plant_file_gd_ngd, data)
save_artifact_stats(plant_file_gd_ngd, normalization, "HONU plant")

bibs_data = column_stack((t_all, eta_w_all, A2_w_all, Rho_w_all, A2_y_all, Rho_y_all))
metadata = (
    f"learning={learning}, requested_mu={mu_w_requested:.12g}, "
    f"effective_mu={mu_w_effective:.12g}, rmse={rmse:.12g}, "
    f"final_max_local_rho={nanmax(Rho_y_final):.12g}"
)
savetxt(
    bibs_plant_file,
    bibs_data,
    header=metadata + "\n" + "t eta_w A2_w Rho_Aw A2_y Rho_Ay"
)

import os as _os
if _os.environ.get("HONU_GUI_NO_MPL") != "1":
    show()
