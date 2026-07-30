# -*- coding: utf-8 -*-
"""Aggregate cloud-server backlog with saturating service and actuator lag."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "cloud_server_workload"
    backlog_nom: float = 8.0
    arrival_rate: float = 5.0
    service_nom: float = 5.0
    service_gain: float = 3.0
    tau_capacity: float = 1.5
    half_saturation: float = 2.0
    abandonment: float = 0.03
    latency_gain: float = 0.18

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.backlog_nom, par.service_nom, 0.0], float)
def algebraic_outputs(chi, par):
    x, c = chi[:2]
    service = c*x/(par.half_saturation+max(x,0.0))
    latency = par.latency_gain*x
    return {"latency_deviation": latency-par.latency_gain*par.backlog_nom,
            "backlog": x, "allocated_capacity": c, "service_rate": service,
            "response_time": latency}
def rhs(t, chi, u, par):
    x, c = chi[:2]
    c_cmd = par.service_nom + par.service_gain*np.tanh(float(u))
    service = max(c,0.0)*max(x,0.0)/(par.half_saturation+max(x,0.0))
    dx = par.arrival_rate-service-par.abandonment*x
    if x <= 0.0 and dx < 0.0: dx = 0.0
    return np.array([dx, (c_cmd-c)/par.tau_capacity, 0.0], float)
