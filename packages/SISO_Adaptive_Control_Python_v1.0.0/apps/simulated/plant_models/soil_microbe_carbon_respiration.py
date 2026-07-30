# -*- coding: utf-8 -*-
"""Substrate-microbial-biomass carbon respiration benchmark."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_microbe_carbon_respiration"
    substrate_nom: float = 1.2
    biomass_nom: float = 0.30
    vmax: float = 0.18
    k_substrate: float = 0.45
    yield_coeff: float = 0.42
    mortality: float = 0.045
    recycling: float = 0.35
    feed_nom: float = 0.054
    feed_gain: float = 0.030
    respiration_nom: float = 0.033

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.substrate_nom, par.biomass_nom, 0.0], float)
def _uptake(s, b, par): return par.vmax*max(b,0.0)*max(s,0.0)/(par.k_substrate+max(s,0.0)+1e-12)
def algebraic_outputs(chi, par):
    s, b = chi[:2]
    uptake = _uptake(s,b,par)
    maintenance = par.mortality*max(b,0.0)
    respiration = (1.0-par.yield_coeff)*uptake + (1.0-par.recycling)*maintenance
    return {"respiration_deviation": respiration-par.respiration_nom,
            "labile_carbon": s, "microbial_biomass": b,
            "carbon_uptake": uptake, "co2_flux": respiration}
def rhs(t, chi, u, par):
    s, b = chi[:2]
    uptake = _uptake(s,b,par)
    mortality = par.mortality*max(b,0.0)
    feed = par.feed_nom + par.feed_gain*np.tanh(float(u))
    ds = feed-uptake+par.recycling*mortality
    db = par.yield_coeff*uptake-mortality
    return np.array([ds, db, 0.0], float)
