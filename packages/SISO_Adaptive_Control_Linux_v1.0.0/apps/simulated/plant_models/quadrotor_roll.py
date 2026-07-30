# -*- coding: utf-8 -*-
"""Quadrotor roll channel with actuator lag and changing inertia.
State chi=[phi,omega,tau,J,0,0,0], y2=phi.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="quadrotor_roll"
    J0: float=0.022; J_delta: float=0.008; change_time: float=60.0
    tau_act: float=0.06; torque_gain: float=0.16; damping: float=0.025
    nonlinear_drag: float=0.010; disturbance_amp: float=0.015; disturbance_period: float=13.0; attitude_stiffness: float=0.12
def default_params(): return PlantParams()
def initial_state(par): return np.array([0,0,0,par.J0,0,0,0],float)
def algebraic_outputs(chi,par):
    phi,w,tau,J=chi[:4]
    return {"roll":phi,"roll_rate":w,"torque":tau,"inertia":J}
def rhs(t,chi,u,par):
    phi,w,tau,J=chi[:4]; Jtarget=par.J0+(par.J_delta if t>=par.change_time else 0.0)
    taucmd=par.torque_gain*np.tanh(u); dist=par.disturbance_amp*np.sin(2*np.pi*t/par.disturbance_period)
    return np.array([w,(tau-par.damping*w-par.attitude_stiffness*phi-par.nonlinear_drag*w*abs(w)+dist)/J,
                     (taucmd-tau)/par.tau_act,(Jtarget-J)/0.20,0,0,0],float)
