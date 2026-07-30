# -*- coding: utf-8 -*-
"""Shared module-04 test of a trained controller on the physical ODE plant."""

from __future__ import annotations

import builtins
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from project_setup import (
    Tau_1,
    Tau_2,
    controller_plant_source,
    d_max,
    d_min,
    dt_sim,
    plant_model_name,
    plant_par,
    r_0_max,
    r_0_min,
    reference_seed,
    reference_duration_sec,
    reference_step_hold_sec,
    reference_type,
    reference_measured_y_column,
    solver_setup,
    tau_d,
    uy_file,
    simulated_normalization_file,
    preg_blackbox_enabled,
    r_preg,
    controller_lnu_plant_file,
    controller_qnu_plant_file,
    ctrl_learning,
    ctrl_qnu_learning,
    mu_v,
    mu_r_0,
    mu_v_qnu,
    mu_r_0_qnu,
    alpha_v,
    alpha_r_0,
    alpha_v_qnu,
    alpha_r_0_qnu,
    ctrl_eps,
    qnu_v_norm_max,
)
from reference_signal import finite_signal_range, make_reference_signal, validate_reference_domain
from reference_model_dt_sim import advance_reference_model
from honu_basis import qnu_feature_count, qnu_features, qnu_features_and_jacobian
from shared_plant_model import (plant_display_name, algebraic_outputs, controlled_output, initial_state, plant_signal_metadata, plant_signal_symbol, simulate_sample_period_zoh, simulate_sample_period_preg)
from simulated_normalization import (
    load_stats, load_artifact_stats, assert_same_stats, normalize_u, denormalize_u,
    normalize_y, denormalize_y, denormalize_error,
)


def qnu_phi(xi: np.ndarray) -> np.ndarray:
    return qnu_features(xi)


