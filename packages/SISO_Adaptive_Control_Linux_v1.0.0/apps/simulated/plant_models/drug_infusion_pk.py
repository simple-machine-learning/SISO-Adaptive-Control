# -*- coding: utf-8 -*-
"""Two-compartment nonlinear pharmacokinetic model with saturable elimination.
State chi=[C1,C2,R,0,0,0,0], y2=C1-C10. Educational simulation only.
"""
from dataclasses import dataclass
import numpy as np
@dataclass
class PlantParams:
    plant_model_name: str="drug_infusion_pk"
    C10: float=1.0; C20: float=0.65; R0: float=0.55; R_gain: float=0.45
    tau_pump: float=0.18; V1: float=4.0; V2: float=8.0; Q: float=0.55
    Vmax: float=0.65; Km: float=0.75
def default_params(): return PlantParams()
def initial_state(par): return np.array([par.C10,par.C20,par.R0,0,0,0,0],float)
def algebraic_outputs(chi,par):
    C1,C2,R=chi[:3]; elim=par.Vmax*C1/(par.Km+C1)
    return {"central_concentration":C1,"central_concentration_deviation":C1-par.C10,"peripheral_concentration":C2,"infusion_rate":R,"elimination":elim}
def rhs(t,chi,u,par):
    C1,C2,R=chi[:3]; Rcmd=max(0.0,par.R0+par.R_gain*np.tanh(u)); elim=par.Vmax*C1/(par.Km+C1)
    return np.array([(R-elim-par.Q*(C1-C2))/par.V1, par.Q*(C1-C2)/par.V2,
                     (Rcmd-R)/par.tau_pump,0,0,0,0],float)
