# -*- coding: utf-8 -*-
"""Asymmetric SISO thermoelectric (Peltier) temperature-control plant.

The single manipulated input is the signed electrical-current command. Positive
current heats the controlled plate; negative current cools it. The Peltier term
is odd in current while Joule heating is even, so heating and cooling have
physically different dynamics although the plant remains controllable from one
input over the recommended operating range.

State chi = [T_hot, T_cold, I, 0, 0, 0, 0]
Controlled output = T_hot - T_ambient [deg C]
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "peltier_thermal_asymmetric"
    T_ambient: float = 25.0
    C_hot: float = 28.0
    C_cold: float = 42.0
    alpha: float = 0.018       # effective Seebeck/Peltier coefficient [W/K/A]
    resistance: float = 1.15   # electrical resistance [ohm]
    conductance: float = 0.65  # thermal conductance between plates [W/K]
    h_hot: float = 0.55        # hot-side ambient loss [W/K]
    h_cold: float = 1.25       # cold-side ambient loss [W/K]
    current_gain: float = 2.2  # maximum signed current [A]
    tau_current: float = 0.18  # current-driver time constant [s]


def default_params():
    return PlantParams()


def initial_state(par):
    return np.array([par.T_ambient, par.T_ambient, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)


def algebraic_outputs(chi, par):
    T_hot, T_cold, current = np.asarray(chi, dtype=float)[:3]
    T_hot_K = T_hot + 273.15
    peltier_heat = par.alpha * T_hot_K * current
    joule_heat = par.resistance * current * current
    return {
        "temperature_hot": T_hot,
        "temperature_deviation": T_hot - par.T_ambient,
        "temperature_cold": T_cold,
        "current": current,
        "peltier_heat": peltier_heat,
        "joule_heat": joule_heat,
    }


def rhs(t, chi, u, par):
    T_hot, T_cold, current = np.asarray(chi, dtype=float)[:3]
    current_cmd = par.current_gain * np.tanh(float(u))
    dcurrent = (current_cmd - current) / par.tau_current

    T_hot_K = T_hot + 273.15
    T_cold_K = T_cold + 273.15
    peltier_hot = par.alpha * T_hot_K * current
    peltier_cold = par.alpha * T_cold_K * current
    joule_half = 0.5 * par.resistance * current * current
    conduction = par.conductance * (T_hot - T_cold)

    dT_hot = (
        peltier_hot + joule_half - conduction
        - par.h_hot * (T_hot - par.T_ambient)
    ) / par.C_hot
    dT_cold = (
        -peltier_cold + joule_half + conduction
        - par.h_cold * (T_cold - par.T_ambient)
    ) / par.C_cold

    return np.array([dT_hot, dT_cold, dcurrent, 0.0, 0.0, 0.0, 0.0], dtype=float)
