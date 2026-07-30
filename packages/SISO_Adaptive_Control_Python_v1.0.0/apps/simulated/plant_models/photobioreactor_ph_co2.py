# -*- coding: utf-8 -*-
"""Photobioreactor: pH control by CO2 dosing with light-driven uptake.
State chi=[C_CO2, X, Q_CO2, I, pH_filter,0,0], y2=pH-pH0.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="photobioreactor_ph_co2"
    C0: float=0.35; X0: float=0.8; Q0: float=0.25; I0: float=0.65
    pH0: float=7.20; Q_gain: float=0.22; tau_Q: float=0.25
    kla: float=0.45; C_gas_gain: float=1.15; uptake_max: float=0.18
    K_C: float=0.20; K_I: float=0.25; mu_max: float=0.006; k_decay: float=0.002
    beta_pH: float=1.35; tau_pH: float=0.20; light_amp: float=0.18; light_period: float=60.0
def default_params(): return PlantParams()
def initial_state(par): return np.array([par.C0,par.X0,par.Q0,par.I0,par.pH0,0,0],float)
def algebraic_outputs(chi,par):
    C,X,Q,I,pH=chi[:5]
    return {"CO2":C,"biomass":X,"CO2_flow":Q,"light":I,"pH":pH,"pH_deviation":pH-par.pH0}
def rhs(t,chi,u,par):
    C,X,Q,I,pH=chi[:5]; Qcmd=par.Q0+par.Q_gain*np.tanh(u)
    Itarget=par.I0+par.light_amp*np.sin(2*np.pi*t/par.light_period)
    photo=par.uptake_max*X*(I/(par.K_I+I))*(C/(par.K_C+C))
    Cgas=par.C_gas_gain*Q
    pHeq=par.pH0-par.beta_pH*(C-par.C0)
    mu=par.mu_max*(I/(par.K_I+I))*(C/(par.K_C+C))
    return np.array([par.kla*(Cgas-C)-photo,(mu-par.k_decay)*X,
                     (Qcmd-Q)/par.tau_Q,(Itarget-I)/0.5,(pHeq-pH)/par.tau_pH,0,0],float)
