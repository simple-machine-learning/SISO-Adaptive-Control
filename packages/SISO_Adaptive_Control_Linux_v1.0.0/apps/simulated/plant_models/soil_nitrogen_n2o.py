# -*- coding: utf-8 -*-
"""Reduced nitrification-denitrification and N2O-emission benchmark."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_nitrogen_n2o"
    ammonium_nom: float = 0.65
    nitrate_nom: float = 0.80
    oxygen_nom: float = 0.62
    nit_rate: float = 0.16
    den_rate: float = 0.095
    k_nh4: float = 0.35
    k_no3: float = 0.40
    k_oxygen: float = 0.22
    oxygen_inhibition: float = 0.18
    oxygen_tau: float = 1.8
    aeration_gain: float = 0.28
    nitrogen_input: float = 0.055
    nitrogen_loss: float = 0.025
    frac_n2o_nit: float = 0.035
    frac_n2o_den: float = 0.22
    n2o_nom: float = 0.020

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.ammonium_nom, par.nitrate_nom, par.oxygen_nom, 0.0], float)
def _rates(nh4,no3,o2,par):
    a,n,o=max(nh4,0.0),max(no3,0.0),max(o2,0.0)
    rnit=par.nit_rate*a/(par.k_nh4+a+1e-12)*o/(par.k_oxygen+o+1e-12)
    rden=par.den_rate*n/(par.k_no3+n+1e-12)*par.oxygen_inhibition/(par.oxygen_inhibition+o+1e-12)
    return rnit,rden
def algebraic_outputs(chi, par):
    nh4,no3,o2=chi[:3]
    rnit,rden=_rates(nh4,no3,o2,par)
    n2o=par.frac_n2o_nit*rnit+par.frac_n2o_den*rden
    return {"n2o_deviation": n2o-par.n2o_nom, "ammonium": nh4, "nitrate": no3,
            "oxygen": o2, "nitrification_rate": rnit,
            "denitrification_rate": rden, "n2o_flux": n2o}
def rhs(t, chi, u, par):
    nh4,no3,o2=chi[:3]
    rnit,rden=_rates(nh4,no3,o2,par)
    oeq=np.clip(par.oxygen_nom+par.aeration_gain*np.tanh(float(u)),0.05,1.0)
    dnh4=par.nitrogen_input-rnit-par.nitrogen_loss*max(nh4,0.0)
    dno3=rnit-rden-par.nitrogen_loss*max(no3,0.0)
    do2=(oeq-o2)/par.oxygen_tau-0.35*rnit-0.18*rden
    return np.array([dnh4,dno3,do2,0.0],float)
