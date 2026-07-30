from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "common"), str(ROOT / "apps" / "simulated")]
import HONU_MPC_runner as runner  # noqa: E402


def case(model: str, horizon: int = 30):
    rng = np.random.default_rng(42 if model == "LNU" else 43)
    ny = nu = 3
    P = np.eye(ny + nu)
    z = P.shape[1]
    n_c = z + 1 if model == "LNU" else (z + 1) * (z + 2) // 2
    c = rng.normal(scale=0.02, size=n_c)
    c[1] = 0.35
    local = {"c": c, "pca": {"P": P}, "ny": ny, "nu": nu, "delay_u": 1, "model": model}
    ref = rng.normal(scale=0.3, size=horizon)
    y_hist = rng.normal(scale=0.1, size=100)
    u_hist = rng.normal(scale=0.1, size=100)
    warm = rng.normal(scale=0.1, size=horizon)
    cfg = {"q_track": 1.0, "r_du": 0.1, "r_ddu": 0.02, "r_u": 0.01,
           "u_min": -1.0, "u_max": 1.0, "opt_iter": 10}
    return ref, y_hist, u_hist, local, warm, cfg


def run(model: str):
    args = case(model)
    os.environ["SISO_HONU_NATIVE"] = "0"
    py = runner.optimize_u(*args)
    os.environ["SISO_HONU_NATIVE"] = "1"
    native = runner.optimize_u(*args)
    np.testing.assert_allclose(native[0], py[0], rtol=2e-6, atol=2e-7)
    np.testing.assert_allclose(native[2], py[2], rtol=1e-10, atol=1e-12)

    timings = {}
    for flag, name, repeats in (("0", "Python", 20), ("1", "C++", 200)):
        os.environ["SISO_HONU_NATIVE"] = flag
        for _ in range(3):
            runner.optimize_u(*args)
        start = time.perf_counter()
        for _ in range(repeats):
            runner.optimize_u(*args)
        timings[name] = (time.perf_counter() - start) / repeats
    print(f"{model}: Python={timings['Python']*1e3:.3f} ms, C++={timings['C++']*1e3:.3f} ms, speedup={timings['Python']/timings['C++']:.1f}x")


if __name__ == "__main__":
    run("LNU")
    run("QNU")
