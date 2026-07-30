# -*- coding: utf-8 -*-
"""Desired-reference helpers for module-04 physical ODE tests.

The controlled output in this package is ``y2``. Module 04 constrains every
physical-test reference trajectory to the range already covered by the measured
``y2`` record from module 01. A narrower range can still be set with ``d_min``
and ``d_max``; the measured range is the hard outer envelope. Modules 03 and 04 both use this helper so the selected reference mode is identical in training and testing.
"""

from __future__ import annotations

import numpy as np

from signal_generation import block_step_signal


_REFERENCE_ALIASES = {
    "steps": "alternating_steps",  # backward compatibility with v08/v09
    "alternating": "alternating_steps",
    "alternating_steps": "alternating_steps",
    "random": "random_steps",
    "random_steps": "random_steps",
    "plant_input": "plant_input",
}


def normalize_reference_type(reference_type: str) -> str:
    """Return a canonical reference type or raise a clear configuration error."""
    mode = str(reference_type).strip().lower()
    try:
        return _REFERENCE_ALIASES[mode]
    except KeyError as exc:
        allowed = "alternating_steps, random_steps, plant_input"
        raise ValueError(f"reference_type must be one of: {allowed}") from exc


def finite_signal_range(values, signal_name: str = "signal") -> tuple[float, float]:
    """Return the finite minimum and maximum of a sampled signal."""
    data = np.asarray(values, dtype=float).reshape(-1)
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise ValueError(f"{signal_name} contains no finite samples")

    value_min = float(np.min(finite))
    value_max = float(np.max(finite))
    if not value_min < value_max:
        raise ValueError(
            f"{signal_name} has zero range ({value_min:.12g}). Generate a "
            "non-constant plant record in module 01 first."
        )
    return value_min, value_max


def effective_reference_bounds(
    reference_type: str,
    requested_d_min: float,
    requested_d_max: float,
    measured_output,
) -> tuple[float, float, float, float]:
    """Validate and return the user-requested reference interval unchanged.

    The measured module-01 output range is returned only as diagnostic metadata;
    it is not used as a hard clipping envelope. This permits deliberate
    extrapolation tests outside the identification trajectory.
    """
    normalize_reference_type(reference_type)
    requested_min = float(requested_d_min)
    requested_max = float(requested_d_max)
    if (
        not np.isfinite(requested_min)
        or not np.isfinite(requested_max)
        or requested_min >= requested_max
    ):
        raise ValueError("d_min and d_max must be finite and satisfy d_min < d_max")
    measured_min, measured_max = finite_signal_range(
        measured_output, "originally measured controlled output y2"
    )
    return requested_min, requested_max, float(measured_min), float(measured_max)

def _validate_step_parameters(d_min: float, d_max: float, step_hold_sec: float) -> None:
    if not np.isfinite(d_min) or not np.isfinite(d_max) or d_min >= d_max:
        raise ValueError("d_min and d_max must be finite and satisfy d_min < d_max")
    if not np.isfinite(step_hold_sec) or step_hold_sec <= 0.0:
        raise ValueError("reference step hold time must be positive")


def _initial_level(d_min: float, d_max: float) -> float:
    """Use zero when admissible, otherwise use the centre of the interval."""
    if d_min <= 0.0 <= d_max:
        return 0.0
    return 0.5 * (float(d_min) + float(d_max))


