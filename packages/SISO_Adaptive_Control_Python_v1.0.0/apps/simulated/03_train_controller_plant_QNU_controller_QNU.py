from matplotlib.pyplot import *
from numpy import *
from honu_basis import qnu_feature_count, qnu_features_and_jacobian
import builtins



from shared_plant_model import active_plant_display_name
from reference_model_dt_sim import advance_reference_model
from simulated_normalization import (load_normalized_uy, load_artifact_stats, assert_same_stats,
    save_artifact_stats, normalize_y, denormalize_y, denormalize_u, denormalize_error)

# =============================================================================
# Setup
# =============================================================================

from project_setup import (
    uy_file,
    simulated_normalization_file,
    controller_qnu_plant_file as plant_file,
    ctrl_qnu_qnu_file as ctrl_file,
    controller_seed as seed,
    Tau_1,
    Tau_2,
    ctrl_qnu_learning as learning,
    ctrl_qnu_epochs as epochs,
    mu_v_qnu as mu_v,
    mu_r_0_qnu as mu_r_0,
    ctrl_qnu_eps as eps,
    qnu_v_norm_max,
    r_0_min,
    r_0_max,
    r_0_init,
    alpha_v_qnu as alpha_v, alpha_r_0_qnu as alpha_r_0,
    bibs_ctrl_qnu_qnu_file as bibs_ctrl_file,
    reference_type,
    reference_seed,
    d_min,
    d_max,
    reference_duration_sec,
    reference_step_hold_sec,
    dt_sim,
)

# =============================================================================
# Loading original plant data
# =============================================================================

u_data, y_data, normalization = load_normalized_uy(uy_file, simulated_normalization_file)
plant_normalization = load_artifact_stats(plant_file)
assert_same_stats(normalization, plant_normalization, "module 01 data versus trained HONU plant")
normalization = plant_normalization

# Build the controller-training reference from the same GUI/setup selection
# used by module 04. Alternating steps are deterministic; random steps use
# reference_seed; plant_input explicitly replays the module-01 excitation.
from reference_signal import make_reference_signal, normalize_reference_type, validate_reference_domain

reference_mode = normalize_reference_type(reference_type)
reference_sample_count = builtins.max(2, int(round(reference_duration_sec / float(normalization["dt"]))) + 1)
reference_plant_input = denormalize_u(resize(asarray(u_data, dtype=float).reshape(-1), reference_sample_count), normalization)
d_physical = make_reference_signal(
    reference_type=reference_mode,
    sample_count=reference_sample_count,
    dt=float(normalization["dt"]),
    d_min=d_min,
    d_max=d_max,
    step_hold_sec=reference_step_hold_sec,
    seed=reference_seed,
    plant_input=reference_plant_input,
)
validate_reference_domain(d_physical, denormalize_y(y_data, normalization), context="module 03")
d = asarray(normalize_y(d_physical, normalization), dtype=float)


# =============================================================================
# Loading trained QNU plant
# =============================================================================

data = loadtxt(plant_file)
dt = data[0]
tau_u = data[1]
n_u = int(data[2])
n_u1 = int(data[3])
n_y = int(data[4])
plant_n_xi = int(data[5])
plant_n_phi = int(data[6])
w = data[7:]

if len(w) != plant_n_phi:
    raise ValueError("Loaded plant is not a compatible QNU plant file. Run 02_Plant_QNU_* first.")

N = len(d)
t = arange(N)*dt
reference_metadata = (
    f"training_reference_type={reference_mode}, "
    f"reference_duration_sec={reference_duration_sec:g}, "
    f"reference_step_hold_sec={reference_step_hold_sec:g}, "
    f"configured_d_min={d_min:g}, configured_d_max={d_max:g}, "
    f"actual_d_physical_min={amin(d_physical):g}, actual_d_physical_max={amax(d_physical):g}, "
    f"actual_d_z_min={amin(d):g}, actual_d_z_max={amax(d):g}, "
    f"reference_delay_samples={n_u1}, "
    f"reference_delay_sec={n_u1*dt:g}"
)
print("training reference d: " + reference_metadata + f", samples={N}")

# =============================================================================
# Dimensions and initialization
# =============================================================================

if not (0.0 <= alpha_v <= 1.0 and 0.0 <= alpha_r_0 <= 1.0):
    raise ValueError("alpha_v and alpha_r_0 must lie in [0, 1]")

random.seed(seed)

n_e = n_y
n_x = n_y + n_u
n_xi = 1 + n_y + n_e
n_phi = qnu_feature_count(n_xi)
n_v = n_phi


