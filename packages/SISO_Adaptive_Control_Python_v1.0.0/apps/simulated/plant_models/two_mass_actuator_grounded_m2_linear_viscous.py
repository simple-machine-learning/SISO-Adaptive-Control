# -*- coding: utf-8 -*-
"""
Two-mass plant with second-order actuator, grounded masses, and linear viscous
damping only.

This file contains the complete setup of this physical model. Algorithmic setup
for scripts 01, 02 and 03 remains in project_setup.py.

State vector:

    chi = [y1, dy1, y2, dy2, F1, dF1, z_f]

The last state z_f is unused and is kept only for API compatibility with the
LuGre model.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "two_mass_actuator_grounded_m2_linear_viscous"

    # Two-mass actuator model
    m1: float = 1.0
    m2: float = 1.0
    kp: float = 25.0
    bp: float = 0.0
    k1: float = 0.35
    k2: float = 0.20
    kg1: float = 0.0
    kg2: float = 2.0
    ka: float = 1.0
    omega_a: float = 18.0
    zeta_a: float = 0.65


def default_params():
    return PlantParams()


def initial_state(par):
    return np.zeros(7, dtype=float)


def friction_force(v, z_f, par):
    return 0.0, 0.0, np.nan


def algebraic_outputs(chi, par):
    y1 = chi[0]
    dy1 = chi[1]
    y2 = chi[2]
    dy2 = chi[3]
    F1 = chi[4]
    z_f = chi[6]

    F2 = par.kp * (y1 - y2) + par.bp * (dy1 - dy2)
    F_f, dz_f, g_f = friction_force(dy2, z_f, par)

    return {
        "y1": y1,
        "dy1": dy1,
        "y2": y2,
        "dy2": dy2,
        "F1": F1,
        "F2": F2,
        "z_f": z_f,
        "F_f": F_f,
        "dz_f": dz_f,
        "g_f": g_f,
    }


def rhs(t_local, chi, u_const, par):
    y1 = chi[0]
    dy1 = chi[1]
    y2 = chi[2]
    dy2 = chi[3]
    F1 = chi[4]
    dF1 = chi[5]

    F2 = par.kp * (y1 - y2) + par.bp * (dy1 - dy2)
    F_f = 0.0
    dz_f = 0.0

    ddy1 = (F1 - F2 - par.kg1 * y1 - par.k1 * dy1) / par.m1
    ddy2 = (F2 - par.kg2 * y2 - par.k2 * dy2 - F_f) / par.m2
    ddF1 = (
        par.omega_a**2 * par.ka * u_const
        - 2.0 * par.zeta_a * par.omega_a * dF1
        - par.omega_a**2 * F1
    )

    return np.array([dy1, ddy1, dy2, ddy2, dF1, ddF1, dz_f], dtype=float)
