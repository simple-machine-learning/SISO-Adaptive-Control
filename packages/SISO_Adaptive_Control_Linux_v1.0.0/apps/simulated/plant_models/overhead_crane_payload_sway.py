# -*- coding: utf-8 -*-
"""Nonlinear overhead-crane trolley and suspended-payload dynamics.

SISO input: trolley-drive force command.
SISO output: horizontal payload position. Payload sway angle is diagnostic.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "overhead_crane_payload_sway"
    trolley_mass: float = 1.8
    payload_mass: float = 0.45
    cable_length: float = 0.75
    gravity: float = 9.81
    trolley_damping: float = 0.32
    pivot_damping: float = 0.035
    drive_force_max: float = 14.0
    drive_tau: float = 0.035
    travel_limit: float = 1.5
    end_stop_stiffness: float = 250.0
    end_stop_damping: float = 8.0


def default_params():
    return PlantParams()


def initial_state(par):
    # [trolley_position, trolley_velocity, sway_angle, sway_rate, drive_force]
    return np.zeros(5, dtype=float)


def _end_stop_force(x, v, par):
    excess = abs(x) - par.travel_limit
    if excess <= 0.0:
        return 0.0
    return -np.sign(x) * par.end_stop_stiffness * excess - par.end_stop_damping * v


def algebraic_outputs(chi, par):
    x, v, theta, omega, force = chi[:5]
    payload_x = x + par.cable_length * np.sin(theta)
    payload_y = -par.cable_length * np.cos(theta)
    return {
        "payload_position": payload_x,
        "trolley_position": x,
        "trolley_velocity": v,
        "sway_angle": theta,
        "sway_rate": omega,
        "payload_vertical_position": payload_y,
        "drive_force": force,
        "end_stop_force": _end_stop_force(x, v, par),
    }


def rhs(t, chi, u, par):
    x, v, theta, omega, force = chi[:5]
    M = par.trolley_mass
    m = par.payload_mass
    l = par.cable_length
    s = np.sin(theta)
    c = np.cos(theta)

    force_cmd = par.drive_force_max * np.tanh(float(u))
    applied_force = force - par.trolley_damping * v + _end_stop_force(x, v, par)

    rhs_1 = applied_force + m * l * s * omega**2
    rhs_2 = -par.gravity * s - (par.pivot_damping / (m * l)) * omega
    det = l * (M + m * s**2)
    x_ddot = (l * rhs_1 - m * l * c * rhs_2) / det
    theta_ddot = ((M + m) * rhs_2 - c * rhs_1) / det

    return np.array([v, x_ddot, omega, theta_ddot, (force_cmd - force) / par.drive_tau], dtype=float)