plant_qnu_pairs = []
for i in range(plant_n_xi):
    for j in range(i, plant_n_xi):
        plant_qnu_pairs.append((i, j))

v = random.randn(n_v)/n_v
r_0_value = float(r_0_init)

# Limit only the recursively predicted output state to the identified output
# domain. The controller command u is intentionally unrestricted in module 03.
y_domain_min = float(amin(y_data))
y_domain_max = float(amax(y_data))

N_start = builtins.max(n_y, n_e, n_u1 + n_u, n_u1 + 1)
N_episode = N - N_start
N_all = N_episode*epochs

# Each epoch starts from the same zero initial state, so it must also use
# the same complete reference record.  Continuing the reference phase while
# resetting plant/controller histories creates an inconsistent training episode.
# The displayed trace is still stored only for actually processed samples.

# Store only samples that are actually processed by controller adaptation.
# Do not pad each epoch with zero-filled, unprocessed samples.
t_all = arange(N_all)*dt
d_all = zeros(N_all)

V_all = zeros((N_all, n_v))
y_all = zeros(N_all)
y_ref_all = zeros(N_all)
e_ref_all = zeros(N_all)
u_all = zeros(N_all)
q_all = zeros(N_all)
r_0_all = zeros(N_all)
g_v_norm_all = zeros(N_all)
g_r_0_all = zeros(N_all)

# BIBS monitoring of local controller weight-update dynamics
# v(k+1) = A_v(k) v(k) + forced terms
# Local Gauss-Newton form: A_v(k) = I - eta_v(k) g_v(k) g_v(k)^T
A2_v_all = full(N_all, nan)
Rho_v_all = full(N_all, nan)
A_abs_r_0_all = full(N_all, nan)

# Closed-loop characteristic polynomial norm and spectral radius
# m contains only the first row coefficients of the closed-loop companion matrix.
# ||m||_2 is dimensionally cleaner than ||M||_2 because it does not include
# the unit shift rows of the companion matrix.
n_M = builtins.max(n_y, n_u1 + n_u + n_y - 1)
m_norm_all = zeros(N_all)
Rho_all = zeros(N_all)



def qnu_phi_and_jacobian(xi):
    """Canonical QNU: phi=[xi_i*xi_j], 0<=i<=j; xi_0=1 supplies bias and linear terms once."""
    return qnu_features_and_jacobian(xi)


def qnu_phi(xi):
    phi, _ = qnu_phi_and_jacobian(xi)
    return phi


def plant_qnu_phi_and_jacobian_x(x):
    """Canonical non-redundant QNU plant basis with x_0=1 exactly once."""
    xi_p = ones(plant_n_xi)
    xi_p[1:] = x
    phi_p, J_xi = qnu_features_and_jacobian(xi_p)
    if phi_p.size != plant_n_phi:
        raise ValueError(
            f"QNU plant basis mismatch: generated {phi_p.size}, expected {plant_n_phi}"
        )
    return phi_p, J_xi[:, 1:]


def closed_loop_characteristic_metrics(w, v, r_0_value, x_operating, xi_operating, n_y, n_u, n_u1, n_M):
    # QNU plant and QNU controller are both locally linearized.
    # Plant: y(k) ~= a_y^T[y(k-1)..] + a_u^T[u(k-n_u1-1)..] + forced terms.
    # Controller: q(k) ~= c_y^T[y(k-1)..] + c_e^T[e(k-1)..] + forced terms.
    # In the homogeneous closed-loop test d=0 and y_ref=0, hence e_ref=y.

    _, J_x_p = plant_qnu_phi_and_jacobian_x(x_operating)
    grad_x_y = w @ J_x_p
    a_y = grad_x_y[:n_y]
    a_u = grad_x_y[n_y:n_y+n_u]

    _, J_phi_c = qnu_phi_and_jacobian(xi_operating)
    grad_xi_q = v @ J_phi_c
    c_y = grad_xi_q[1:1+n_y]
    c_e = grad_xi_q[1+n_y:1+n_y+n_y]
    c_cl = c_y + c_e

    m = zeros(n_M)
    m[:n_y] = a_y

    for j in range(n_u):
        for p in range(n_y):
            r = n_u1 + (j + 1) + p
            if r < n_M:
                m[r] = m[r] - r_0_value*a_u[j]*c_cl[p]

    M = zeros((n_M, n_M))
    M[0, :] = m
    M[1:, :-1] = eye(n_M - 1)

    m_norm = linalg.norm(m, 2)
    if all(isfinite(M)):
        Rho = max(abs(linalg.eigvals(M)))
    else:
        Rho = nan

    return m_norm, Rho

