# -*- coding: utf-8 -*-
"""
Two-mass plant with second-order actuator, grounded masses, and stronger LuGre friction
acting on m2.

This file contains the complete setup of this physical model. Algorithmic setup
for scripts 01, 02 and 03 remains in project_setup.py.

State vector:

    chi = [y1, dy1, y2, dy2, F1, dF1, z_f]
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "two_mass_actuator_grounded_m2_lugre2"

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

    # LuGre friction on m2
    # Deliberately pronounced LuGre/Stribeck regime.  The previous values
    # made friction small compared with the actuator force and the Stribeck
    # transition ended at velocities far below the normal operating range.
    # These values create visible presliding/stiction, breakaway and a broad
    # velocity-dependent drop from static to Coulomb friction while retaining
    # a stable, fully controllable benchmark over the existing input range.
    normal_force: float = 8.0
    mu_k: float = 0.12
    mu_s: float = 0.65
    sigma_0: float = 5.0e3
    sigma_1: float = 30.0
    sigma_2: float = 0.05
    v_s: float = 0.12
    friction_shape_alpha: float = 2.0
    g_eps: float = 1.0e-12


def default_params():
    return PlantParams()


def initial_state(par):
    return np.zeros(7, dtype=float)


def stribeck_function(v, par):
    F_c = par.mu_k * par.normal_force
    F_s = par.mu_s * par.normal_force
    v_ratio = abs(v / par.v_s)
    g = F_c + (F_s - F_c) * np.exp(-(v_ratio ** par.friction_shape_alpha))
    return max(g, par.g_eps)


def friction_force(v, z_f, par):
    g = stribeck_function(v, par)
    dz_f = v - z_f * par.sigma_0 * abs(v) / g
    F_f = par.sigma_0 * z_f + par.sigma_1 * dz_f + par.sigma_2 * v
    return F_f, dz_f, g


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
    z_f = chi[6]

    F2 = par.kp * (y1 - y2) + par.bp * (dy1 - dy2)
    F_f, dz_f, _ = friction_force(dy2, z_f, par)

    ddy1 = (F1 - F2 - par.kg1 * y1 - par.k1 * dy1) / par.m1
    ddy2 = (F2 - par.kg2 * y2 - par.k2 * dy2 - F_f) / par.m2
    ddF1 = (
        par.omega_a**2 * par.ka * u_const
        - 2.0 * par.zeta_a * par.omega_a * dF1
        - par.omega_a**2 * F1
    )

    return np.array([dy1, ddy1, dy2, ddy2, dF1, ddF1, dz_f], dtype=float)
