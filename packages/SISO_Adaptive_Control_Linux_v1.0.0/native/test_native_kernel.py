from __future__ import annotations

import os
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "common"), str(ROOT / "apps" / "simulated")]
import HONU_MPC_runner as runner


def make_local(model: str, rng: np.random.Generator):
    ny, nu, components = 4, 3, 5
    P = rng.normal(size=(ny + nu, components)) * 0.2
    n_aug = components + 1
    n_theta = n_aug if model == "LNU" else n_aug * (n_aug + 1) // 2
    c = rng.normal(size=n_theta) * (0.08 if model == "LNU" else 0.025)
    return {"model": model, "c": c, "ny": ny, "nu": nu, "delay_u": 2, "pca": {"P": P}}


def run_once(model: str):
    rng = np.random.default_rng(42)
    local = make_local(model, rng)
    candidate = rng.normal(size=30) * 0.1
    y_hist = rng.normal(size=100) * 0.05
    u_hist = rng.normal(size=100) * 0.1

    os.environ["SISO_HONU_NATIVE"] = "0"
    y_py, j_py = runner.predict_sequence_and_jacobian(candidate, y_hist, u_hist, local, True)
    os.environ["SISO_HONU_NATIVE"] = "1"
    y_cpp, j_cpp = runner.predict_sequence_and_jacobian(candidate, y_hist, u_hist, local, True)

    np.testing.assert_allclose(y_cpp, y_py, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(j_cpp, j_py, rtol=2e-12, atol=2e-12)

    repeats = 1500
    os.environ["SISO_HONU_NATIVE"] = "0"
    t0 = perf_counter()
    for _ in range(repeats):
        runner.predict_sequence_and_jacobian(candidate, y_hist, u_hist, local, True)
    t_py = perf_counter() - t0

    os.environ["SISO_HONU_NATIVE"] = "1"
    t0 = perf_counter()
    for _ in range(repeats):
        runner.predict_sequence_and_jacobian(candidate, y_hist, u_hist, local, True)
    t_cpp = perf_counter() - t0
    print(f"{model}: Python={1e6*t_py/repeats:.2f} us, C++={1e6*t_cpp/repeats:.2f} us, speedup={t_py/t_cpp:.2f}x")


if __name__ == "__main__":
    run_once("LNU")
    run_once("QNU")
