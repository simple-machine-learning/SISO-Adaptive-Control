# -*- coding: utf-8 -*-
"""Smoke test for the recursive rollout-trained HONU predictor."""
from __future__ import annotations

import numpy as np

from HONU_MPC_runner import fit_selected_model, initialise_fixed_pca, predict_sequence


def run_case(model: str) -> None:
    n = 180
    u = np.sin(np.arange(n) * 0.11)
    y = np.zeros(n + 1)
    for k in range(n):
        y[k + 1] = 0.76 * y[k] + 0.20 * u[k] + 0.025 * y[k] * u[k]

    cfg = {
        "honu": model,
        "n_y": 2,
        "n_u": 2,
        "horizon": 6,
        "dt_control": 0.1,
        "tau_u": 0.0,
        "prediction_mode": "recursive_rollout",
        "plant_learning": "ridge",
        "lambda": 0.05,
        "pca_selection_mode": "rank",
        "pca_retained_variability": 0.999,
        "rollout_max_windows": 60,
        "rollout_iterations": 8,
    }
    pca = initialise_fixed_pca(y, u, cfg)
    local, theta, _, rho, rmse, weights, _ = fit_selected_model(y, u, cfg, pca, True)
    prediction = predict_sequence(np.zeros(cfg["horizon"]), y[:80], u[:79], local)
    assert local["prediction_mode"] == "recursive_rollout"
    assert theta.ndim == 1 and np.all(np.isfinite(theta))
    assert prediction.shape == (cfg["horizon"],) and np.all(np.isfinite(prediction))
    assert rmse.shape == (2,) and weights.shape[0] == 2
    assert np.isfinite(rho)
    print(f"{model}: theta={theta.size}, RMSE initial/final={rmse[0]:.6g}/{rmse[1]:.6g}, rho={rho:.6g}")


if __name__ == "__main__":
    run_case("LNU")
    run_case("QNU")
    print("recursive rollout training: OK")
