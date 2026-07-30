"""C++-compiled ODE integration and physical model backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np

try:
    from .numba_ode import available_for as numba_available_for, simulate_interval as numba_simulate_interval
except ImportError:
    numba_available_for = None
    numba_simulate_interval = None

_NATIVE_IMPORT_ERROR = None
try:
    from . import _physical_ode_native as _native
except (ImportError, OSError) as exc:
    _native = None
    _NATIVE_IMPORT_ERROR = exc

NATIVE_AVAILABLE = _native is not None and hasattr(_native, "simulate_interval")
_reported_models: set[str] = set()
_numba_status: dict[str, tuple[bool, str]] = {}


def native_import_error() -> str:
    if _NATIVE_IMPORT_ERROR is None:
        return ""
    return f"{type(_NATIVE_IMPORT_ERROR).__name__}: {_NATIVE_IMPORT_ERROR}"


def native_enabled() -> bool:
    value = os.environ.get("SISO_ODE_NATIVE", "1").strip().lower()
    return NATIVE_AVAILABLE and value not in {"0", "false", "no", "off"}


def strict_native() -> bool:
    value = os.environ.get("SISO_ODE_NATIVE_STRICT", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def model_is_compiled(model_module) -> bool:
    path = str(getattr(model_module, "__file__", ""))
    return any(path.endswith(suffix) for suffix in (".so", ".pyd", ".dll", ".dylib"))


def simulate_interval(state, u, dt, dt_internal, model_module, par,
                      preg=False, r_preg=1.0, output_function=None):
    if not native_enabled():
        raise RuntimeError("C++ physical ODE backend is unavailable or disabled")
    model_name = str(getattr(par, "plant_model_name", model_module.__name__))
    if not model_is_compiled(model_module):
        raise RuntimeError(
            f"Plant model '{model_name}' is not loaded from a compiled C++ extension. "
            "Run ./build_native_linux.sh."
        )
    # Numba is used for ZOH intervals when the original model source can be
    # compiled in nopython mode. P-feedback remains in the compiled Cython
    # integrator because its controlled-output callback is model-specific.
    if not preg and numba_available_for is not None and numba_simulate_interval is not None:
        status = _numba_status.get(model_name)
        if status is None:
            status = numba_available_for(model_name, par, np.asarray(state, dtype=np.float64))
            _numba_status[model_name] = status
        if status[0]:
            x_next = numba_simulate_interval(state, u, dt, dt_internal, model_name, par)
            if model_name not in _reported_models:
                print(f"ODE backend: Numba nopython RK4 + generated typed model ({model_name})")
                _reported_models.add(model_name)
            return np.asarray(x_next), float(u)

    result = _native.simulate_interval(
        np.ascontiguousarray(state, dtype=np.float64),
        float(u), float(dt), float(dt_internal), model_module.rhs,
        output_function, bool(preg), float(r_preg), par,
    )
    if model_name not in _reported_models:
        detail = _numba_status.get(model_name, (False, "not attempted"))[1]
        print(f"ODE backend: Cython compiled RK4 + compiled model ({model_name}); Numba unavailable: {detail}")
        _reported_models.add(model_name)
    return result


