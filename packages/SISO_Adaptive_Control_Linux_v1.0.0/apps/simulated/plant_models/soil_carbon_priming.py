# -*- coding: utf-8 -*-
"""Labile-carbon induced priming of stable soil organic matter."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "soil_carbon_priming"
    labile_nom: float = 0.35
    stable_nom: float = 3.0
    biomass_nom: float = 0.28
    k_labile: float = 0.22
    k_stable: float = 0.010
    half_labile: float = 0.20
    half_stable: float = 1.0
    priming_strength: float = 2.2
    priming_half: float = 0.30
    yield_labile: float = 0.48
    yield_stable: float = 0.32
    mortality: float = 0.055
    feed_nom: float = 0.030
    feed_gain: float = 0.025
    respiration_nom: float = 0.028

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.labile_nom, par.stable_nom, par.biomass_nom, 0.0], float)
def _rates(cl, cs, b, par):
    clp, csp, bp = max(cl,0.0), max(cs,0.0), max(b,0.0)
    rl = par.k_labile*bp*clp/(par.half_labile+clp+1e-12)
    prime = 1.0+par.priming_strength*clp/(par.priming_half+clp+1e-12)
    rs = par.k_stable*prime*bp*csp/(par.half_stable+csp+1e-12)
    return rl, rs, prime
def algebraic_outputs(chi, par):
    cl, cs, b = chi[:3]
    rl, rs, prime = _rates(cl,cs,b,par)
    respiration = (1-par.yield_labile)*rl+(1-par.yield_stable)*rs+0.35*par.mortality*max(b,0.0)
    return {"respiration_deviation": respiration-par.respiration_nom,
            "labile_carbon": cl, "stable_carbon": cs, "microbial_biomass": b,
            "priming_factor": prime, "co2_flux": respiration}
def rhs(t, chi, u, par):
    cl, cs, b = chi[:3]
    rl, rs, prime = _rates(cl,cs,b,par)
    mortality = par.mortality*max(b,0.0)
    feed = par.feed_nom+par.feed_gain*np.tanh(float(u))
    return np.array([feed-rl, -rs, par.yield_labile*rl+par.yield_stable*rs-mortality, 0.0], float)
