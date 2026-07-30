# -*- coding: utf-8 -*-
"""Carbon-nitrogen co-limitation with smooth stoichiometric limitation."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_microbe_cn_stoichiometry"
    carbon_nom: float = 1.0
    nitrogen_nom: float = 0.45
    biomass_nom: float = 0.25
    carbon_rate: float = 0.16
    nitrogen_rate: float = 0.10
    k_carbon: float = 0.35
    k_nitrogen: float = 0.20
    biomass_cn: float = 6.0
    mortality: float = 0.040
    carbon_input_nom: float = 0.042
    carbon_input_gain: float = 0.030
    nitrogen_input: float = 0.013
    smooth_beta: float = 18.0
    respiration_nom: float = 0.030

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.carbon_nom,par.nitrogen_nom,par.biomass_nom,0.0],float)
def _smin(a,b,beta):
    m=min(a,b)
    return m-np.log(np.exp(-beta*(a-m))+np.exp(-beta*(b-m)))/beta
def _rates(c,n,b,par):
    c,n,b=max(c,0.0),max(n,0.0),max(b,0.0)
    uc=par.carbon_rate*b*c/(par.k_carbon+c+1e-12)
    un=par.nitrogen_rate*b*n/(par.k_nitrogen+n+1e-12)
    growth=max(_smin(0.48*uc,par.biomass_cn*un,par.smooth_beta),0.0)
    return uc,un,growth
def algebraic_outputs(chi,par):
    c,n,b=chi[:3]; uc,un,g=_rates(c,n,b,par)
    respiration=max(uc-g,0.0)+0.35*par.mortality*max(b,0.0)
    ratio=(0.48*uc)/(par.biomass_cn*un+1e-12)
    return {"respiration_deviation":respiration-par.respiration_nom,"available_carbon":c,
            "available_nitrogen":n,"microbial_biomass":b,"limitation_ratio":ratio,
            "co2_flux":respiration}
def rhs(t,chi,u,par):
    c,n,b=chi[:3]; uc,un,g=_rates(c,n,b,par); mort=par.mortality*max(b,0.0)
    cin=par.carbon_input_nom+par.carbon_input_gain*np.tanh(float(u))
    return np.array([cin-uc+0.25*mort,par.nitrogen_input-un+0.15*mort/par.biomass_cn,g-mort,0.0],float)
