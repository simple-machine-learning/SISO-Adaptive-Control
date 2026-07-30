# -*- coding: utf-8 -*-
"""Reduced RF-cavity envelope amplitude with amplifier lag and beam loading."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "accelerator_rf_cavity_amplitude"
    amplitude_nom: float = 1.0
    drive_nom: float = 1.12
    drive_gain: float = 0.75
    tau_amplifier: float = 0.0015
    tau_cavity: float = 0.006
    cavity_gain: float = 1.0
    beam_loading: float = 0.12
    detuning_nonlinearity: float = 0.10

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.amplitude_nom, par.drive_nom, 0.0], float)
def algebraic_outputs(chi, par):
    V, a = chi[:2]
    return {"field_deviation": V-par.amplitude_nom, "field_amplitude": V,
            "rf_drive": a, "beam_loading": par.beam_loading,
            "detuning_loss": par.detuning_nonlinearity*V**3}
def rhs(t, chi, u, par):
    V, a = chi[:2]
    a_cmd = max(0.0, par.drive_nom+par.drive_gain*np.tanh(float(u)))
    dV = (-V-par.detuning_nonlinearity*V**3+par.cavity_gain*a-par.beam_loading)/par.tau_cavity
    return np.array([dV, (a_cmd-a)/par.tau_amplifier, 0.0], float)
