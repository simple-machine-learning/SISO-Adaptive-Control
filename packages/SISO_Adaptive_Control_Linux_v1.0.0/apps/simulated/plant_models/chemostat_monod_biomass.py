# -*- coding: utf-8 -*-
"""Chemostat with Monod kinetics: biomass control by dilution-rate command.
State chi=[X,S,D,0,0,0,0], y2=X-X0.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="chemostat_monod_biomass"
    X0: float=0.60; S0: float=0.40; D0: float=0.18; D_gain: float=0.12
    tau_D: float=0.25; mu_max: float=0.55; K_S: float=0.18
    k_decay: float=0.015; Y_XS: float=0.62; S_in: float=1.0
def default_params(): return PlantParams()
def initial_state(par): return np.array([par.X0,par.S0,par.D0,0,0,0,0],float)
def algebraic_outputs(chi,par):
    X,S,D=chi[:3]; mu=par.mu_max*S/(par.K_S+S)
    return {"biomass":X,"biomass_deviation":X-par.X0,"substrate":S,"dilution":D,"growth_rate":mu}
def rhs(t,chi,u,par):
    X,S,D=chi[:3]; Dcmd=max(0.01,par.D0+par.D_gain*np.tanh(u)); mu=par.mu_max*S/(par.K_S+S)
    dX=(mu-D-par.k_decay)*X
    dS=D*(par.S_in-S)-(mu/par.Y_XS)*X
    return np.array([dX,dS,(Dcmd-D)/par.tau_D,0,0,0,0],float)
