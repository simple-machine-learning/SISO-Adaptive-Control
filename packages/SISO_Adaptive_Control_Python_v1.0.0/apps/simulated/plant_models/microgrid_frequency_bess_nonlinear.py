# -*- coding: utf-8 -*-
"""Nonlinear microgrid frequency model with diesel governor and BESS actuator/SOC."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "microgrid_frequency_bess_nonlinear"
    T_g: float = 0.08
    T_t: float = 0.40
    T_bess: float = 0.10
    H: float = 0.1667
    D: float = 0.020
    R: float = 3.0
    bess_power_max: float = 0.45
    diesel_bias: float = 0.0
    load_bias: float = 0.0
    soc_nom: float = 0.60
    energy_capacity: float = 1800.0
    deadband_hz: float = 0.005

def default_params(): return PlantParams()
def initial_state(par): return np.array([0.0, 0.0, 0.0, 0.0, par.soc_nom], float)
def algebraic_outputs(chi, par):
    xg, pm, df, pb, soc = chi[:5]
    return {"frequency_deviation": df, "governor_output": xg,
            "diesel_power": pm, "bess_power": pb, "state_of_charge": soc,
            "load_disturbance": par.load_bias, "frequency_hz": 50.0+df}
def rhs(t, chi, u, par):
    xg, pm, df, pb, soc = chi[:5]
    db = 0.0 if abs(df) <= par.deadband_hz else df-np.sign(df)*par.deadband_hz
    dxg = (-xg+par.diesel_bias-db/par.R)/par.T_g
    dpm = (-pm+xg)/par.T_t
    availability = np.clip(4.0*soc*(1.0-soc), 0.0, 1.0)
    pb_cmd = par.bess_power_max*availability*np.tanh(float(u))
    dpb = (pb_cmd-pb)/par.T_bess
    ddf = (pm+pb-par.load_bias-par.D*df)/(2.0*par.H)
    dsoc = -pb/par.energy_capacity
    if soc <= 0.02 and dsoc < 0.0: dsoc = 0.0
    if soc >= 0.98 and dsoc > 0.0: dsoc = 0.0
    return np.array([dxg, dpm, ddf, dpb, dsoc], float)
