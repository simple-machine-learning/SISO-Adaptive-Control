"""Numerical and speed check for the native nonlinear microgrid ODE kernel."""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "common"), str(ROOT / "apps" / "simulated")]
import shared_plant_model as plant

par = plant.default_params("microgrid_frequency_bess_nonlinear")
solver = SimpleNamespace(method="Radau", rtol=1e-8, atol=1e-10, dt_sim=0.002, max_step_factor=0.1)
x0 = plant.initial_state(par)
inputs = 1.2 * np.sin(np.arange(500, dtype=float) * 0.03)

def run(native: bool, preg: bool):
    os.environ["SISO_ODE_NATIVE"] = "1" if native else "0"
    x = x0.copy()
    trajectory = np.empty((len(inputs), len(x)), dtype=float)
    start = time.perf_counter()
    for k, u in enumerate(inputs):
        if preg:
            x, _ = plant.simulate_sample_period_preg(x, float(u), 0.02, par, solver, 1.0)
        else:
            x = plant.simulate_sample_period_zoh(x, float(u), 0.02, par, solver)
        trajectory[k] = x
    return trajectory, time.perf_counter() - start

for preg in (False, True):
    reference, t_python = run(False, preg)
    accelerated, t_native = run(True, preg)
    max_error = float(np.max(np.abs(reference - accelerated)))
    print(f"PREG={preg}: Radau={t_python:.6f} s, C++={t_native:.6f} s, speedup={t_python/t_native:.1f}x, max error={max_error:.3e}")
    if max_error > 2.0e-6:
        raise SystemExit("Native ODE trajectory differs too much from Radau reference")
print("Physical ODE native test: PASS")
