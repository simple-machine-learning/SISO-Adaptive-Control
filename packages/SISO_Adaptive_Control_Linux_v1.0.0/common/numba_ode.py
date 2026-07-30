"""Automatic Numba ODE backend built from the existing Python plant sources.

The original model source remains authoritative.  Numeric dataclass fields are
mapped to a generated Numba jitclass and the model RHS plus RK4 interval are
compiled in nopython mode.  Unsupported models are reported to the caller so
that the existing compiled Cython backend can be used instead.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib.util
import math
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

try:
    from numba import boolean, float64, int64, njit
    from numba.experimental import jitclass
except ImportError:  # pragma: no cover
    njit = None

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "apps" / "simulated" / "plant_models"


class _DTypeFixer(ast.NodeTransformer):
    """Convert dtype=float in NumPy constructors to dtype=np.float64."""

    _constructors = {"array", "asarray", "zeros", "ones", "empty", "full"}

    def visit_Call(self, node):
        self.generic_visit(node)
        func = node.func
        is_numpy_ctor = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "np"
            and func.attr in self._constructors
        )
        if not is_numpy_ctor:
            return node
        for kw in node.keywords:
            if kw.arg == "dtype" and isinstance(kw.value, ast.Name) and kw.value.id == "float":
                kw.value = ast.Attribute(value=ast.Name(id="np", ctx=ast.Load()), attr="float64", ctx=ast.Load())
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Name) and node.args[1].id == "float":
            node.args[1] = ast.Attribute(value=ast.Name(id="np", ctx=ast.Load()), attr="float64", ctx=ast.Load())
        return node


def _load_source_module(model_name: str) -> ModuleType:
    path = MODEL_DIR / f"{model_name}.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    tree = _DTypeFixer().visit(tree)
    ast.fix_missing_locations(tree)
    module = ModuleType(f"_numba_source_{model_name}")
    module.__file__ = str(path)
    module.__dict__.update({"np": np, "math": math})
    sys.modules[module.__name__] = module
    # Delay wrapper modules import another plant module and are intentionally
    # left on the already compiled Cython backend.
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) and any(a.name.startswith("plant_models") for a in n.names)
           for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))):
        raise NotImplementedError("cross-model import")
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


def _numeric_fields(par: Any):
    result = []
    for field in dataclasses.fields(par):
        value = getattr(par, field.name)
        if isinstance(value, (bool, np.bool_)):
            result.append((field.name, boolean, bool))
        elif isinstance(value, (int, np.integer)):
            result.append((field.name, int64, int))
        elif isinstance(value, (float, np.floating)):
            result.append((field.name, float64, float))
    return result


def _make_param_class(fields):
    args = ", ".join(name for name, _, _ in fields)
    lines = ["class NativeParams:", f"    def __init__(self, {args}):"]
    lines.extend(f"        self.{name} = {name}" for name, _, _ in fields)
    namespace: dict[str, Any] = {}
    exec("\n".join(lines), namespace)
    return jitclass([(name, typ) for name, typ, _ in fields])(namespace["NativeParams"])


@lru_cache(maxsize=None)
def _build(model_name: str):
    if njit is None:
        raise RuntimeError("Numba is not installed")
    module = _load_source_module(model_name)
    par0 = module.default_params()
    fields = _numeric_fields(par0)
    ParamClass = _make_param_class(fields)

    # Compile all local numerical helpers before RHS so Numba sees dispatchers
    # in globals. Public helpers such as friction_force() and
    # stribeck_function() are used by the LuGre models.
    api_names = {"default_params", "initial_state", "algebraic_outputs", "rhs"}
    helper_names = []
    for name, obj in list(module.__dict__.items()):
        if (name not in api_names and callable(obj)
                and getattr(obj, "__module__", None) == module.__name__):
            module.__dict__[name] = njit(cache=False)(obj)
            helper_names.append(name)
    rhs = njit(cache=False)(module.rhs)

    @njit(cache=False)
    def rk4_interval(x, u, dt, dt_internal, p):
        n_steps = max(1, int(math.ceil(dt / dt_internal)))
        h = dt / n_steps
        state = x.copy()
        for _ in range(n_steps):
            k1 = rhs(0.0, state, u, p)
            k2 = rhs(0.0, state + 0.5 * h * k1, u, p)
            k3 = rhs(0.0, state + 0.5 * h * k2, u, p)
            k4 = rhs(0.0, state + h * k3, u, p)
            state = state + (h / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
        return state

    return module, fields, ParamClass, rhs, rk4_interval


def available_for(model_name: str, par: Any, state: np.ndarray) -> tuple[bool, str]:
    try:
        _, fields, ParamClass, rhs, rk4 = _build(model_name)
        p = ParamClass(*[cast(getattr(par, name)) for name, _, cast in fields])
        # Trigger compilation using the actual state dimension.
        rk4(np.ascontiguousarray(state, dtype=np.float64), 0.0, 1e-6, 1e-6, p)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def simulate_interval(state, u, dt, dt_internal, model_name: str, par):
    _, fields, ParamClass, rhs, rk4 = _build(model_name)
    p = ParamClass(*[cast(getattr(par, name)) for name, _, cast in fields])
    return np.asarray(
        rk4(np.ascontiguousarray(state, dtype=np.float64), float(u), float(dt), float(dt_internal), p),
        dtype=np.float64,
    )
