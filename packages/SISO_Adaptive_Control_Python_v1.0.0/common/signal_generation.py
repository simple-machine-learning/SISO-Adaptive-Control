# -*- coding: utf-8 -*-
"""Common deterministic generators for sampled excitation and reference signals."""
from __future__ import annotations
import numpy as np

ALIASES = {
    "steps": "alternating_steps",
    "alternating": "alternating_steps",
    "alternating_steps": "alternating_steps",
    "random": "random_steps",
    "random_steps": "random_steps",
}

def normalize_step_mode(mode: str) -> str:
    key = str(mode).strip().lower()
    if key not in ALIASES:
        raise ValueError("step mode must be 'alternating_steps' or 'random_steps'")
    return ALIASES[key]

def block_step_signal(sample_count: int, dt: float, low: float, high: float,
                      hold_sec: float, mode: str, seed: int, initial: float = 0.0) -> np.ndarray:
    n = int(sample_count)
    dt = float(dt); low = float(low); high = float(high); hold_sec = float(hold_sec)
    if n <= 0 or not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("sample_count and dt must be positive")
    if not np.isfinite(low) or not np.isfinite(high) or low >= high:
        raise ValueError("low and high must be finite and satisfy low < high")
    if not np.isfinite(hold_sec) or hold_sec <= 0.0:
        raise ValueError("hold_sec must be positive")
    mode = normalize_step_mode(mode)
    hold_samples = max(1, int(round(hold_sec / dt)))
    block_index = np.arange(n, dtype=np.int64) // hold_samples
    block_count = int(block_index[-1]) + 1
    levels = np.empty(block_count, dtype=float)
    levels[0] = float(np.clip(initial, low, high))
    if block_count > 1:
        if mode == "alternating_steps":
            levels[1:] = np.where(np.arange(1, block_count) % 2 == 1, high, low)
        else:
            rng = np.random.default_rng(int(seed))
            levels[1:] = rng.uniform(low, high, size=block_count - 1)
    return levels[block_index]
