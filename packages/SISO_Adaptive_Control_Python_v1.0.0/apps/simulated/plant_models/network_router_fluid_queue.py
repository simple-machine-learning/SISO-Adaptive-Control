# -*- coding: utf-8 -*-
"""Reduced fluid model of an actively controlled router queue.
State chi=[q,r], where q is buffer occupancy and r is admitted traffic rate.
The command u changes the admitted rate around the nominal link capacity.
"""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "network_router_fluid_queue"
    capacity: float = 12.0
    q_nom: float = 4.0
    q_scale: float = 3.0
    tau_rate: float = 0.35
    rate_gain: float = 4.0
    service_floor: float = 0.15
    leakage: float = 0.03
    q_max: float = 20.0

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.q_nom, par.capacity, 0.0], float)
def algebraic_outputs(chi, par):
    q, r = chi[:2]
    service = par.capacity * (par.service_floor + (1.0-par.service_floor)*(1.0-np.exp(-max(q,0.0)/par.q_scale)))
    return {"queue_deviation": q-par.q_nom, "queue": q, "admitted_rate": r,
            "service_rate": service, "delay": q/max(service,1.0e-9)}
def rhs(t, chi, u, par):
    q, r = chi[:2]
    r_cmd = par.capacity + par.rate_gain*np.tanh(float(u))
    service = par.capacity * (par.service_floor + (1.0-par.service_floor)*(1.0-np.exp(-max(q,0.0)/par.q_scale)))
    dq = r-service-par.leakage*q
    if q <= 0.0 and dq < 0.0: dq = 0.0
    if q >= par.q_max and dq > 0.0: dq = 0.0
    return np.array([dq, (r_cmd-r)/par.tau_rate, 0.0], float)
