# -*- coding: utf-8 -*-
"""Nonlinear SISO tank-level plant with a bidirectional pump.

The same signed pump command fills or drains the tank. Gravity outflow is
proportional to sqrt(h), which makes upward and downward transients different,
while the bidirectional pump preserves SISO control authority in both
directions around the nominal operating point.

State chi = [h, q_pump, 0, 0, 0, 0, 0]
Controlled output = h - h0 [m]
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "bidirectional_tank_level"
    h0: float = 1.0
    area: float = 1.6
    outflow_coeff: float = 0.34
    pump_gain: float = 0.62
    tau_pump: float = 0.22

    @property
    def q0(self):
        return self.outflow_coeff * np.sqrt(self.h0)


def default_params():
    return PlantParams()


def initial_state(par):
    return np.array([par.h0, par.q0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)


def algebraic_outputs(chi, par):
    h, q_pump = np.asarray(chi, dtype=float)[:2]
    q_out = par.outflow_coeff * np.sqrt(max(h, 0.0))
    return {
        "level": h,
        "level_deviation": h - par.h0,
        "pump_flow": q_pump,
        "gravity_outflow": q_out,
        "net_flow": q_pump - q_out,
    }


def rhs(t, chi, u, par):
    h, q_pump = np.asarray(chi, dtype=float)[:2]
    q_cmd = par.q0 + par.pump_gain * np.tanh(float(u))
    dq_pump = (q_cmd - q_pump) / par.tau_pump
    q_out = par.outflow_coeff * np.sqrt(max(h, 0.0))
    dh = (q_pump - q_out) / par.area
    # Keep the continuous state on the physical half-line. If a numerical
    # integration stage crosses slightly below zero, drive it smoothly back
    # instead of leaving it trapped at a negative level.
    if h < 0.0:
        dh = max(dh, -h / 0.01)
    elif h == 0.0 and dh < 0.0:
        dh = 0.0
    return np.array([dh, dq_pump, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)
