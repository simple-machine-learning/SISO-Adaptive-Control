# -*- coding: utf-8 -*-
"""Reduced soil-water and microbial-respiration SISO ODE benchmark."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_moisture_respiration"
    theta_nom: float = 0.55
    theta_opt: float = 0.58
    theta_width: float = 0.20
    carbon_nom: float = 1.0
    carbon_input: float = 0.018
    decay_rate: float = 0.020
    irrigation_gain: float = 0.035
    evap_rate: float = 0.010
    drainage_rate: float = 0.16
    field_capacity: float = 0.72
    respiration_nom: float = 0.020

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.theta_nom, par.carbon_nom, 0.0], float)
def _activity(theta, par):
    return np.exp(-0.5*((theta-par.theta_opt)/par.theta_width)**2)
def algebraic_outputs(chi, par):
    theta, carbon = chi[:2]
    activity = _activity(theta, par)
    respiration = par.decay_rate*max(carbon,0.0)*activity
    return {"respiration_deviation": respiration-par.respiration_nom,
            "soil_moisture": theta, "available_carbon": carbon,
            "co2_flux": respiration, "moisture_activity": activity}
def rhs(t, chi, u, par):
    theta, carbon = chi[:2]
    irrigation = par.irrigation_gain*np.tanh(float(u))
    drainage = par.drainage_rate*max(theta-par.field_capacity, 0.0)**2
    dtheta = irrigation + par.evap_rate*(par.theta_nom-theta) - drainage
    activity = _activity(theta, par)
    respiration = par.decay_rate*max(carbon,0.0)*activity
    dcarbon = par.carbon_input-respiration
    return np.array([dtheta, dcarbon, 0.0], float)