# =============================================================================
# Module 03: controller training on QNU HONU plant
# =============================================================================

k_all = 0

# Exponential smoothing state for QNU controller updates.
# Keep it across epochs because controller parameters are also retained.
dv_smooth = zeros(n_v)
dr_0_smooth = 0.0

for epoch in range(epochs):
    d_epoch = d

    # One simulated episode. Controller parameters v and r_0_value are NOT reset.
    y = zeros(N)
    y_ref = zeros(N)
    e_ref = zeros(N)
    u = zeros(N)
    q = zeros(N)

    dydv = zeros((N, n_v))
    dudv = zeros((N, n_v))
    dydr_0 = zeros(N)
    dudr_0 = zeros(N)

    x = zeros(n_x)
    xi = ones(n_xi)
    dxdv = zeros((n_x, n_v))
    dxdr_0 = zeros(n_x)
    dxidv = zeros((n_xi, n_v))
    dxidr_0 = zeros(n_xi)

    z = 0.0

    for k in range(N_start, N):

        # ---------------------------------------------------------------------
        # Controller regressor xi(k-1)
        # xi = [1, y(k-1), ..., y(k-n_y), e_ref(k-1), ..., e_ref(k-n_e)]
        # ---------------------------------------------------------------------

        xi[0] = 1.0
        xi[1:1+n_y] = y[k-n_y:k][::-1]
        xi[1+n_y:] = e_ref[k-n_e:k][::-1]

        dxidv[:, :] = 0.0
        dxidv[1:1+n_y, :] = dydv[k-n_y:k, :][::-1]
        dxidv[1+n_y:, :] = dydv[k-n_e:k, :][::-1]

        dxidr_0[:] = 0.0
        dxidr_0[1:1+n_y] = dydr_0[k-n_y:k][::-1]
        dxidr_0[1+n_y:] = dydr_0[k-n_e:k][::-1]

        phi, J_phi = qnu_phi_and_jacobian(xi)
        q[k-1] = v @ phi

        # Exact local sensitivities of the unrestricted QNU output q.
        grad_xi_q = v @ J_phi
        dqdv = phi + grad_xi_q @ dxidv
        dqdr_0 = grad_xi_q @ dxidr_0

        # u(k-1) = r_0*(d(k-1) - q(k-1))
        u[k-1] = r_0_value*(d_epoch[k-1] - q[k-1])
        dudv[k-1, :] = -r_0_value*dqdv
        dudr_0[k-1] = (d_epoch[k-1] - q[k-1]) - r_0_value*dqdr_0

        # ---------------------------------------------------------------------
        # QNU plant
        # y(k) = w^T phi_Q([1, y(k-1), ..., u(k-n_u1-n_u)]).
        # The exact local sensitivities use the QNU plant Jacobian.
        # ---------------------------------------------------------------------

        x[:n_y] = y[k-n_y:k][::-1]
        x[n_y:] = u[k-n_u1-n_u:k-n_u1][::-1]
        x_bounded = x.copy()
        x_bounded[:n_y] = clip(x_bounded[:n_y], y_domain_min, y_domain_max)
        y_domain_mask = ((x[:n_y] > y_domain_min) &
                         (x[:n_y] < y_domain_max)).astype(float)
        phi_p, J_x_p = plant_qnu_phi_and_jacobian_x(x_bounded)
        J_x_p[:, :n_y] = J_x_p[:, :n_y]*y_domain_mask[None, :]

        y_raw = w @ phi_p
        y[k] = minimum(maximum(y_raw, y_domain_min), y_domain_max)
        if y_raw <= y_domain_min or y_raw >= y_domain_max:
            grad_x_y = zeros(n_x)
        else:
            grad_x_y = w @ J_x_p

        dxdv[:n_y, :] = dydv[k-n_y:k, :][::-1]
        dxdv[n_y:, :] = dudv[k-n_u1-n_u:k-n_u1, :][::-1]
        dydv[k, :] = grad_x_y @ dxdv

        dxdr_0[:n_y] = dydr_0[k-n_y:k][::-1]
        dxdr_0[n_y:] = dudr_0[k-n_u1-n_u:k-n_u1][::-1]
        dydr_0[k] = grad_x_y @ dxdr_0

        # ---------------------------------------------------------------------
        # Reference model with the original plant-input delay convention
        # ---------------------------------------------------------------------

        z, y_ref[k] = advance_reference_model(
            z, y_ref[k-1], d_epoch[k-n_u1-1],
            dt, dt_sim, Tau_1, Tau_2,
        )
        e_ref[k] = y[k] - y_ref[k]

        # ---------------------------------------------------------------------
        # Controller adaptation
        # ---------------------------------------------------------------------

        g_v = dydv[k, :]
        g_r_0 = dydr_0[k]

        # Stable GD/NGD evaluation. The direct expressions g@g and g_r_0**2
        # can overflow for large QNU sensitivities even when the normalized
        # update remains finite. Use scaled norms and exact rank-one
        # eigenvalues instead; u remains unrestricted.
        g_v_norm = linalg.norm(g_v, 2)
        g_r_abs = abs(g_r_0)
        if not (isfinite(g_v_norm) and isfinite(g_r_abs) and isfinite(e_ref[k])):
            raise FloatingPointError(
                f"non-finite QNU controller sensitivity at epoch={epoch+1}, k={k}: "
                f"||g_v||={g_v_norm}, |g_r_0|={g_r_abs}, e_ref={e_ref[k]}"
            )

        if learning == "NGD":
            if g_v_norm > 0.0:
                denom_v_scaled = g_v_norm + eps/g_v_norm
                dv = -mu_v*e_ref[k]*(g_v/g_v_norm)/denom_v_scaled
                eta_g2_v = mu_v*(g_v_norm/(g_v_norm + eps/g_v_norm))
            else:
                dv = zeros_like(g_v)
                eta_g2_v = 0.0

            if g_r_abs > 0.0:
                denom_r_scaled = g_r_abs + eps/g_r_abs
                dr_0 = -mu_r_0*e_ref[k]*(g_r_0/g_r_abs)/denom_r_scaled
                eta_g2_r = mu_r_0*(g_r_abs/(g_r_abs + eps/g_r_abs))
            else:
                dr_0 = 0.0
                eta_g2_r = 0.0
        elif learning == "GD":
            dv = -mu_v*e_ref[k]*g_v
            dr_0 = -mu_r_0*e_ref[k]*g_r_0
            eta_g2_v = mu_v*g_v_norm*g_v_norm
            eta_g2_r = mu_r_0*g_r_abs*g_r_abs
        else:
            raise ValueError("learning must be 'GD' or 'NGD'")

        if not (all(isfinite(dv)) and isfinite(dr_0)):
            raise FloatingPointError(
                f"non-finite QNU controller update at epoch={epoch+1}, k={k}"
            )

        rank_one_eig = 1.0 - eta_g2_v
        A2_v_all[k_all] = builtins.max(1.0, abs(rank_one_eig))
        Rho_v_all[k_all] = A2_v_all[k_all]
        A_abs_r_0_all[k_all] = abs(1.0 - eta_g2_r)

        dv_smooth = alpha_v*dv + (1.0-alpha_v)*dv_smooth
        dr_0_smooth = alpha_r_0*dr_0 + (1.0-alpha_r_0)*dr_0_smooth
        v = v + dv_smooth
        v_norm = linalg.norm(v, 2)
        if v_norm > qnu_v_norm_max:
            v = v*(qnu_v_norm_max/v_norm)

        r_0_value = r_0_value + dr_0_smooth
        r_0_value = minimum(maximum(r_0_value, r_0_min), r_0_max)

        # ---------------------------------------------------------------------
        # Store all epochs on one extended time axis
        # ---------------------------------------------------------------------

        d_all[k_all] = d_epoch[k]
        V_all[k_all, :] = v
        y_all[k_all] = y[k]
        y_ref_all[k_all] = y_ref[k]
        e_ref_all[k_all] = e_ref[k]
        u_all[k_all] = u[k-1]
        q_all[k_all] = q[k-1]
        r_0_all[k_all] = r_0_value
        g_v_norm_all[k_all] = sqrt(g_v @ g_v)
        g_r_0_all[k_all] = g_r_0
        m_norm_all[k_all], Rho_all[k_all] = closed_loop_characteristic_metrics(
            w, v, r_0_value, x, xi, n_y, n_u, n_u1, n_M
        )

        k_all += 1


    rmse = float(sqrt(mean(e_ref[N_start:]**2)))
    print(f"Controller QNU-QNU epoch {epoch+1}/{epochs}: RMSE={rmse:.6g}, r_0={r_0_value:.6g}", flush=True)

