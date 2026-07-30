# -*- coding: utf-8 -*-
"""Quadrotor vertical channel with motor lag, quadratic drag and payload change.
State chi=[z,v,T,m,0,0,0], y2=z. Command u is collective-thrust deviation.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="quadrotor_altitude"
    m0: float=1.20; g: float=9.81; tau_motor: float=0.10
    thrust_gain: float=5.0; drag_linear: float=0.35; drag_quadratic: float=0.08
    payload_delta: float=0.25; payload_time: float=60.0; wind_amp: float=0.5; wind_period: float=17.0; position_stiffness: float=0.8
def default_params(): return PlantParams()
def initial_state(par): return np.array([0,0,par.m0*par.g,par.m0,0,0,0],float)
def algebraic_outputs(chi,par):
    z,v,T,m=chi[:4]
    return {"altitude":z,"vertical_velocity":v,"thrust":T,"mass":m}
def rhs(t,chi,u,par):
    z,v,T,m=chi[:4]; mtarget=par.m0+(par.payload_delta if t>=par.payload_time else 0.0)
    Tcmd=max(0.0,mtarget*par.g+par.thrust_gain*np.tanh(u))
    drag=par.drag_linear*v+par.drag_quadratic*v*abs(v)
    wind=par.wind_amp*np.sin(2*np.pi*t/par.wind_period)
    return np.array([v,(T-m*par.g-drag-par.position_stiffness*z+wind)/m,(Tcmd-T)/par.tau_motor,(mtarget-m)/0.25,0,0,0],float)
