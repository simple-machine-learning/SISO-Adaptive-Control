# -*- coding: utf-8 -*-
"""Aeration-controlled soil denitrification and N2O flux benchmark."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_denitrification_aeration"
    nitrate_nom: float = 0.90
    carbon_nom: float = 0.75
    oxygen_nom: float = 0.35
    den_rate: float = 0.14
    k_nitrate: float = 0.35
    k_carbon: float = 0.30
    oxygen_inhibition: float = 0.16
    nitrate_input: float = 0.045
    carbon_input: float = 0.035
    carbon_decay: float = 0.020
    oxygen_tau: float = 1.2
    aeration_gain: float = 0.38
    n2o_fraction: float = 0.30
    n2o_nom: float = 0.018

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.nitrate_nom,par.carbon_nom,par.oxygen_nom,0.0],float)
def _rate(n,c,o,par):
    n,c,o=max(n,0.0),max(c,0.0),max(o,0.0)
    return par.den_rate*n/(par.k_nitrate+n+1e-12)*c/(par.k_carbon+c+1e-12)*par.oxygen_inhibition/(par.oxygen_inhibition+o+1e-12)
def algebraic_outputs(chi,par):
    n,c,o=chi[:3]; r=_rate(n,c,o,par); flux=par.n2o_fraction*r
    return {"n2o_deviation":flux-par.n2o_nom,"nitrate":n,"available_carbon":c,
            "oxygen":o,"denitrification_rate":r,"n2o_flux":flux}
def rhs(t,chi,u,par):
    n,c,o=chi[:3]; r=_rate(n,c,o,par)
    oeq=np.clip(par.oxygen_nom+par.aeration_gain*np.tanh(float(u)),0.02,1.0)
    return np.array([par.nitrate_input-r,par.carbon_input-r-par.carbon_decay*max(c,0.0),
                     (oeq-o)/par.oxygen_tau-0.12*r,0.0],float)