def make_reference_signal(
    reference_type: str,
    sample_count: int,
    dt: float,
    d_min: float,
    d_max: float,
    step_hold_sec: float,
    seed: int,
    plant_input=None,
):
    """Build the desired signal ``d``.

    ``alternating_steps`` alternates between the interval limits after one
    initial hold block. ``random_steps`` draws one uniformly distributed level
    per fixed-duration block. ``plant_input`` copies the module-01 excitation.
    """
    n = int(sample_count)
    if n <= 0:
        raise ValueError("sample_count must be positive")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be a positive finite number")

    mode = normalize_reference_type(reference_type)
    if mode == "plant_input":
        if plant_input is None:
            raise ValueError("plant_input is required for reference_type='plant_input'")
        d = np.asarray(plant_input, dtype=float).reshape(-1)
        if d.size != n:
            raise ValueError(f"plant_input has {d.size} samples; expected {n}")
        if not np.all(np.isfinite(d)):
            raise ValueError("plant_input contains non-finite values")
        return d.copy()

    _validate_step_parameters(float(d_min), float(d_max), float(step_hold_sec))

    if mode == "alternating_steps":
        # Generate d directly from sign(sin) and map the sign only to the two
        # configured endpoint values.  Sampling at block centres prevents
        # sin(.) == 0 at switching instants, so no zero-valued or one-sample
        # intermediate level can enter controller training or ODE validation.
        # One sign half-wave lasts exactly hold_samples samples.
        hold_samples = max(1, int(round(float(step_hold_sec) / float(dt))))
        sample_index = np.arange(n, dtype=float)
        phase = np.pi * (sample_index + 0.5) / float(hold_samples)
        sign_wave = np.sign(np.sin(phase))
        return np.where(sign_wave >= 0.0, float(d_max), float(d_min))

    # Random steps retain one constant random value per requested hold block.
    return block_step_signal(
        sample_count=n,
        dt=float(dt),
        low=float(d_min),
        high=float(d_max),
        hold_sec=float(step_hold_sec),
        mode=mode,
        seed=int(seed),
        initial=_initial_level(float(d_min), float(d_max)),
    )


def make_bounded_reference_signal(
    reference_type: str,
    sample_count: int,
    dt: float,
    d_min: float,
    d_max: float,
    step_hold_sec: float,
    seed: int,
    measured_y,
    plant_input=None,
):
    """Build ``d`` using the requested interval without measured-range clipping.

    Returns
    -------
    d, effective_d_min, effective_d_max, measured_y_min, measured_y_max
    """
    (
        effective_min,
        effective_max,
        measured_y_min,
        measured_y_max,
    ) = effective_reference_bounds(
        reference_type=reference_type,
        requested_d_min=d_min,
        requested_d_max=d_max,
        measured_output=measured_y,
    )

    bounded_plant_input = plant_input

    d = make_reference_signal(
        reference_type=reference_type,
        sample_count=sample_count,
        dt=dt,
        d_min=effective_min,
        d_max=effective_max,
        step_hold_sec=step_hold_sec,
        seed=seed,
        plant_input=bounded_plant_input,
    )
    d = np.asarray(d, dtype=float)

    return (
        d,
        effective_min,
        effective_max,
        measured_y_min,
        measured_y_max,
    )


def validate_reference_domain(d_physical, measured_y_physical, context="reference"):
    """Report reference extrapolation without blocking modules 03 or 04."""
    d = np.asarray(d_physical, dtype=float).reshape(-1)
    y = np.asarray(measured_y_physical, dtype=float).reshape(-1)
    d = d[np.isfinite(d)]
    y = y[np.isfinite(y)]
    if d.size == 0 or y.size == 0:
        print(f"WARNING: {context}: reference or module-01 output contains no finite values", flush=True)
        return None
    d_lo, d_hi = float(np.min(d)), float(np.max(d))
    y_lo, y_hi = float(np.min(y)), float(np.max(y))
    span = max(y_hi - y_lo, 1.0e-12)
    tol = 0.02 * span
    outside = d_lo < y_lo - tol or d_hi > y_hi + tol
    if outside:
        print(
            f"WARNING: {context}: physical reference [{d_lo:.6g}, {d_hi:.6g}] lies outside "
            f"the module-01 output domain [{y_lo:.6g}, {y_hi:.6g}]. "
            "HONU extrapolation is allowed; controller-generated u remains unrestricted.",
            flush=True,
        )
    return d_lo, d_hi, y_lo, y_hi
