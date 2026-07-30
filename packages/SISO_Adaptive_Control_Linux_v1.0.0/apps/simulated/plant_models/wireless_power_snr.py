# -*- coding: utf-8 -*-
"""Envelope model of wireless transmit-power control and effective SNR."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PlantParams:
    plant_model_name: str = "wireless_power_snr"
    power_nom: float = 1.0
    power_gain: float = 0.8
    tau_power: float = 0.12
    channel_gain: float = 1.0
    noise_interference: float = 0.25
    tau_snr: float = 0.45
    snr_nom: float = 4.0
    bandwidth: float = 1.0

def default_params(): return PlantParams()
def initial_state(par): return np.array([par.power_nom, par.snr_nom, 0.0], float)
def algebraic_outputs(chi, par):
    p, snr = chi[:2]
    return {"snr_deviation": snr-par.snr_nom, "transmit_power": p,
            "snr": snr, "throughput": par.bandwidth*np.log2(1.0+max(snr,0.0)),
            "interference": par.noise_interference}
def rhs(t, chi, u, par):
    p, snr = chi[:2]
    p_cmd = max(0.0, par.power_nom+par.power_gain*np.tanh(float(u)))
    snr_eq = par.channel_gain*max(p,0.0)/par.noise_interference
    return np.array([(p_cmd-p)/par.tau_power, (snr_eq-snr)/par.tau_snr, 0.0], float)
