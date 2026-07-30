# -*- coding: utf-8 -*-
"""Voice-coil electromechanical position servo.

State chi = [x, v, i, v_a, 0, 0, 0], controlled output y = x.
The model includes amplifier lag, coil electrical dynamics, back EMF,
linear/cubic suspension stiffness, viscous damping, and smooth Coulomb friction.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class PlantParams:
    plant_model_name: str = "voice_coil_servo"
    mass: float = 0.12
    resistance: float = 3.2
    inductance: float = 0.018
    force_constant: float = 4.5
    back_emf_constant: float = 4.5
    damping: float = 1.1
    stiffness: float = 18.0
    cubic_stiffness: float = 1.8e4
    coulomb_friction: float = 0.18
    stribeck_velocity: float = 0.004
    amplifier_gain: float = 8.0
    amplifier_time_constant: float = 0.004


def default_params():
    return PlantParams()


def initial_state(par):
    return np.zeros(7, dtype=float)


def algebraic_outputs(chi, par):
    x, velocity, current, drive_voltage = np.asarray(chi, dtype=float)[:4]
    electromagnetic_force = par.force_constant * current
    friction_force = (
        par.damping * velocity
        + par.coulomb_friction * np.tanh(velocity / par.stribeck_velocity)
    )
    return {
        "position": x,
        "velocity": velocity,
        "coil_current": current,
        "drive_voltage": drive_voltage,
        "electromagnetic_force": electromagnetic_force,
        "friction_force": friction_force,
    }


def rhs(t, chi, u, par):
    x, velocity, current, drive_voltage = np.asarray(chi, dtype=float)[:4]
    voltage_command = par.amplifier_gain * np.tanh(float(u))
    electromagnetic_force = par.force_constant * current
    friction_force = (
        par.damping * velocity
        + par.coulomb_friction * np.tanh(velocity / par.stribeck_velocity)
    )
    restoring_force = par.stiffness * x + par.cubic_stiffness * x ** 3

    dx = velocity
    dv = (electromagnetic_force - friction_force - restoring_force) / par.mass
    di = (drive_voltage - par.resistance * current - par.back_emf_constant * velocity) / par.inductance
    ddrive_voltage = (voltage_command - drive_voltage) / par.amplifier_time_constant
    return np.array([dx, dv, di, ddrive_voltage, 0.0, 0.0, 0.0], dtype=float)
