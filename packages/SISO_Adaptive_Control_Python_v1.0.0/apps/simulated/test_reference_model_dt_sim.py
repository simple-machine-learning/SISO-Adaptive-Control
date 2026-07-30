# -*- coding: utf-8 -*-
"""Regression checks for MRAC/MPC reference-model integration."""

from __future__ import annotations

import numpy as np

from reference_model_dt_sim import simulate_reference_model


def main() -> None:
    d = np.ones(40, dtype=float)
    y = simulate_reference_model(
        d, dt_control=0.5, dt_sim=0.01, tau_1=0.3, tau_2=0.3
    )
    if not np.all(np.isfinite(y)):
        raise AssertionError("Reference-model output contains non-finite values")
    if np.any(np.diff(y) < -1.0e-12):
        raise AssertionError("Reference-model step response is not monotone")
    if np.min(y) < -1.0e-12 or np.max(y) > 1.0 + 1.0e-12:
        raise AssertionError("Reference-model step response left the input bounds")

    coarse = simulate_reference_model(
        d, dt_control=0.5, dt_sim=0.02, tau_1=0.3, tau_2=0.3
    )
    fine = simulate_reference_model(
        d, dt_control=0.5, dt_sim=0.005, tau_1=0.3, tau_2=0.3
    )
    if np.max(np.abs(coarse - fine)) > 0.02:
        raise AssertionError("Reference model does not converge with dt_sim refinement")

    print("Reference model dt_sim integration: PASS")
    print(f"dt_control=0.5 s, dt_sim=0.01 s, tau1=tau2=0.3 s")
    print(f"first output={y[0]:.9g}, final output={y[-1]:.9g}")


if __name__ == "__main__":
    main()
