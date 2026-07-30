# -*- coding: utf-8 -*-
"""Linear reduced-order load-frequency-control model: governor, turbine and grid."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "microgrid_frequency_linear"
    T_g: float = 0.08
    T_t: float = 0.40
    H: float = 0.1667
    D: float = 0.015
    R: float = 3.0
    control_gain: float = 0.30
    load_bias: float = 0.0

def default_params(): return PlantParams()
def initial_state(par): return np.zeros(4, float)
def algebraic_outputs(chi, par):
    xg, pm, df = chi[:3]
    return {"frequency_deviation": df, "governor_output": xg,
            "mechanical_power": pm, "load_disturbance": par.load_bias,
            "frequency_hz": 50.0+df}
def rhs(t, chi, u, par):
    xg, pm, df = chi[:3]
    dxg = (-xg+par.control_gain*np.tanh(float(u))-df/par.R)/par.T_g
    dpm = (-pm+xg)/par.T_t
    ddf = (pm-par.load_bias-par.D*df)/(2.0*par.H)
    return np.array([dxg, dpm, ddf, 0.0], float)