# =============================================================================
# Module 03 output: save trained controller
# =============================================================================

save_data = r_[dt, tau_u, n_u, n_u1, n_y, n_e, n_xi, n_phi, r_0_value, v]
savetxt(ctrl_file, save_data)
save_artifact_stats(ctrl_file, normalization, "HONU controller")

print(f"max ||A_v(k)||_2 = {nanmax(A2_v_all):.6f}")
print(f"max Rho(A_v(k)) = {nanmax(Rho_v_all):.6f}")
print(f"max |A_r_0(k)| = {nanmax(A_abs_r_0_all):.6f}")
print(f"max ||m(k)||_2 = {nanmax(m_norm_all):.6f}")
print(f"max Rho(M(k)) = {nanmax(Rho_all):.6f}")

bibs_data = column_stack((t_all, A2_v_all, Rho_v_all, A_abs_r_0_all, m_norm_all, Rho_all))
savetxt(
    bibs_ctrl_file,
    bibs_data,
    header="t A2_v Rho_Av A_abs_r_0 m_norm Rho_M"
)

training_trace_file = bibs_ctrl_file.replace("bibs_controller_", "training_controller_")
d_trace = denormalize_y(d_all, normalization)
y_ref_trace = denormalize_y(y_ref_all, normalization)
y_trace = denormalize_y(y_all, normalization)
e_ref_trace = denormalize_error(e_ref_all, normalization)
u_trace = denormalize_u(u_all, normalization)
q_trace = denormalize_y(q_all, normalization)
training_cols = [
    "t", "d", "y_ref", "y", "e_ref", "u", "q", "r_0",
    "g_v_norm", "g_r_0", "Rho_Av", "A_abs_r_0", "Rho_M",
]
training_cols += [f"v_{i}" for i in range(V_all.shape[1])]
training_data = column_stack((
    t_all, d_trace, y_ref_trace, y_trace, e_ref_trace, u_trace, q_trace, r_0_all,
    g_v_norm_all, g_r_0_all, Rho_v_all, A_abs_r_0_all, Rho_all, V_all
))
savetxt(
    training_trace_file,
    training_data,
    header=reference_metadata + "\n" + " ".join(training_cols)
)


