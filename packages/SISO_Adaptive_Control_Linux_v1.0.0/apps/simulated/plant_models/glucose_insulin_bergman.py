# -*- coding: utf-8 -*-
"""Reduced Bergman glucose-insulin model with meal disturbance.
State chi=[G,X,I,U,D,0,0], y2=G-Gb. Educational simulation only.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="glucose_insulin_bergman"
    Gb: float=5.5; Ib: float=10.0; U0: float=0.0; U_gain: float=2.2
    tau_pump: float=0.20; p1: float=0.025; p2: float=0.030; p3: float=0.0012
    n: float=0.10; V_I: float=12.0; meal_amp: float=0.12; meal_time: float=45.0; meal_tau: float=14.0
def default_params(): return PlantParams()
def initial_state(par): return np.array([par.Gb,0,par.Ib,par.U0,0,0,0],float)
def algebraic_outputs(chi,par):
    G,X,I,U,D=chi[:5]
    return {"glucose":G,"glucose_deviation":G-par.Gb,"remote_insulin_effect":X,"insulin":I,"infusion_rate":U,"meal_disturbance":D}
def rhs(t,chi,u,par):
    G,X,I,U,D=chi[:5]; Ucmd=max(0.0,par.U0+par.U_gain*(0.5+0.5*np.tanh(u)))
    Dtarget=par.meal_amp*np.exp(-(t-par.meal_time)/par.meal_tau) if t>=par.meal_time else 0.0
    return np.array([-par.p1*(G-par.Gb)-X*G+D,-par.p2*X+par.p3*(I-par.Ib),
                     -par.n*(I-par.Ib)+U/par.V_I,(Ucmd-U)/par.tau_pump,(Dtarget-D)/0.3,0,0],float)
