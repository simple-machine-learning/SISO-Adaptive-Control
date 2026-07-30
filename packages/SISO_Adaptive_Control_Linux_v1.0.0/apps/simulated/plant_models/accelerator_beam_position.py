# -*- coding: utf-8 -*-
"""Transverse beam-position dynamics controlled by a corrector magnet."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "accelerator_beam_position"
    omega_beta: float = 18.0
    damping_ratio: float = 0.12
    magnet_gain: float = 8.0
    tau_magnet: float = 0.012
    cubic_stiffness: float = 45.0
    orbit_bias: float = 0.0

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.orbit_bias, 0.0, 0.0, 0.0], float)
def algebraic_outputs(chi, par):
    x, v, m = chi[:3]
    return {"position": x, "beam_velocity": v, "magnet_field": m,
            "restoring_force": par.omega_beta**2*x+par.cubic_stiffness*x**3}
def rhs(t, chi, u, par):
    x, v, m = chi[:3]
    m_cmd = np.tanh(float(u))
    a = (-2.0*par.damping_ratio*par.omega_beta*v-par.omega_beta**2*x
         -par.cubic_stiffness*x**3+par.magnet_gain*m)
    return np.array([v, a, (m_cmd-m)/par.tau_magnet, 0.0], float)