print(f"Final epoch {epochs}/{epochs}; RMSE={rmse:.6g}", flush=True)

# =============================================================================
# Module 03 training plots
# =============================================================================

# Physical copies for presentation only. Internal learning histories remain normalized.
d_plot = denormalize_y(d_all, normalization)
y_ref_plot = denormalize_y(y_ref_all, normalization)
y_plot = denormalize_y(y_all, normalization)
e_ref_plot = denormalize_error(e_ref_all, normalization)
u_plot = denormalize_u(u_all, normalization)


fig, ax = subplots(7, 1, sharex=True, figsize=(10, 13))
fig.suptitle(
    active_plant_display_name() + "\n" + r"QNU plant + QNU controller, learning=" + learning +
    r", $\mu_v$=" + str(mu_v) +
    r", $\mu_{r_0}$=" + str(mu_r_0) +
    f", controller dt={dt} s"
)

ax[0].plot(t_all, d_plot, 'b', label="d", drawstyle="steps-post")
ax[0].set_ylabel("d")
ax[0].ticklabel_format(axis="y", style="plain", useOffset=False)
ax[0].legend(loc="best")

ax[1].plot(t_all, y_ref_plot, 'b', label="y_ref")
ax[1].plot(t_all, y_plot, 'g', label="y")
ax[1].set_ylabel("y, y_ref")
ax[1].legend(loc="best")

ax[2].plot(t_all, e_ref_plot, 'r')
ax[2].set_ylabel("regulation deviation")

ax[3].plot(t_all, V_all)
ax[3].set_ylabel("v")

ax[4].plot(t_all, r_0_all, 'b')
ax[4].set_ylabel(r"$r_0$")

ax[5].plot(t_all, Rho_v_all, 'k')
ax[5].axhline(1.0, linestyle='--')
ax[5].set_ylabel(r"$\rho(\mathbf{A}_v)$")

ax[6].plot(t_all, Rho_all, 'k')
ax[6].axhline(1.0, linestyle='--')
ax[6].set_ylabel(r"$\rho(\mathbf{M})$")
ax[6].set_xlabel(f"t [sec], dt={dt} [sec]")

for a in ax:
    a.grid(True)



import os as _os
if _os.environ.get("HONU_GUI_NO_MPL") != "1":
    show()

