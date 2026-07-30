# -*- coding: utf-8 -*-
"""Delayed-input variant of ``network_router_fluid_queue``.

The transport delay is represented by an 3-stage cascaded lag (Erlang
transport approximation) with mean delay ``input_delay_sec``. This keeps the
plant in finite-dimensional ODE form while producing a substantially delayed,
smooth actuator command.
"""
from dataclasses import dataclass
import numpy as np
from plant_models import network_router_fluid_queue as base

@dataclass
class PlantParams(base.PlantParams):
    plant_model_name: str = "network_router_fluid_queue_with_delay"
    input_delay_sec: float = 0.35
    delay_order: int = 3

def default_params():
    return PlantParams()

def initial_state(par):
    x0 = np.asarray(base.initial_state(par), dtype=float)
    return np.concatenate((x0, np.zeros(int(par.delay_order), dtype=float)))

def _split(chi, par):
    n = len(base.initial_state(par))
    return np.asarray(chi[:n], dtype=float), np.asarray(chi[n:n+int(par.delay_order)], dtype=float)

def algebraic_outputs(chi, par):
    x, z = _split(chi, par)
    out = dict(base.algebraic_outputs(x, par))
    out["effective_input"] = float(z[-1]) if len(z) else 0.0
    out["input_delay_sec"] = float(par.input_delay_sec)
    return out

def rhs(t, chi, u, par):
    x, z = _split(chi, par)
    order = max(1, int(par.delay_order))
    tau_stage = max(float(par.input_delay_sec) / order, 1.0e-12)
    dz = np.empty(order, dtype=float)
    source = float(u)
    for i in range(order):
        dz[i] = (source - z[i]) / tau_stage
        source = z[i]
    dx = np.asarray(base.rhs(t, x, float(z[-1]), par), dtype=float)
    return np.concatenate((dx, dz))
