"""Optional C++ acceleration for recursive HONU MPC prediction."""
from __future__ import annotations

import os
import numpy as np

try:
    from . import _honu_mpc_native as _native
except ImportError:
    try:
        import _honu_mpc_native as _native
    except ImportError:
        _native = None

NATIVE_AVAILABLE = _native is not None


def native_enabled() -> bool:
    value = os.environ.get("SISO_HONU_NATIVE", "1").strip().lower()
    return NATIVE_AVAILABLE and value not in {"0", "false", "no", "off"}


def predict_sequence_and_jacobian(candidate_u, y_hist, u_hist, local, compute_jacobian=True):
    if not native_enabled():
        raise RuntimeError("Native HONU kernel is not available or is disabled")
    return _native.predict_sequence_and_jacobian(
        np.ascontiguousarray(candidate_u, dtype=np.float64),
        np.ascontiguousarray(y_hist, dtype=np.float64),
        np.ascontiguousarray(u_hist, dtype=np.float64),
        np.ascontiguousarray(local["c"], dtype=np.float64),
        np.ascontiguousarray(local["pca"]["P"], dtype=np.float64),
        int(local["ny"]),
        int(local["nu"]),
        int(local.get("delay_u", 0)),
        int(str(local["model"]).upper() == "QNU"),
        bool(compute_jacobian),
    )


_backend_reported = False

def optimize_u(ref, y_hist, u_hist, local, warm, cfg):
    global _backend_reported
    if not native_enabled():
        raise RuntimeError("Native HONU optimizer is not available or is disabled")
    result = _native.optimize_u(
        np.ascontiguousarray(ref, dtype=np.float64),
        np.ascontiguousarray(y_hist, dtype=np.float64),
        np.ascontiguousarray(u_hist, dtype=np.float64),
        np.ascontiguousarray(local["c"], dtype=np.float64),
        np.ascontiguousarray(local["pca"]["P"], dtype=np.float64),
        int(local["ny"]), int(local["nu"]), int(local.get("delay_u", 0)),
        int(str(local["model"]).upper() == "QNU"),
        None if warm is None else np.ascontiguousarray(warm, dtype=np.float64),
        float(cfg["q_track"]), float(cfg["r_du"]), float(cfg["r_ddu"]), float(cfg["r_u"]),
        float(cfg.get("u_min", -1.0)), float(cfg.get("u_max", 1.0)), int(cfg["opt_iter"]),
    )
    if not _backend_reported:
        print("MPC backend: C++ accelerated (full optimizer)")
        _backend_reported = True
    return result
