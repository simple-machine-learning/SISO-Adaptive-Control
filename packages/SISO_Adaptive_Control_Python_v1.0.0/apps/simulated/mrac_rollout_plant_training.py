"""Optional recurrent rollout refinement for MRAC plant HONU models.

The initial one-step model is supplied by the existing Ridge, GD/NGD, or LM
identifier.  When enabled, its weights are refined on overlapping free-running
rollouts.  Every rollout starts from measured y/u history; predicted y values
are fed back only inside that rollout.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from honu_basis import qnu_features_and_jacobian


def _feature_and_grad_x(x: np.ndarray, model: str):
    x = np.asarray(x, dtype=float)
    if str(model).upper() == "LNU":
        phi = np.r_[1.0, x]
        # d phi / d x, shape feature x base
        J = np.zeros((phi.size, x.size), dtype=float)
        J[1:, :] = np.eye(x.size)
        return phi, J
    xa = np.r_[1.0, x]
    phi, J_aug = qnu_features_and_jacobian(xa)
    return np.asarray(phi, float), np.asarray(J_aug[:, 1:], float)


def _valid_starts(n: int, ny: int, nu: int, delay: int, horizon: int, max_windows: int):
    first = max(ny, delay + nu)
    last = n - horizon
    if last <= first:
        raise ValueError("Dataset is too short for MRAC rollout plant training")
    starts = np.arange(first, last, dtype=int)
    if max_windows > 0 and starts.size > max_windows:
        # Deterministic coverage of the complete identification record.
        idx = np.linspace(0, starts.size - 1, max_windows).round().astype(int)
        starts = starts[np.unique(idx)]
    return starts


def _rollout(theta, y, u, start, ny, nu, delay, horizon, model):
    y_seq = list(np.asarray(y[start-ny:start], float))
    # Keep chronological u values up to start-1.  Delay is handled by indexing.
    u_seq = list(np.asarray(u[:start], float))
    pred = np.empty(horizon, dtype=float)
    for j in range(horizon):
        k = start + j
        y_hist = [y_seq[-1-i] for i in range(ny)]
        u_hist = []
        for i in range(nu):
            ui = k - 1 - delay - i
            u_hist.append(float(u[ui]) if ui >= 0 else 0.0)
        x = np.asarray(y_hist + u_hist, dtype=float)
        phi, _ = _feature_and_grad_x(x, model)
        value = float(theta @ phi)
        if not np.isfinite(value) or abs(value) > 1.0e8:
            value = np.sign(value) * 1.0e8 if np.isfinite(value) else 1.0e8
        pred[j] = value
        y_seq.append(value)
    return pred


def rollout_rmse(theta, y, u, *, model, ny, nu, delay, horizon, max_windows=300, discount=1.0):
    y = np.asarray(y, float); u = np.asarray(u, float)
    starts = _valid_starts(y.size, ny, nu, delay, horizon, max_windows)
    weights = np.sqrt(np.power(float(discount), np.arange(horizon, dtype=float)))
    errors = []
    for k in starts:
        pred = _rollout(theta, y, u, int(k), ny, nu, delay, horizon, model)
        errors.append(weights * (pred - y[k:k+horizon]))
    e = np.concatenate(errors)
    return float(np.sqrt(np.mean(e * e)))


def refine_plant_weights(theta0, y, u, *, model, ny, nu, delay, enabled=False,
                         horizon=10, iterations=20, max_windows=300,
                         discount=1.0, ridge=0.0):
    theta0 = np.asarray(theta0, dtype=float).reshape(-1)
    if not enabled or int(horizon) <= 1 or int(iterations) <= 0:
        return theta0, {"enabled": False, "rmse_before": np.nan, "rmse_after": np.nan}
    y = np.asarray(y, float); u = np.asarray(u, float)
    horizon = int(horizon); max_windows = int(max_windows)
    starts = _valid_starts(y.size, int(ny), int(nu), int(delay), horizon, max_windows)
    weights = np.sqrt(np.power(float(discount), np.arange(horizon, dtype=float)))
    ridge_sqrt = np.sqrt(max(0.0, float(ridge)))

    def residual(theta):
        blocks = []
        for k in starts:
            pred = _rollout(theta, y, u, int(k), int(ny), int(nu), int(delay), horizon, model)
            blocks.append(weights * (pred - y[k:k+horizon]))
        if ridge_sqrt > 0.0:
            blocks.append(ridge_sqrt * theta)
        out = np.concatenate(blocks)
        return np.nan_to_num(out, nan=1.0e8, posinf=1.0e8, neginf=-1.0e8)

    before = rollout_rmse(theta0, y, u, model=model, ny=int(ny), nu=int(nu),
                          delay=int(delay), horizon=horizon,
                          max_windows=max_windows, discount=float(discount))
    result = least_squares(
        residual, theta0, method="trf", jac="2-point",
        max_nfev=int(iterations), x_scale="jac", loss="linear",
    )
    theta = np.asarray(result.x, float)
    after = rollout_rmse(theta, y, u, model=model, ny=int(ny), nu=int(nu),
                         delay=int(delay), horizon=horizon,
                         max_windows=max_windows, discount=float(discount))
    print(
        f"MRAC plant HONU training: recurrent rollout, model={str(model).upper()}, "
        f"horizon={horizon}, windows={starts.size}, RMSE {before:.9g} -> {after:.9g}, "
        f"nfev={result.nfev}, success={result.success}"
    )
    return theta, {
        "enabled": True, "rmse_before": before, "rmse_after": after,
        "horizon": horizon, "windows": int(starts.size),
        "nfev": int(result.nfev), "success": bool(result.success),
    }
