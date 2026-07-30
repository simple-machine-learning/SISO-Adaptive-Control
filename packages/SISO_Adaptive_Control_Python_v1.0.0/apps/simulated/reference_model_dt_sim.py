# -*- coding: utf-8 -*-
"""Reference-model integration on the internal simulation step ``dt_sim``."""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def advance_reference_model(
    z_1: float,
    y_ref: float,
    reference: float,
    dt_control: float,
    dt_sim: float,
    tau_1: float,
    tau_2: float,
) -> Tuple[float, float]:
    """Advance the cascaded first-order reference model by one control period.

    The controller/MPC remains sampled at ``dt_control``.  The reference model
    is advanced internally using substeps no larger than ``dt_sim``.  Each
    first-order substep uses its exact zero-order-hold update, eliminating the
    explicit-Euler oscillation that occurs when ``dt_control > tau``.
    """
    dt_control = float(dt_control)
    dt_sim = float(dt_sim)
    tau_1 = float(tau_1)
    tau_2 = float(tau_2)
    if not math.isfinite(dt_control) or dt_control <= 0.0:
        raise ValueError("dt_control must be positive and finite")
    if not math.isfinite(dt_sim) or dt_sim <= 0.0:
        raise ValueError("dt_sim must be positive and finite")
    if not math.isfinite(tau_1) or tau_1 <= 0.0:
        raise ValueError("tau_1 must be positive and finite")
    if not math.isfinite(tau_2) or tau_2 <= 0.0:
        raise ValueError("tau_2 must be positive and finite")

    n_sub = max(1, int(math.ceil(dt_control / dt_sim)))
    h = dt_control / n_sub
    a_1 = math.exp(-h / tau_1)
    a_2 = math.exp(-h / tau_2)
    z = float(z_1)
    y = float(y_ref)
    d = float(reference)
    for _ in range(n_sub):
        z = a_1 * z + (1.0 - a_1) * d
        y = a_2 * y + (1.0 - a_2) * z
    return z, y


def simulate_reference_model(
    reference: np.ndarray,
    dt_control: float,
    dt_sim: float,
    tau_1: float,
    tau_2: float,
    delay_samples: int = 0,
) -> np.ndarray:
    """Return the sampled reference-model output for a complete sequence."""
    d = np.asarray(reference, dtype=float).reshape(-1)
    output = np.zeros(d.size, dtype=float)
    z_1 = 0.0
    y_ref = 0.0
    delay_samples = max(0, int(delay_samples))
    for k in range(d.size):
        d_delayed = d[k - delay_samples] if k >= delay_samples else 0.0
        z_1, y_ref = advance_reference_model(
            z_1, y_ref, d_delayed, dt_control, dt_sim, tau_1, tau_2
        )
        output[k] = y_ref
    return output
