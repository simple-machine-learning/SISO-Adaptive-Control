# -*- coding: utf-8 -*-
"""Uniform nearest-sample resampling for measured HONU MRAC datasets.

The HONU identification and controller code requires a strictly uniform sample
period. Raw measurement timestamps may contain small jitter, so this module
creates the exact target grid ``t[k] = k * dt_target`` and copies the value of
the nearest original measured sample onto every grid point.

No low-pass filter, anti-alias filter, smoothing, or interpolation is applied.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ResamplingInfo:
    method: str
    dt_original: float
    dt_target: float
    input_samples: int
    output_samples: int
    unique_source_samples: int
    repeated_source_samples: int
    max_source_time_error: float
    timestamp_jitter_peak: float

    def to_dict(self) -> dict:
        return asdict(self)


def _prepare_inputs(t, signals):
    t = np.asarray(t, dtype=float).ravel()
    x = np.asarray(signals, dtype=float)
    one_dimensional = x.ndim == 1
    if one_dimensional:
        x = x[:, None]
    if x.ndim != 2 or x.shape[0] != t.size:
        raise ValueError("signals must have one row per time sample")
    if t.size < 2:
        raise ValueError("At least two measured samples are required")

    finite_rows = np.isfinite(t) & np.all(np.isfinite(x), axis=1)
    t = t[finite_rows]
    x = x[finite_rows]
    if t.size < 2:
        raise ValueError("Too few finite samples remain after cleaning")

    order = np.argsort(t, kind="stable")
    t = t[order]
    x = x[order]
    keep = np.r_[True, np.diff(t) > 0.0]
    t = t[keep]
    x = x[keep]
    if t.size < 2:
        raise ValueError("Timestamps must contain at least two unique values")
    return t, x, one_dimensional


def _nearest_indices(t_source: np.ndarray, t_target: np.ndarray) -> np.ndarray:
    right = np.searchsorted(t_source, t_target, side="left")
    right = np.clip(right, 0, t_source.size - 1)
    left = np.maximum(right - 1, 0)
    choose_left = np.abs(t_target - t_source[left]) <= np.abs(t_source[right] - t_target)
    return np.where(choose_left, left, right)


def resample_uniform(t, signals, dt_target: float, *, method: str = "nearest"):
    """Copy nearest measured samples to an exact uniform target grid.

    Parameters
    ----------
    t:
        Source timestamps in seconds.
    signals:
        One vector or an ``(N, n_signals)`` matrix.
    dt_target:
        Requested final sample period in seconds.
    method:
        Must be ``"nearest"``. The argument is retained so GUI and CLI calls
        remain explicit. No filtering or interpolation is performed.

    Returns
    -------
    t_out, signals_out, info
        ``t_out`` starts at zero and equals ``arange(N) * dt_target``. Each
        output row is copied from the nearest original measured row.
    """
    t, x, one_dimensional = _prepare_inputs(t, signals)
    dt_target = float(dt_target)
    if not np.isfinite(dt_target) or dt_target <= 0.0:
        raise ValueError("dt_target must be a positive finite number")

    method = str(method).strip().lower()
    if method != "nearest":
        raise ValueError("method must be 'nearest'; this package does not filter or interpolate measured data")

    diffs = np.diff(t)
    dt_original = float(np.median(diffs))
    if not np.isfinite(dt_original) or dt_original <= 0.0:
        raise ValueError("Cannot determine a positive original sample period")

    t0 = float(t[0])
    duration = float(t[-1] - t0)
    output_count = int(np.floor(duration / dt_target)) + 1
    if output_count < 2:
        raise ValueError("Selected interval is shorter than one requested sample period")

    t_absolute = t0 + np.arange(output_count, dtype=float) * dt_target
    source_indices = _nearest_indices(t, t_absolute)
    x_out = x[source_indices].copy()
    t_out = np.arange(output_count, dtype=float) * dt_target

    ideal_source = t0 + np.arange(t.size, dtype=float) * dt_original
    jitter_peak = float(np.max(np.abs(t - ideal_source)))
    unique_count = int(np.unique(source_indices).size)
    max_time_error = float(np.max(np.abs(t[source_indices] - t_absolute)))
    info = ResamplingInfo(
        method="nearest_original_sample_exact_grid_no_filter",
        dt_original=dt_original,
        dt_target=dt_target,
        input_samples=int(t.size),
        output_samples=int(output_count),
        unique_source_samples=unique_count,
        repeated_source_samples=int(output_count - unique_count),
        max_source_time_error=max_time_error,
        timestamp_jitter_peak=jitter_peak,
    )
    if one_dimensional:
        x_out = x_out[:, 0]
    return t_out, x_out, info
