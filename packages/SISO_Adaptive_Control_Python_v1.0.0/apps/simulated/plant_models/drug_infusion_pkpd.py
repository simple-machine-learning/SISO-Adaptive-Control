# -*- coding: utf-8 -*-
"""Nonlinear PK-PD infusion model with effect compartment and Hill response.
State chi=[C1,C2,Ce,R,E,0,0], y2=E-E0. Educational simulation only.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="drug_infusion_pkpd"
    C10: float=1.0; C20: float=0.65; Ce0: float=0.85; R0: float=0.55; R_gain: float=0.45
    tau_pump: float=0.18; V1: float=4.0; V2: float=8.0; Q: float=0.55
    Vmax: float=0.65; Km: float=0.75; ke0: float=0.30
    E0: float=0.0; Emax: float=1.0; EC50: float=0.90; gamma: float=2.2; tau_E: float=0.12
def default_params(): return PlantParams()
def hill(Ce,p): return p.E0+p.Emax*Ce**p.gamma/(p.EC50**p.gamma+Ce**p.gamma)
def initial_state(par):
    E=hill(par.Ce0,par); return np.array([par.C10,par.C20,par.Ce0,par.R0,E,0,0],float)
def algebraic_outputs(chi,par):
    C1,C2,Ce,R,E=chi[:5]; Ebase=hill(par.Ce0,par)
    return {"central_concentration":C1,"peripheral_concentration":C2,"effect_concentration":Ce,"infusion_rate":R,"effect":E,"effect_deviation":E-Ebase}
def rhs(t,chi,u,par):
    C1,C2,Ce,R,E=chi[:5]; Rcmd=max(0.0,par.R0+par.R_gain*np.tanh(u)); elim=par.Vmax*C1/(par.Km+C1); Ess=hill(Ce,par)
    return np.array([(R-elim-par.Q*(C1-C2))/par.V1,par.Q*(C1-C2)/par.V2,
                     par.ke0*(C1-Ce),(Rcmd-R)/par.tau_pump,(Ess-E)/par.tau_E,0,0],float)
