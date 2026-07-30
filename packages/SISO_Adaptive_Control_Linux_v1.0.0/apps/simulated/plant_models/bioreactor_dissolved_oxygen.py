# -*- coding: utf-8 -*-
"""Stirred-tank bioreactor: dissolved oxygen control by agitation command.

State chi = [C, X, N, OUR, 0, 0, 0]. Controlled output y2 = C-C0.
The command u is a dimensionless deviation; N_cmd=N0+N_gain*tanh(u).
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str = "bioreactor_dissolved_oxygen"
    C_star: float = 1.0; C0: float = 0.55; X0: float = 1.0
    N0: float = 0.55; N_gain: float = 0.35; tau_N: float = 0.30
    kla0: float = 0.12; kla1: float = 0.55; kla2: float = 0.18
    qO2: float = 0.24; mu_max: float = 0.010; K_O2: float = 0.20
    k_decay: float = 0.004; tau_our: float = 0.7
def default_params(): return PlantParams()
def initial_state(par):
    our0=par.qO2*par.X0*par.C0/(par.K_O2+par.C0)
    return np.array([par.C0,par.X0,par.N0,our0,0,0,0],float)
def algebraic_outputs(chi,par):
    C,X,N,OUR=chi[:4]; kla=par.kla0+par.kla1*N+par.kla2*N*N
    return {"C_O2":C,"C_O2_deviation":C-par.C0,"biomass":X,"agitation":N,"kla":kla,"OUR":OUR}
def rhs(t,chi,u,par):
    C,X,N,OUR=chi[:4]; Ncmd=par.N0+par.N_gain*np.tanh(u)
    kla=par.kla0+par.kla1*N+par.kla2*N*N
    mu=par.mu_max*C/(par.K_O2+C)
    OURss=par.qO2*X*C/(par.K_O2+C)
    return np.array([kla*(par.C_star-C)-OUR, (mu-par.k_decay)*X,
                     (Ncmd-N)/par.tau_N,(OURss-OUR)/par.tau_our,0,0,0],float)
