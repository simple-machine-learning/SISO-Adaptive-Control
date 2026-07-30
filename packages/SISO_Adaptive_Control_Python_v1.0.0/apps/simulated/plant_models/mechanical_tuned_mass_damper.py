# -*- coding: utf-8 -*-
"""Primary structure with a passive tuned-mass vibration absorber.

SISO input: commanded actuator force applied to the primary structure.
SISO output: primary-structure displacement.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "mechanical_tuned_mass_damper"
    m_primary: float = 1.0
    m_absorber: float = 0.12
    k_primary: float = 42.0
    c_primary: float = 0.45
    k_absorber: float = 5.0
    c_absorber: float = 0.16
    k_primary_cubic: float = 55.0
    k_absorber_cubic: float = 18.0
    actuator_force_max: float = 12.0
    actuator_tau: float = 0.025


def default_params():
    return PlantParams()


def initial_state(par):
    # [x_primary, v_primary, x_absorber, v_absorber, actuator_force]
    return np.zeros(5, dtype=float)


def algebraic_outputs(chi, par):
    x_p, v_p, x_a, v_a, force = chi[:5]
    rel_x = x_a - x_p
    rel_v = v_a - v_p
    absorber_force = par.k_absorber * rel_x + par.k_absorber_cubic * rel_x**3 + par.c_absorber * rel_v
    primary_restoring = par.k_primary * x_p + par.k_primary_cubic * x_p**3 + par.c_primary * v_p
    return {
        "primary_displacement": x_p,
        "primary_velocity": v_p,
        "absorber_displacement": x_a,
        "absorber_velocity": v_a,
        "relative_displacement": rel_x,
        "actuator_force": force,
        "absorber_force": absorber_force,
        "primary_restoring_force": primary_restoring,
    }


def rhs(t, chi, u, par):
    x_p, v_p, x_a, v_a, force = chi[:5]
    force_cmd = par.actuator_force_max * np.tanh(float(u))
    rel_x = x_a - x_p
    rel_v = v_a - v_p
    f_abs = par.k_absorber * rel_x + par.k_absorber_cubic * rel_x**3 + par.c_absorber * rel_v
    f_ground = par.k_primary * x_p + par.k_primary_cubic * x_p**3 + par.c_primary * v_p
    a_p = (force - f_ground + f_abs) / par.m_primary
    a_a = -f_abs / par.m_absorber
    return np.array([v_p, a_p, v_a, a_a, (force_cmd - force) / par.actuator_tau], dtype=float)