def qnu_phi_and_jacobian(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return qnu_features_and_jacobian(x)


def load_surrogate_plant(honu_plant_model: str) -> dict:
    """Load the identified HONU plant used only for online sensitivity propagation."""
    model = str(honu_plant_model).strip().upper()
    path = Path(controller_qnu_plant_file if model == "QNU" else controller_lnu_plant_file)
    if not path.exists():
        raise FileNotFoundError(f"Missing identified {model} plant: {path}. Run module 02 first.")
    data = np.asarray(np.loadtxt(path), dtype=float).reshape(-1)
    if model == "LNU":
        if data.size < 6:
            raise ValueError(f"{path} is too short for an LNU plant")
        dt, tau_u = float(data[0]), float(data[1])
        n_u, n_u1, n_y = (int(round(v)) for v in data[2:5])
        w = data[5:].copy()
        expected = 1 + n_y + n_u
        n_x = n_y + n_u
    elif model == "QNU":
        if data.size < 8:
            raise ValueError(f"{path} is too short for a QNU plant")
        dt, tau_u = float(data[0]), float(data[1])
        n_u, n_u1, n_y, plant_n_xi, n_phi = (int(round(v)) for v in data[2:7])
        w = data[7:].copy()
        expected_x = n_y + n_u
        expected_xi = 1 + expected_x
        expected_phi = qnu_feature_count(expected_xi)
        if plant_n_xi != expected_xi or n_phi != expected_phi:
            raise ValueError(f"{path} contains incompatible QNU dimensions")
        n_x = expected_x
        expected = n_phi
    else:
        raise ValueError("honu_plant_model must be 'LNU' or 'QNU'")
    if w.size != expected:
        raise ValueError(f"{path} contains {w.size} weights; expected {expected}")
    return {"model": model, "path": path, "dt": dt, "tau_u": tau_u,
            "n_u": n_u, "n_u1": n_u1, "n_y": n_y, "n_x": n_x, "w": w}

def load_controller(controller_file: str | Path, controller_model: str) -> dict:
    """Load and validate a controller saved by one of the module-03 scripts."""
    path = Path(controller_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing trained controller file: {path}. Run module 03 first."
        )

    data = np.asarray(np.loadtxt(path), dtype=float).reshape(-1)
    model = str(controller_model).strip().upper()

    if model == "LNU":
        if data.size < 8:
            raise ValueError(f"{path} is too short for an LNU controller file")
        dt, tau_u = float(data[0]), float(data[1])
        n_u, n_u1, n_y, n_e = (int(round(v)) for v in data[2:6])
        r_0_value = float(data[6])
        v = data[7:].copy()
        n_xi = 1 + n_y + n_e
        expected = n_xi
    elif model == "QNU":
        if data.size < 10:
            raise ValueError(f"{path} is too short for a QNU controller file")
        dt, tau_u = float(data[0]), float(data[1])
        n_u, n_u1, n_y, n_e = (int(round(v)) for v in data[2:6])
        n_xi, n_phi = int(round(data[6])), int(round(data[7]))
        r_0_value = float(data[8])
        v = data[9:].copy()
        expected_xi = 1 + n_y + n_e
        expected_phi = qnu_feature_count(expected_xi)
        if n_xi != expected_xi or n_phi != expected_phi:
            raise ValueError(
                f"{path} contains incompatible QNU dimensions: "
                f"n_xi={n_xi}, n_phi={n_phi}, expected {expected_xi}, {expected_phi}"
            )
        expected = n_phi
    else:
        raise ValueError("controller_model must be 'LNU' or 'QNU'")

    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError(f"Invalid controller sample period dt={dt!r} in {path}")
    if min(n_u, n_y, n_e) <= 0 or n_u1 < 0:
        raise ValueError(f"Invalid embedding dimensions in {path}")
    if v.size != expected:
        raise ValueError(
            f"{path} contains {v.size} controller weights; expected {expected}"
        )
    if not np.all(np.isfinite(v)) or not np.isfinite(r_0_value):
        raise ValueError(f"{path} contains non-finite controller parameters")

    return {
        "dt": dt,
        "tau_u": tau_u,
        "n_u": n_u,
        "n_u1": n_u1,
        "n_y": n_y,
        "n_e": n_e,
        "n_xi": n_xi,
        "r_0": r_0_value,
        "v": v,
        "model": model,
    }


def run_physical_test(
    honu_plant_model: str,
    controller_model: str,
    controller_file: str | Path,
    output_file: str | Path,
) -> Path:
    """Run module 04 and save the closed-loop physical-plant trajectory."""
    controller = load_controller(controller_file, controller_model)
    dt = controller["dt"]
    n_u = controller["n_u"]
    n_u1 = controller["n_u1"]
    n_y = controller["n_y"]
    n_e = controller["n_e"]
    n_xi = controller["n_xi"]
    v = controller["v"].copy()
    v_initial = v.copy()
    r_0_value = float(np.clip(controller["r_0"], r_0_min, r_0_max))

    # Module 04 is an adaptive validation, not a frozen-controller replay.
    # The physical ODE plant supplies the actual regulation error, while the
    # identified HONU plant supplies the local input-output sensitivities.
    surrogate = load_surrogate_plant(honu_plant_model)
    if abs(float(surrogate["dt"]) - dt) > 1e-12:
        raise ValueError(
            f"Controller dt={dt:g} differs from identified plant dt={surrogate['dt']:g}"
        )
    if (surrogate["n_u"], surrogate["n_u1"], surrogate["n_y"]) != (n_u, n_u1, n_y):
        raise ValueError(
            "Controller and identified HONU plant use incompatible embedding dimensions"
        )
    w = surrogate["w"]
    plant_model = surrogate["model"]

    if controller["model"] == "QNU":
        learning = str(ctrl_qnu_learning).strip().upper()
        mu_v_online = float(mu_v_qnu)
        mu_r0_online = float(mu_r_0_qnu)
        alpha_v_online = float(alpha_v_qnu)
        alpha_r0_online = float(alpha_r_0_qnu)
    else:
        learning = str(ctrl_learning).strip().upper()
        mu_v_online = float(mu_v)
        mu_r0_online = float(mu_r_0)
        alpha_v_online = float(alpha_v)
        alpha_r0_online = float(alpha_r_0)
    if learning not in ("GD", "NGD"):
        raise ValueError("Controller learning must be GD or NGD")
    if not (0.0 <= alpha_v_online <= 1.0 and 0.0 <= alpha_r0_online <= 1.0):
        raise ValueError("Controller smoothing factors must lie in [0, 1]")

    uy = np.loadtxt(uy_file, comments="#")
    if uy.ndim == 1:
        uy = uy.reshape(1, -1)
    if uy.shape[1] < 3:
        raise ValueError(f"{uy_file} must contain the common columns t, u, y")
    dataset_normalization = load_stats(simulated_normalization_file)
    normalization = load_artifact_stats(controller_file)
    assert_same_stats(dataset_normalization, normalization, "module 01 data versus trained controller")
    if normalization.get("model_name") and normalization["model_name"] != plant_model_name:
        raise ValueError(
            f"Normalization belongs to {normalization['model_name']}, but the selected model is {plant_model_name}. Run module 01 again."
        )
    u_data_physical = np.asarray(uy[:, 1], dtype=float)
    measured_y_physical = np.asarray(uy[:, 2], dtype=float)
    u_data = normalize_u(u_data_physical, normalization)
    measured_y = normalize_y(measured_y_physical, normalization)
    sample_count = max(2, int(round(reference_duration_sec / dt)) + 1)
    reference_plant_input = denormalize_u(np.resize(u_data, sample_count), normalization)

    d_physical = make_reference_signal(
        reference_type=reference_type,
        sample_count=sample_count,
        dt=dt,
        d_min=d_min,
        d_max=d_max,
        step_hold_sec=reference_step_hold_sec,
        seed=reference_seed,
        plant_input=reference_plant_input,
    )
    validate_reference_domain(d_physical, measured_y_physical, context="module 04")
    d = np.asarray(normalize_y(d_physical, normalization), dtype=float)
    effective_d_min = float(d_min)
    effective_d_max = float(d_max)
    measured_y_min, measured_y_max = finite_signal_range(
        measured_y, "normalized module-01 controlled output y_z"
    )
    # Module 03 evaluates the controller only on trajectories produced by the
    # identified plant, whose output is projected to this identification
    # domain.  A QNU controller must therefore be evaluated on the same domain
    # in module 04; otherwise a small ODE/model mismatch is squared by the QNU
    # basis and causes polynomial extrapolation.  The physical ODE output and
    # the physical command remain unrestricted.
    d_z_min, d_z_max = finite_signal_range(d, "normalized reference d_z")
    controller_e_min = measured_y_min - d_z_max
    controller_e_max = measured_y_max - d_z_min
    # The reference-model delay must be identical to the delay used during
    # controller training.  Module 03 stores that delay as n_u1 in the
    # controller file, so module 04 must not recompute it from a live GUI value.
    n_d1 = n_u1
    requested_n_d1 = builtins.max(0, int(round(tau_d / dt)))
    if requested_n_d1 != n_d1:
        print(
            f"NOTE: requested tau_d={tau_d:g} s gives {requested_n_d1} samples, "
            f"but the trained controller uses {n_d1} samples "
            f"({n_d1 * dt:g} s). Module 04 uses the trained value."
        )
    n_start = builtins.max(n_y, n_e, n_u1 + n_u, n_d1 + 1)
    if sample_count <= n_start:
        raise ValueError(
            f"The test record has {sample_count} samples, but at least {n_start + 1} are required"
        )

    t = np.arange(sample_count, dtype=float) * dt
    y = np.zeros(sample_count)
    y_ref = np.zeros(sample_count)
    e_ref = np.zeros(sample_count)
    u = np.zeros(sample_count)
    u_physical = np.zeros(sample_count)
    y_physical = np.zeros(sample_count)
    q = np.zeros(sample_count)
    r_0_history = np.full(sample_count, r_0_value, dtype=float)
    v_history = np.tile(np.asarray(v, dtype=float), (sample_count, 1))
    g_v_norm = np.zeros(sample_count, dtype=float)
    g_r_0 = np.zeros(sample_count, dtype=float)
    v0_integral_step = np.zeros(sample_count, dtype=float)
    r0_integral_step = np.zeros(sample_count, dtype=float)
    plant_dc_gain_sign = np.zeros(sample_count, dtype=float)
    rho_Av_history = np.full(sample_count, np.nan, dtype=float)
    abs_Ar0_history = np.full(sample_count, np.nan, dtype=float)
    rho_M_history = np.full(sample_count, np.nan, dtype=float)
    m_norm_history = np.full(sample_count, np.nan, dtype=float)

    # Surrogate-model sensitivity states. They estimate how the actual ODE
    # output changes with controller parameters; the measured/ODE error itself
    # is always used in the update.
    n_v = v.size
    dydv = np.zeros((sample_count, n_v), dtype=float)
    dudv = np.zeros((sample_count, n_v), dtype=float)
    dydr_0 = np.zeros(sample_count, dtype=float)
    dudr_0 = np.zeros(sample_count, dtype=float)
    dxidv = np.zeros((n_xi, n_v), dtype=float)
    dxidr_0 = np.zeros(n_xi, dtype=float)
    plant_x = np.zeros(n_y + n_u, dtype=float)
    plant_dxdv = np.zeros((n_y + n_u, n_v), dtype=float)
    plant_dxdr_0 = np.zeros(n_y + n_u, dtype=float)
    dv_smooth = np.zeros(n_v, dtype=float)
    dr_0_smooth = 0.0

    signal_meta = plant_signal_metadata(plant_model_name)
    diagnostic_keys = [item[0] for item in signal_meta["signals"]]
    diagnostics = {key: np.zeros(sample_count) for key in diagnostic_keys}

    xi = np.ones(n_xi)
    z_ref = 0.0
    chi = initial_state(plant_par)

    out0 = algebraic_outputs(chi, plant_par)
    y_physical[0] = controlled_output(chi, plant_par)
    y[0] = float(normalize_y(y_physical[0], normalization))
    for key in diagnostic_keys:
        diagnostics[key][0] = float(out0.get(key, np.nan))

    # Advance the physical plant from the first sample instead of leaving an
    # artificial zero-filled dead interval.  Until enough controller history is
    # available, hold u_z = 0, i.e. the normalization operating-point input.
    u_warmup_z = 0.0
    u_warmup_physical = float(denormalize_u(u_warmup_z, normalization))
    for k in range(1, n_start):
        u[k - 1] = u_warmup_z
        if preg_blackbox_enabled:
            chi, u_physical[k - 1] = simulate_sample_period_preg(
                chi, u_warmup_physical, dt, plant_par, solver_setup, r_preg
            )
        else:
            u_physical[k - 1] = float(u_warmup_physical)
            chi = simulate_sample_period_zoh(
                chi, u_physical[k - 1], dt, plant_par, solver_setup
            )
        out = algebraic_outputs(chi, plant_par)
        y_physical[k] = controlled_output(chi, plant_par)
        y[k] = float(normalize_y(y_physical[k], normalization))
        for key in diagnostic_keys:
            diagnostics[key][k] = float(out.get(key, np.nan))

    for k in range(n_start, sample_count):
        xi[0] = 1.0
        xi[1 : 1 + n_y] = y[k - n_y : k][::-1]
        xi[1 + n_y :] = e_ref[k - n_e : k][::-1]

        # Derivatives of the controller regressor. Since y_ref is independent
        # of controller parameters, d(e_ref)/d(theta) = d(y)/d(theta).
        dxidv[:, :] = 0.0
        dxidv[1 : 1 + n_y, :] = dydv[k - n_y : k, :][::-1]
        dxidv[1 + n_y :, :] = dydv[k - n_e : k, :][::-1]
        dxidr_0[:] = 0.0
        dxidr_0[1 : 1 + n_y] = dydr_0[k - n_y : k][::-1]
        dxidr_0[1 + n_y :] = dydr_0[k - n_e : k][::-1]

        if controller["model"] == "QNU":
            # Evaluate the polynomial controller in the same regressor domain
            # in which it was trained.  This is a projection of xi for QNU
            # evaluation only; y, e_ref, q and u are not saturated.
            xi_eval = xi.copy()
            xi_eval[1 : 1 + n_y] = np.clip(
                xi_eval[1 : 1 + n_y], measured_y_min, measured_y_max
            )
            xi_eval[1 + n_y :] = np.clip(
                xi_eval[1 + n_y :], controller_e_min, controller_e_max
            )
            xi_mask = np.ones(n_xi, dtype=float)
            xi_mask[1 : 1 + n_y] = (
                (xi[1 : 1 + n_y] > measured_y_min)
                & (xi[1 : 1 + n_y] < measured_y_max)
            ).astype(float)
            xi_mask[1 + n_y :] = (
                (xi[1 + n_y :] > controller_e_min)
                & (xi[1 + n_y :] < controller_e_max)
            ).astype(float)

            regressor, jac_controller = qnu_phi_and_jacobian(xi_eval)
            jac_controller = jac_controller * xi_mask[None, :]
            q[k - 1] = float(v @ regressor)
            dqdv = regressor + v @ jac_controller @ dxidv
            dqdr_0 = float(v @ jac_controller @ dxidr_0)
        else:
            regressor = xi
            q[k - 1] = float(v @ regressor)
            dqdv = regressor + v @ dxidv
            dqdr_0 = float(v @ dxidr_0)

        # No saturation of q or u in modules 03/04.
        u[k - 1] = float(r_0_value * (d[k - 1] - q[k - 1]))
        if not np.isfinite(q[k - 1]) or not np.isfinite(u[k - 1]):
            raise FloatingPointError(
                f"Non-finite controller output at sample {k}: "
                f"q={q[k - 1]!r}, u_z={u[k - 1]!r}."
            )
        dudv[k - 1, :] = -r_0_value * dqdv
        dudr_0[k - 1] = (d[k - 1] - q[k - 1]) - r_0_value * dqdr_0

        u_new_physical = float(denormalize_u(u[k - 1], normalization))
        if preg_blackbox_enabled:
            chi, u_physical[k - 1] = simulate_sample_period_preg(
                chi, u_new_physical, dt, plant_par, solver_setup, r_preg
            )
        else:
            u_physical[k - 1] = float(u_new_physical)
            chi = simulate_sample_period_zoh(
                chi, u_physical[k - 1], dt, plant_par, solver_setup
            )
        out = algebraic_outputs(chi, plant_par)
        y_physical[k] = controlled_output(chi, plant_par)
        y[k] = float(normalize_y(y_physical[k], normalization))
        for key in diagnostic_keys:
            diagnostics[key][k] = float(out.get(key, np.nan))

        z_ref, y_ref[k] = advance_reference_model(
            z_ref, y_ref[k - 1], d[k - n_d1 - 1],
            dt, dt_sim, Tau_1, Tau_2,
        )
        e_ref[k] = y[k] - y_ref[k]

        # Local sensitivity supplied by the identified HONU plant. The plant
        # regressor uses the actual ODE y history and the actual controller u
        # history, while its Jacobian propagates parameter sensitivities.
        plant_x[:n_y] = y[k - n_y : k][::-1]
        plant_x[n_y:] = u[k - n_u1 - n_u : k - n_u1][::-1]
        plant_dxdv[:n_y, :] = dydv[k - n_y : k, :][::-1]
        plant_dxdv[n_y:, :] = dudv[k - n_u1 - n_u : k - n_u1, :][::-1]
        plant_dxdr_0[:n_y] = dydr_0[k - n_y : k][::-1]
        plant_dxdr_0[n_y:] = dudr_0[k - n_u1 - n_u : k - n_u1][::-1]

        if plant_model == "QNU":
            plant_x_eval = plant_x.copy()
            plant_x_eval[:n_y] = np.clip(
                plant_x_eval[:n_y], measured_y_min, measured_y_max
            )
            # The surrogate Jacobian is projected only in the output-history
            # coordinates. The controller-generated input history remains
            # completely unrestricted, exactly as in module 03.
            plant_xi = np.concatenate(([1.0], plant_x_eval))
            _phi_p, jac_plant_xi = qnu_phi_and_jacobian(plant_xi)
            grad_x_y = w @ jac_plant_xi[:, 1:]
        else:
            grad_x_y = w[1:]

        sensitivity_limit = 1.0e6
        dydv[k, :] = np.clip(
            np.nan_to_num(grad_x_y @ plant_dxdv, nan=0.0, posinf=sensitivity_limit, neginf=-sensitivity_limit),
            -sensitivity_limit, sensitivity_limit,
        )
        dydr_0[k] = float(np.clip(
            np.nan_to_num(grad_x_y @ plant_dxdr_0, nan=0.0, posinf=sensitivity_limit, neginf=-sensitivity_limit),
            -sensitivity_limit, sensitivity_limit,
        ))
        # Full online MRAC adaptation. The regulation error is measured on the
        # physical ODE plant, while the identified HONU model supplies the
        # recursive sensitivities dy/dv and dy/dr_0. Thus every controller
        # weight, including the constant xi_0 channel, and r_0 continue learning.
        g_v = np.asarray(dydv[k, :], dtype=float)
        g_r0 = float(dydr_0[k])
        g_v_norm[k] = float(np.linalg.norm(g_v, 2))
        g_r_0[k] = g_r0

        # Module 04 uses only the selected GD/NGD rule. There is no separate
        # integral correction of the controller bias v_0 or feedforward gain r_0.
        # The bias remains fully adaptive through the ordinary gradient because
        # xi_0 = 1 is part of both the LNU and QNU controller regressors.
        if not (np.all(np.isfinite(g_v)) and np.isfinite(g_r0) and np.isfinite(e_ref[k])):
            raise FloatingPointError(
                f"Non-finite module-04 adaptation signal at sample {k}: "
                f"||g_v||={np.linalg.norm(g_v)!r}, g_r_0={g_r0!r}, e_ref={e_ref[k]!r}"
            )

        norm_g = float(np.linalg.norm(g_v, 2))
        abs_g_r0 = abs(g_r0)
        if learning == "NGD":
            # Stable evaluation of g/(eps + ||g||^2), avoiding an unnecessary
            # square of a large norm. This is algebraically identical to NGD.
            if norm_g > 0.0:
                normalized_g = (g_v / norm_g) / (norm_g + ctrl_eps / norm_g)
                eta_g2_v = mu_v_online * (norm_g / (norm_g + ctrl_eps / norm_g))
            else:
                normalized_g = np.zeros_like(g_v)
                eta_g2_v = 0.0
            dv = -mu_v_online * e_ref[k] * normalized_g

            if abs_g_r0 > 0.0:
                normalized_g_r0 = np.sign(g_r0) / (abs_g_r0 + ctrl_eps / abs_g_r0)
                eta_g2_r0 = mu_r0_online * (abs_g_r0 / (abs_g_r0 + ctrl_eps / abs_g_r0))
            else:
                normalized_g_r0 = 0.0
                eta_g2_r0 = 0.0
            dr0 = -mu_r0_online * e_ref[k] * normalized_g_r0
        else:
            dv = -mu_v_online * e_ref[k] * g_v
            dr0 = -mu_r0_online * e_ref[k] * g_r0
            eta_g2_v = mu_v_online * norm_g * norm_g
            eta_g2_r0 = mu_r0_online * abs_g_r0 * abs_g_r0

        # Local adaptation-map monitoring, consistent with module 03.
        # A_v = I - eta_v g_v g_v^T has one active eigenvalue
        # 1-eta_v||g_v||^2 and n_v-1 unit eigenvalues.
        active_eig_v = 1.0 - eta_g2_v
        rho_Av_history[k] = max(1.0, abs(active_eig_v)) if n_v > 1 else abs(active_eig_v)
        abs_Ar0_history[k] = abs(1.0 - eta_g2_r0)

        if not (np.all(np.isfinite(dv)) and np.isfinite(dr0)):
            raise FloatingPointError(
                f"Non-finite {learning} update at sample {k}: "
                f"||dv||={np.linalg.norm(dv)!r}, dr_0={dr0!r}"
            )

        # Retain zero-valued diagnostic columns for backward-compatible result
        # files and GUI readers. No integral adaptation is applied.
        v0_integral_step[k] = 0.0
        r0_integral_step[k] = 0.0
        plant_dc_gain_sign[k] = 0.0

        dv_smooth = alpha_v_online * dv + (1.0 - alpha_v_online) * dv_smooth
        dr_0_smooth = alpha_r0_online * dr0 + (1.0 - alpha_r0_online) * dr_0_smooth
        v = v + dv_smooth

        # Projection protects the online estimator from windup while keeping
        # every controller weight adaptive. It does not saturate q or u.
        trust_radius = 0.1 if controller["model"] == "QNU" else 20.0
        delta_v = v - v_initial
        delta_v_norm = float(np.linalg.norm(delta_v, 2))
        if delta_v_norm > trust_radius:
            v = v_initial + delta_v * (trust_radius / delta_v_norm)
        if controller["model"] == "QNU":
            v_norm = float(np.linalg.norm(v, 2))
            if v_norm > qnu_v_norm_max:
                v *= qnu_v_norm_max / v_norm
        r_0_value = float(np.clip(r_0_value + dr_0_smooth, r_0_min, r_0_max))

        # Local closed-loop companion metric rho(M(k)). The identified HONU
        # plant is frozen; the controller parameters are the newly adapted
        # values at this physical sample. The homogeneous test uses d=0 and
        # y_ref=0, hence e_ref=y.
        a_y = np.asarray(grad_x_y[:n_y], dtype=float)
        a_u = np.asarray(grad_x_y[n_y:n_y + n_u], dtype=float)
        if controller["model"] == "QNU":
            _phi_c_metric, J_c_metric = qnu_phi_and_jacobian(xi_eval)
            grad_q_metric = np.asarray(v @ J_c_metric, dtype=float)
            c_y = grad_q_metric[1:1 + n_y]
            c_e = grad_q_metric[1 + n_y:1 + n_y + n_y]
        else:
            c_y = np.asarray(v[1:1 + n_y], dtype=float)
            c_e = np.asarray(v[1 + n_y:1 + n_y + n_y], dtype=float)
        c_cl = c_y + c_e
        n_M = builtins.max(n_y, n_u1 + n_u + n_y - 1)
        m = np.zeros(n_M, dtype=float)
        m[:n_y] = a_y
        for j in range(n_u):
            for p in range(n_y):
                lag_index = n_u1 + (j + 1) + p
                if lag_index < n_M:
                    m[lag_index] -= r_0_value * a_u[j] * c_cl[p]
        M = np.zeros((n_M, n_M), dtype=float)
        M[0, :] = m
        if n_M > 1:
            M[1:, :-1] = np.eye(n_M - 1)
        if np.all(np.isfinite(M)):
            m_norm_history[k] = float(np.linalg.norm(m, 2))
            rho_M_history[k] = float(np.max(np.abs(np.linalg.eigvals(M))))

        v_history[k, :] = v
        r_0_history[k] = r_0_value


    rmse = float(np.sqrt(np.mean(e_ref[n_start:] ** 2)))
    actual_d_min = float(np.min(d_physical))
    actual_d_max = float(np.max(d_physical))
    actual_d_z_min = float(np.min(d))
    actual_d_z_max = float(np.max(d))
    print(
        f"reference d: type={reference_type}, requested_tau_d={tau_d:g} s, "
        f"effective_tau_d={n_d1 * dt:g} s, "
        f"requested=[{d_min:g}, {d_max:g}], "
        f"effective=[{effective_d_min:g}, {effective_d_max:g}], "
        f"training y_z=[{measured_y_min:g}, {measured_y_max:g}], "
        f"actual_physical=[{actual_d_min:g}, {actual_d_max:g}], "
        f"actual_z=[{actual_d_z_min:g}, {actual_d_z_max:g}], "
        f"duration={reference_duration_sec:g} s, hold={reference_step_hold_sec:g} s, seed={reference_seed}, "
        f"samples={sample_count}"
    )
    print(f"physical adaptive closed-loop rmse {rmse:.12g}")
    print(
        f"module 04 online adaptation: learning={learning}, "
        f"mu_v={mu_v_online:g}, mu_r_0={mu_r0_online:g}, integral_correction=disabled, "
        f"final_r_0={r_0_value:.12g}, final_v_norm={np.linalg.norm(v, 2):.12g}, final_v_0={v[0]:.12g}"
    )

    output_path = Path(output_file)
    d_plot = d_physical
    y_ref_plot = denormalize_y(y_ref, normalization)
    y_plot = y_physical
    e_ref_plot = denormalize_error(e_ref, normalization)
    q_plot = denormalize_y(q, normalization)
    core_columns = [
        "t", "d", "y_ref", "y", "regulation_deviation",
        "u_z", "q", "u_physical", "y_physical",
        "r_0", "g_v_norm", "g_r_0", "Rho_Av", "A_abs_r_0", "m_norm", "Rho_M",
        "dv0_integral", "dr0_integral", "plant_dc_gain_sign",
    ]
    weight_columns = [f"v_{i}" for i in range(n_v)]
    physical_columns = core_columns + weight_columns + diagnostic_keys
    physical_data = np.column_stack(
        [
            t, d_plot, y_ref_plot, y_plot, e_ref_plot,
            u, q_plot, u_physical, y_physical,
            r_0_history, g_v_norm, g_r_0, rho_Av_history, abs_Ar0_history, m_norm_history, rho_M_history,
            v0_integral_step, r0_integral_step, plant_dc_gain_sign, v_history,
        ]
        + [diagnostics[key] for key in diagnostic_keys]
    )
    metadata = (
        f"reference_type={reference_type}, "
        f"requested_d_min={d_min:g}, requested_d_max={d_max:g}, "
        f"effective_d_min={effective_d_min:g}, "
        f"effective_d_max={effective_d_max:g}, "
        f"training_y_z_min={measured_y_min:g}, "
        f"training_y_z_max={measured_y_max:g}, "
        f"actual_d_min={actual_d_min:g}, actual_d_max={actual_d_max:g}, "
        f"reference_duration_sec={reference_duration_sec:g}, step_hold_sec={reference_step_hold_sec:g}, "
        f"requested_tau_d={tau_d:g}, effective_tau_d={n_d1 * dt:g}, "
        f"reference_seed={reference_seed}, "
        f"preg_blackbox_enabled={preg_blackbox_enabled}, r_preg={r_preg:g}, "
        f"online_adaptation=True, adapted_parameters=all_v_and_r_0, sensitivity_plant={plant_model}, learning={learning}, "
        f"mu_v={mu_v_online:g}, mu_r_0={mu_r0_online:g}, integral_correction=disabled, "
        f"alpha_v={alpha_v_online:g}, alpha_r_0={alpha_r0_online:g}, "
        f"normalization=zscore, mu_u={normalization['mu_u']:.17g}, "
        f"scale_u={normalization['scale_u']:.17g}, "
        f"mu_y={normalization['mu_y']:.17g}, scale_y={normalization['scale_y']:.17g}"
    )
    np.savetxt(
        output_path,
        physical_data,
        header=metadata + "\n" + " ".join(physical_columns),
    )

    if os.environ.get("HONU_GUI_NO_MPL") != "1":
        fig, (ax_top, ax_bottom) = plt.subplots(
            2,
            1,
            figsize=(16, 10),
            sharex=True,
            gridspec_kw={"height_ratios": [2.0, 1.0]},
        )
        fig.suptitle(
            plant_display_name(plant_model_name) + "\n" +
            f"Module 04: adaptive physical ODE validation; controller initialized with "
            f"{honu_plant_model} HONU plant ({controller_plant_source}) + "
            f"{controller_model} controller; dt={dt:g} s, ODE dt_sim={dt_sim:g} s"
        )
        ax_top.plot(t, d_plot, color="black", label="d")
        ax_top.plot(t, y_ref_plot, color="magenta", label="y_ref")
        ax_top.plot(t, y_plot, color="green", label="y")
        ax_top.set_ylabel("d, y_ref, y")
        ax_top.grid(True)
        ax_top.legend(loc="best")

        # Show the actual physical input applied to the ODE plant in a
        # separate subplot below the response plot. With the optional internal
        # P-regulated black-box configuration this is the post-feedback input,
        # not merely the external controller command.
        ax_bottom.plot(
            t[:-1], u_physical[:-1], color="blue", linewidth=1.2, label="u"
        )
        ax_bottom.set_ylabel("u")
        ax_bottom.set_xlabel(f"physical plant time t [s], dt={dt:g} s")
        ax_bottom.grid(True)
        ax_bottom.legend(loc="best")

        fig.tight_layout()
        plt.show()

    return output_path
