# -*- coding: utf-8 -*-
"""CPU/GPU lumped thermal model controlled by signed cooling command."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "cpu_thermal_fan"
    ambient: float = 25.0
    temperature_nom: float = 65.0
    thermal_capacity: float = 18.0
    workload_power: float = 18.0
    passive_conductance: float = 0.22
    fan_conductance: float = 0.55
    fan_nom: float = 0.45
    fan_gain: float = 0.40
    tau_fan: float = 0.8
    leakage_power: float = 0.8
    leakage_alpha: float = 0.025

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.temperature_nom, par.fan_nom, 0.0], float)
def algebraic_outputs(chi, par):
    T, fan = chi[:2]
    leakage = par.leakage_power*np.exp(par.leakage_alpha*(T-par.temperature_nom))
    cooling = (par.passive_conductance+par.fan_conductance*fan)*(T-par.ambient)
    return {"temperature_deviation": T-par.temperature_nom, "temperature": T,
            "fan_speed": fan, "chip_power": par.workload_power+leakage,
            "cooling_power": cooling}
def rhs(t, chi, u, par):
    T, fan = chi[:2]
    fan_cmd = np.clip(par.fan_nom-par.fan_gain*np.tanh(float(u)), 0.0, 1.0)
    leakage = par.leakage_power*np.exp(np.clip(par.leakage_alpha*(T-par.temperature_nom),-5.0,5.0))
    cooling = (par.passive_conductance+par.fan_conductance*max(fan,0.0))*(T-par.ambient)
    dT = (par.workload_power+leakage-cooling)/par.thermal_capacity
    return np.array([dT, (fan_cmd-fan)/par.tau_fan, 0.0], float)
