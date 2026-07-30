# -*- coding: utf-8 -*-
"""
Generic shared physical plant interface for the LNU-LNU MRAC examples.

This file contains no concrete physical model setup. It only loads the active
model file from plant_models/ and provides common simulation helpers used by
scripts 01 and 03.

Every file plant_models/<plant_model_name>.py must provide:

    default_params()
    initial_state(par)
    rhs(t_local, chi, u_const, par)
    algebraic_outputs(chi, par)

The parameter object is model-specific and is created inside the selected model
file. New plants can therefore be added by creating a new file in plant_models/
and selecting its filename in project_setup.py.
"""

from functools import lru_cache
from importlib import import_module
from pathlib import Path
import os
import sys
# Ensure the project root is importable even when this module is launched
# from apps/simulated by a GUI subprocess.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from scipy.integrate import solve_ivp



PLANT_DISPLAY_NAMES = {
    "two_mass_actuator_grounded_m2_lugre": "Two-mass mechanical system with LuGre friction",
    "two_mass_actuator_grounded_m2_lugre2": "Two-mass mechanical system with stronger LuGre friction",
    "two_mass_actuator_grounded_m2_linear_viscous": "Two-mass mechanical system with viscous damping",
    "bioreactor_dissolved_oxygen": "Bioreactor dissolved-oxygen control",
    "photobioreactor_ph_co2": "Photobioreactor pH control by CO2 dosing",
    "chemostat_monod_biomass": "Monod chemostat biomass control",
    "drug_infusion_pk": "Nonlinear drug-infusion pharmacokinetic system",
    "drug_infusion_pkpd": "Drug-infusion pharmacokinetic-pharmacodynamic system",
    "glucose_insulin_bergman": "Bergman glucose-insulin system",
    "quadrotor_altitude": "Quadrotor altitude-control system",
    "quadrotor_roll": "Quadrotor roll-control system",
    "peltier_thermal_asymmetric": "Asymmetric Peltier thermal system",
    "bidirectional_tank_level": "Bidirectional-pump nonlinear tank",
}

# Model-specific signal definitions. The common MRAC interface is always
# t, u, y. Remaining signals are diagnostics in physical units.
PLANT_SIGNAL_METADATA = {
    "two_mass_actuator_grounded_m2_lugre": {
        "input": ("u", "Actuator command", "-"), "output": ("y2", "Mass 2 displacement", "m"),
        "signals": [("y1", "Mass 1 displacement", "m"), ("dy1", "Mass 1 velocity", "m/s"),
                    ("dy2", "Mass 2 velocity", "m/s"), ("F1", "Actuator force", "N"),
                    ("F2", "Coupling force", "N"), ("z_f", "LuGre internal state", "m"),
                    ("F_f", "Friction force", "N")],
    },
    "two_mass_actuator_grounded_m2_linear_viscous": {
        "input": ("u", "Actuator command", "-"), "output": ("y2", "Mass 2 displacement", "m"),
        "signals": [("y1", "Mass 1 displacement", "m"), ("dy1", "Mass 1 velocity", "m/s"),
                    ("dy2", "Mass 2 velocity", "m/s"), ("F1", "Actuator force", "N"),
                    ("F2", "Coupling force", "N"), ("F_f", "Viscous friction force", "N")],
    },
    "bioreactor_dissolved_oxygen": {
        "input": ("u", "Agitation command", "-"), "output": ("C_O2_deviation", "Dissolved oxygen deviation", "concentration"),
        "signals": [("C_O2", "Dissolved oxygen", "concentration"), ("biomass", "Biomass concentration", "concentration"),
                    ("agitation", "Agitation speed", "rpm"), ("kla", "Oxygen transfer coefficient", "1/s"),
                    ("OUR", "Oxygen uptake rate", "concentration/s")],
    },
    "photobioreactor_ph_co2": {
        "input": ("u", "CO2 dosing command", "-"), "output": ("pH_deviation", "pH deviation", "pH"),
        "signals": [("pH", "pH", "pH"), ("CO2", "Dissolved CO2", "concentration"),
                    ("biomass", "Biomass concentration", "concentration"), ("CO2_flow", "CO2 flow", "flow"),
                    ("light", "Light intensity", "a.u.")],
    },
    "chemostat_monod_biomass": {
        "input": ("u", "Dilution-rate command", "-"), "output": ("biomass_deviation", "Biomass deviation", "concentration"),
        "signals": [("biomass", "Biomass concentration", "concentration"), ("substrate", "Substrate concentration", "concentration"),
                    ("dilution", "Dilution rate", "1/s"), ("growth_rate", "Specific growth rate", "1/s")],
    },
    "drug_infusion_pk": {
        "input": ("u", "Infusion command", "-"), "output": ("central_concentration_deviation", "Central concentration deviation", "concentration"),
        "signals": [("central_concentration", "Central concentration", "concentration"),
                    ("peripheral_concentration", "Peripheral concentration", "concentration"),
                    ("infusion_rate", "Infusion rate", "dose/s"), ("elimination", "Elimination rate", "dose/s")],
    },
    "drug_infusion_pkpd": {
        "input": ("u", "Infusion command", "-"), "output": ("effect_deviation", "Pharmacodynamic effect deviation", "-"),
        "signals": [("central_concentration", "Central concentration", "concentration"),
                    ("peripheral_concentration", "Peripheral concentration", "concentration"),
                    ("effect_concentration", "Effect-site concentration", "concentration"),
                    ("infusion_rate", "Infusion rate", "dose/s"), ("effect", "Pharmacodynamic effect", "-")],
    },
    "glucose_insulin_bergman": {
        "input": ("u", "Insulin-infusion command", "-"), "output": ("glucose_deviation", "Glucose deviation", "mg/dL"),
        "signals": [("glucose", "Plasma glucose", "mg/dL"), ("insulin", "Plasma insulin", "mU/L"),
                    ("remote_insulin_effect", "Remote insulin effect", "1/s"),
                    ("infusion_rate", "Insulin infusion rate", "mU/s"),
                    ("meal_disturbance", "Meal disturbance", "mg/dL/s")],
    },
    "quadrotor_altitude": {
        "input": ("u", "Collective-thrust command", "-"), "output": ("altitude", "Altitude", "m"),
        "signals": [("vertical_velocity", "Vertical velocity", "m/s"), ("thrust", "Collective thrust", "N"),
                    ("mass", "Vehicle mass", "kg")],
    },
    "quadrotor_roll": {
        "input": ("u", "Roll-torque command", "-"), "output": ("roll", "Roll angle", "rad"),
        "signals": [("roll_rate", "Roll rate", "rad/s"), ("torque", "Roll torque", "N m"),
                    ("inertia", "Roll inertia", "kg m^2")],
    },
    "peltier_thermal_asymmetric": {
        "input": ("u", "Signed current command", "-"),
        "output": ("temperature_deviation", "Controlled-plate temperature deviation", "deg C"),
        "signals": [("temperature_hot", "Controlled-plate temperature", "deg C"),
                    ("temperature_cold", "Heat-sink temperature", "deg C"),
                    ("current", "Peltier current", "A"),
                    ("peltier_heat", "Peltier heat rate", "W"),
                    ("joule_heat", "Joule heat rate", "W")],
    },
    "bidirectional_tank_level": {
        "input": ("u", "Bidirectional pump command", "-"),
        "output": ("level_deviation", "Tank-level deviation", "m"),
        "signals": [("level", "Liquid level", "m"),
                    ("pump_flow", "Signed pump flow", "m^3/s"),
                    ("gravity_outflow", "Gravity outflow", "m^3/s"),
                    ("net_flow", "Net tank flow", "m^3/s")],
    },
}


PLANT_SIGNAL_SYMBOLS = {
    "two_mass_actuator_grounded_m2_lugre": {
        "u": "u", "y": "y2", "y1": "y1", "dy1": "v1", "dy2": "v2",
        "F1": "F1", "F2": "F2", "z_f": "zf", "F_f": "Ff",
    },
    "two_mass_actuator_grounded_m2_linear_viscous": {
        "u": "u", "y": "y2", "y1": "y1", "dy1": "v1", "dy2": "v2",
        "F1": "F1", "F2": "F2", "F_f": "Ff",
    },
    "bioreactor_dissolved_oxygen": {
        "u": "u", "y": "CO2", "C_O2": "CO2", "biomass": "X",
        "agitation": "N", "kla": "kLa", "OUR": "qO2",
    },
    "photobioreactor_ph_co2": {
        "u": "u", "y": "pH", "pH": "pH", "CO2": "CCO2",
        "biomass": "X", "CO2_flow": "QCO2", "light": "I",
    },
    "chemostat_monod_biomass": {
        "u": "u", "y": "X", "biomass": "X", "substrate": "S",
        "dilution": "D", "growth_rate": "mu",
    },
    "drug_infusion_pk": {
        "u": "u", "y": "C1", "central_concentration": "C1",
        "peripheral_concentration": "C2", "infusion_rate": "Rin",
        "elimination": "Rel",
    },
    "drug_infusion_pkpd": {
        "u": "u", "y": "E", "central_concentration": "C1",
        "peripheral_concentration": "C2", "effect_concentration": "Ce",
        "infusion_rate": "Rin", "effect": "E",
    },
    "glucose_insulin_bergman": {
        "u": "u", "y": "G", "glucose": "G", "insulin": "I",
        "remote_insulin_effect": "X", "infusion_rate": "Ri",
        "meal_disturbance": "Dm",
    },
    "quadrotor_altitude": {
        "u": "u", "y": "h", "vertical_velocity": "v", "thrust": "T",
        "mass": "m",
    },
    "quadrotor_roll": {
        "u": "u", "y": "phi", "roll_rate": "omega", "torque": "tau",
        "inertia": "J",
    },
    "peltier_thermal_asymmetric": {
        "u": "u", "y": "DeltaT", "temperature_hot": "Th",
        "temperature_cold": "Tc", "current": "I",
        "peltier_heat": "QP", "joule_heat": "QJ",
    },
    "bidirectional_tank_level": {
        "u": "u", "y": "Deltah", "level": "h", "pump_flow": "qp",
        "gravity_outflow": "qout", "net_flow": "qnet",
    },
}




# LuGre 2 uses the same physical signals and plotting symbols as LuGre 1.
PLANT_SIGNAL_METADATA["two_mass_actuator_grounded_m2_lugre2"] = dict(
    PLANT_SIGNAL_METADATA["two_mass_actuator_grounded_m2_lugre"]
)
PLANT_SIGNAL_SYMBOLS["two_mass_actuator_grounded_m2_lugre2"] = dict(
    PLANT_SIGNAL_SYMBOLS["two_mass_actuator_grounded_m2_lugre"]
)

# Additional cross-domain SISO ODE benchmark models.
PLANT_DISPLAY_NAMES.update({
    "network_router_fluid_queue": "Network router fluid queue",
    "cloud_server_workload": "Cloud server workload and response time",
    "cpu_thermal_fan": "CPU thermal control by fan",
    "wireless_power_snr": "Wireless transmit-power and SNR control",
    "accelerator_rf_cavity_amplitude": "Accelerator RF-cavity amplitude control",
    "accelerator_beam_position": "Accelerator transverse beam-position control",
    "microgrid_frequency_linear": "Linear microgrid frequency control",
    "microgrid_frequency_bess_nonlinear": "Nonlinear microgrid frequency control with BESS",
    "soil_moisture_respiration": "Soil moisture and microbial respiration",
    "soil_microbe_carbon_respiration": "Soil microbial carbon respiration",
    "soil_carbon_priming": "Soil carbon priming effect",
    "soil_nitrogen_n2o": "Soil nitrogen transformation and N2O emission",
    "soil_denitrification_aeration": "Soil denitrification controlled by aeration",
    "soil_microbe_cn_stoichiometry": "Soil microbial C-N stoichiometric limitation",
    "mechanical_tuned_mass_damper": "Mechanical structure with tuned-mass vibration absorber",
    "voice_coil_servo": "Voice-coil electromechanical position servo",
    "overhead_crane_payload_sway": "Overhead crane payload-position and anti-sway dynamics",
})

PLANT_SIGNAL_METADATA.update({
    "network_router_fluid_queue": {
        "input": ("u", "Admission-rate command", "-"),
        "output": ("queue_deviation", "Queue occupancy deviation", "packets"),
        "signals": [("queue", "Queue occupancy", "packets"), ("admitted_rate", "Admitted traffic rate", "packets/s"),
                    ("service_rate", "Service rate", "packets/s"), ("delay", "Queueing-delay proxy", "s")],
    },
    "cloud_server_workload": {
        "input": ("u", "Compute-capacity command", "-"),
        "output": ("latency_deviation", "Response-time deviation", "s"),
        "signals": [("backlog", "Pending workload", "jobs"), ("allocated_capacity", "Allocated compute capacity", "jobs/s"),
                    ("service_rate", "Completed workload rate", "jobs/s"), ("response_time", "Response-time proxy", "s")],
    },
    "cpu_thermal_fan": {
        "input": ("u", "Signed thermal command", "-"),
        "output": ("temperature_deviation", "Chip-temperature deviation", "deg C"),
        "signals": [("temperature", "Chip temperature", "deg C"), ("fan_speed", "Normalized fan speed", "-"),
                    ("chip_power", "Chip heat generation", "W"), ("cooling_power", "Cooling heat flow", "W")],
    },
    "wireless_power_snr": {
        "input": ("u", "Transmit-power command", "-"),
        "output": ("snr_deviation", "SNR deviation", "-"),
        "signals": [("transmit_power", "Transmit power", "a.u."), ("snr", "Effective SNR", "-"),
                    ("throughput", "Shannon-rate proxy", "bit/s/Hz"), ("interference", "Noise and interference", "a.u.")],
    },
    "accelerator_rf_cavity_amplitude": {
        "input": ("u", "RF-drive command", "-"),
        "output": ("field_deviation", "Cavity-field amplitude deviation", "a.u."),
        "signals": [("field_amplitude", "Cavity-field amplitude", "a.u."), ("rf_drive", "RF amplifier output", "a.u."),
                    ("beam_loading", "Beam-loading term", "a.u."), ("detuning_loss", "Nonlinear detuning loss", "a.u.")],
    },
    "accelerator_beam_position": {
        "input": ("u", "Corrector-magnet command", "-"),
        "output": ("position", "Transverse beam position", "m"),
        "signals": [("beam_velocity", "Transverse beam velocity", "m/s"), ("magnet_field", "Corrector field", "a.u."),
                    ("restoring_force", "Effective restoring term", "m/s^2")],
    },
    "microgrid_frequency_linear": {
        "input": ("u", "Governor power command", "-"),
        "output": ("frequency_deviation", "Grid-frequency deviation", "Hz"),
        "signals": [("governor_output", "Governor output", "pu"), ("mechanical_power", "Diesel mechanical power", "pu"),
                    ("load_disturbance", "Load disturbance", "pu"), ("frequency_hz", "Grid frequency", "Hz")],
    },
    "soil_moisture_respiration": {"input": ("u", "Irrigation command", "-"), "output": ("respiration_deviation", "CO2-flux deviation", "a.u."), "signals": [("soil_moisture", "Volumetric soil moisture", "-"), ("available_carbon", "Available carbon", "a.u."), ("co2_flux", "Soil CO2 flux", "a.u./s"), ("moisture_activity", "Moisture activity factor", "-")]},
    "soil_microbe_carbon_respiration": {"input": ("u", "Labile-carbon addition command", "-"), "output": ("respiration_deviation", "CO2-flux deviation", "a.u."), "signals": [("labile_carbon", "Labile carbon pool", "a.u."), ("microbial_biomass", "Microbial biomass", "a.u."), ("carbon_uptake", "Microbial carbon uptake", "a.u./s"), ("co2_flux", "Soil CO2 flux", "a.u./s")]},
    "soil_carbon_priming": {"input": ("u", "Fresh-carbon addition command", "-"), "output": ("respiration_deviation", "CO2-flux deviation", "a.u."), "signals": [("labile_carbon", "Labile carbon pool", "a.u."), ("stable_carbon", "Stable soil carbon pool", "a.u."), ("microbial_biomass", "Microbial biomass", "a.u."), ("priming_factor", "Priming multiplier", "-"), ("co2_flux", "Soil CO2 flux", "a.u./s")]},
    "soil_nitrogen_n2o": {"input": ("u", "Soil aeration command", "-"), "output": ("n2o_deviation", "N2O-flux deviation", "a.u."), "signals": [("ammonium", "Ammonium pool", "a.u."), ("nitrate", "Nitrate pool", "a.u."), ("oxygen", "Soil oxygen availability", "-"), ("nitrification_rate", "Nitrification rate", "a.u./s"), ("denitrification_rate", "Denitrification rate", "a.u./s"), ("n2o_flux", "N2O flux", "a.u./s")]},
    "soil_denitrification_aeration": {"input": ("u", "Aeration command", "-"), "output": ("n2o_deviation", "N2O-flux deviation", "a.u."), "signals": [("nitrate", "Nitrate pool", "a.u."), ("available_carbon", "Available carbon", "a.u."), ("oxygen", "Soil oxygen availability", "-"), ("denitrification_rate", "Denitrification rate", "a.u./s"), ("n2o_flux", "N2O flux", "a.u./s")]},
    "soil_microbe_cn_stoichiometry": {"input": ("u", "Carbon-addition command", "-"), "output": ("respiration_deviation", "CO2-flux deviation", "a.u."), "signals": [("available_carbon", "Available carbon", "a.u."), ("available_nitrogen", "Available nitrogen", "a.u."), ("microbial_biomass", "Microbial biomass", "a.u."), ("limitation_ratio", "C-to-N limitation ratio", "-"), ("co2_flux", "Soil CO2 flux", "a.u./s")]},
    "mechanical_tuned_mass_damper": {
        "input": ("u", "Actuator-force command", "-"),
        "output": ("primary_displacement", "Primary-structure displacement", "m"),
        "signals": [("primary_velocity", "Primary-structure velocity", "m/s"),
                    ("absorber_displacement", "Absorber displacement", "m"),
                    ("absorber_velocity", "Absorber velocity", "m/s"),
                    ("relative_displacement", "Absorber relative displacement", "m"),
                    ("actuator_force", "Actuator force", "N"),
                    ("absorber_force", "Absorber coupling force", "N"),
                    ("primary_restoring_force", "Primary restoring force", "N")],
    },
    "voice_coil_servo": {
        "input": ("u", "Drive-voltage command", "-"),
        "output": ("position", "Carriage position", "m"),
        "signals": [("velocity", "Carriage velocity", "m/s"),
                    ("coil_current", "Voice-coil current", "A"),
                    ("drive_voltage", "Amplifier output voltage", "V"),
                    ("electromagnetic_force", "Electromagnetic force", "N"),
                    ("friction_force", "Friction force", "N")],
    },
    "overhead_crane_payload_sway": {
        "input": ("u", "Trolley-drive command", "-"),
        "output": ("payload_position", "Horizontal payload position", "m"),
        "signals": [("trolley_position", "Trolley position", "m"),
                    ("trolley_velocity", "Trolley velocity", "m/s"),
                    ("sway_angle", "Payload sway angle", "rad"),
                    ("sway_rate", "Payload sway rate", "rad/s"),
                    ("payload_vertical_position", "Payload vertical position", "m"),
                    ("drive_force", "Trolley drive force", "N"),
                    ("end_stop_force", "Travel-limit force", "N")],
    },
    "microgrid_frequency_bess_nonlinear": {
        "input": ("u", "BESS power command", "-"),
        "output": ("frequency_deviation", "Grid-frequency deviation", "Hz"),
        "signals": [("governor_output", "Governor output", "pu"), ("diesel_power", "Diesel mechanical power", "pu"),
                    ("bess_power", "BESS power", "pu"), ("state_of_charge", "Battery state of charge", "-"),
                    ("load_disturbance", "Load disturbance", "pu"), ("frequency_hz", "Grid frequency", "Hz")],
    },
})

PLANT_SIGNAL_SYMBOLS.update({
    "network_router_fluid_queue": {"u":"u", "y":"Deltaq", "queue":"q", "admitted_rate":"rin", "service_rate":"rout", "delay":"tauq"},
    "cloud_server_workload": {"u":"u", "y":"Deltatau", "backlog":"x", "allocated_capacity":"c", "service_rate":"mu", "response_time":"tau"},
    "cpu_thermal_fan": {"u":"u", "y":"DeltaT", "temperature":"T", "fan_speed":"nf", "chip_power":"P", "cooling_power":"Qc"},
    "wireless_power_snr": {"u":"u", "y":"Deltagamma", "transmit_power":"p", "snr":"gamma", "throughput":"R", "interference":"I"},
    "accelerator_rf_cavity_amplitude": {"u":"u", "y":"DeltaVc", "field_amplitude":"Vc", "rf_drive":"a", "beam_loading":"Ib", "detuning_loss":"Ld"},
    "accelerator_beam_position": {"u":"u", "y":"x", "beam_velocity":"vx", "magnet_field":"Bm", "restoring_force":"Fr"},
    "microgrid_frequency_linear": {"u":"u", "y":"Deltaf", "governor_output":"Pg", "mechanical_power":"Pm", "load_disturbance":"PL", "frequency_hz":"f"},
    "soil_moisture_respiration": {"u":"u", "y":"DeltaRco2", "soil_moisture":"theta", "available_carbon":"Cs", "co2_flux":"Rco2", "moisture_activity":"ftheta"},
    "soil_microbe_carbon_respiration": {"u":"u", "y":"DeltaRco2", "labile_carbon":"Cs", "microbial_biomass":"B", "carbon_uptake":"ru", "co2_flux":"Rco2"},
    "soil_carbon_priming": {"u":"u", "y":"DeltaRco2", "labile_carbon":"CL", "stable_carbon":"CS", "microbial_biomass":"B", "priming_factor":"fp", "co2_flux":"Rco2"},
    "soil_nitrogen_n2o": {"u":"u", "y":"DeltaFN2O", "ammonium":"NH4", "nitrate":"NO3", "oxygen":"O2", "nitrification_rate":"rnit", "denitrification_rate":"rden", "n2o_flux":"FN2O"},
    "soil_denitrification_aeration": {"u":"u", "y":"DeltaFN2O", "nitrate":"NO3", "available_carbon":"C", "oxygen":"O2", "denitrification_rate":"rden", "n2o_flux":"FN2O"},
    "soil_microbe_cn_stoichiometry": {"u":"u", "y":"DeltaRco2", "available_carbon":"C", "available_nitrogen":"N", "microbial_biomass":"B", "limitation_ratio":"rhoCN", "co2_flux":"Rco2"},
    "mechanical_tuned_mass_damper": {"u":"u", "y":"xp", "primary_velocity":"vp", "absorber_displacement":"xa", "absorber_velocity":"va", "relative_displacement":"xr", "actuator_force":"Fa", "absorber_force":"Ftmd", "primary_restoring_force":"Fp"},
    "voice_coil_servo": {"u":"u", "y":"x", "velocity":"v", "coil_current":"i", "drive_voltage":"Va", "electromagnetic_force":"Fem", "friction_force":"Ff"},
    "overhead_crane_payload_sway": {"u":"u", "y":"xL", "trolley_position":"xT", "trolley_velocity":"vT", "sway_angle":"theta", "sway_rate":"omega", "payload_vertical_position":"yL", "drive_force":"Fd", "end_stop_force":"Fstop"},
    "microgrid_frequency_bess_nonlinear": {"u":"u", "y":"Deltaf", "governor_output":"Pg", "diesel_power":"Pm", "bess_power":"Pb", "state_of_charge":"z", "load_disturbance":"PL", "frequency_hz":"f"},
})


# Delayed-input ODE benchmark variants. The delay is implemented inside each
# plant as a finite-dimensional cascaded-lag transport approximation.
_DELAYED_VARIANTS = {
    "network_router_fluid_queue_with_delay": ("network_router_fluid_queue", "Network Router Fluid Queue With Delay", 0.35),
    "network_router_fluid_queue_with_large_delay": ("network_router_fluid_queue", "Network Router Fluid Queue With Large Delay", 1.5),
    "cloud_server_workload_with_delay": ("cloud_server_workload", "Cloud Server Workload With Delay", 8.0),
    "microgrid_frequency_bess_nonlinear_with_delay": ("microgrid_frequency_bess_nonlinear", "Microgrid Frequency Bess Nonlinear With Delay", 0.3),
    "soil_moisture_respiration_with_delay": ("soil_moisture_respiration", "Soil Moisture Respiration With Delay", 4.0),
    "soil_carbon_priming_with_delay": ("soil_carbon_priming", "Soil Carbon Priming With Delay", 6.0),
    "accelerator_rf_cavity_amplitude_with_delay": ("accelerator_rf_cavity_amplitude", "Accelerator Rf Cavity Amplitude With Delay", 0.004),
    "overhead_crane_payload_sway_with_delay": ("overhead_crane_payload_sway", "Overhead Crane Payload Sway With Delay", 0.12),
}
for _name, (_base, _display, _delay) in _DELAYED_VARIANTS.items():
    PLANT_DISPLAY_NAMES[_name] = _display
    _meta = dict(PLANT_SIGNAL_METADATA[_base])
    _meta["signals"] = list(_meta["signals"]) + [
        ("effective_input", "Delayed effective input", "-"),
        ("input_delay_sec", "Nominal input delay", "s"),
    ]
    PLANT_SIGNAL_METADATA[_name] = _meta
    _symbols = dict(PLANT_SIGNAL_SYMBOLS[_base])
    _symbols.update({"effective_input": "u_d", "input_delay_sec": "tau_d"})
    PLANT_SIGNAL_SYMBOLS[_name] = _symbols

def plant_display_name(model_name):
    """Return the user-visible title of a physical plant model."""
    return PLANT_DISPLAY_NAMES.get(
        str(model_name), str(model_name).replace("_", " ").strip().title()
    )


def active_plant_display_name():
    """Return the title of the model selected in project_setup.py."""
    from project_setup import plant_model_name
    return plant_display_name(plant_model_name)



def plant_signal_symbol(model_name, key):
    """Return a compact axis symbol for a model signal."""
    return PLANT_SIGNAL_SYMBOLS.get(str(model_name), {}).get(str(key), str(key))


def plant_signal_metadata(model_name):
    if model_name not in PLANT_SIGNAL_METADATA:
        raise KeyError(f"Missing signal metadata for plant model {model_name!r}")
    return PLANT_SIGNAL_METADATA[model_name]


def controlled_output(chi, par):
    model_name = par.plant_model_name
    out = algebraic_outputs(chi, par)
    key = plant_signal_metadata(model_name)["output"][0]
    if key in out:
        return float(out[key])
    # Backward-compatible fallback while model modules are migrated.
    return float(out["y2"])


def signal_columns(model_name):
    meta = plant_signal_metadata(model_name)
    return ["t", "u", "y"] + [item[0] for item in meta["signals"]]


def signal_labels(model_name):
    meta = plant_signal_metadata(model_name)
    return [meta["input"], meta["output"]] + meta["signals"]


@lru_cache(maxsize=1)
def available_models():
    models_dir = Path(__file__).resolve().parent / "plant_models"
    if not models_dir.exists():
        return tuple()
    names = []
    for file_path in sorted(models_dir.glob("*.py")):
        if file_path.name.startswith("_"):
            continue
        if file_path.stem == "__init__":
            continue
        names.append(file_path.stem)
    return tuple(names)


@lru_cache(maxsize=None)
def load_model(model_name):
    if model_name not in available_models():
        raise ValueError(
            "Unknown plant_model_name: " + str(model_name)
            + ". Available models: " + str(available_models())
        )
    return import_module("plant_models." + model_name)


def default_params(model_name):
    model = load_model(model_name)
    if not hasattr(model, "default_params"):
        raise AttributeError(
            "Plant model " + str(model_name) + " must define default_params()."
        )
    par = model.default_params()
    if not hasattr(par, "plant_model_name"):
        par.plant_model_name = model_name
    return par


def _model_from_par(par):
    return load_model(par.plant_model_name)


def initial_state(par):
    return _model_from_par(par).initial_state(par)


def algebraic_outputs(chi, par):
    return _model_from_par(par).algebraic_outputs(chi, par)


def plant_rhs(t_local, chi, u_const, par):
    return _model_from_par(par).rhs(t_local, chi, u_const, par)


def _internal_step(dt_sample, solver):
    """Maximum fixed RK4 substep, independent of the sampled-data period."""
    configured = getattr(solver, "dt_ode", None)
    if configured is None:
        configured = getattr(solver, "dt_sim", None)
    if configured is not None:
        max_step = min(float(configured), float(dt_sample))
    else:
        max_step = float(dt_sample) * float(getattr(solver, "max_step_factor", 0.1))
    return max(max_step, 1.0e-12)


_STIFF_ODE_MODELS = {
    "two_mass_actuator_grounded_m2_lugre",
    "two_mass_actuator_grounded_m2_lugre2",
}
_ADAPTIVE_METHODS = {"radau": "Radau", "bdf": "BDF", "lsoda": "LSODA", "rk45": "RK45", "dop853": "DOP853"}


def _selected_ode_method(par, solver):
    requested = str(getattr(solver, "method", "auto") or "auto").strip().lower()
    if requested == "auto":
        return "Radau" if str(par.plant_model_name) in _STIFF_ODE_MODELS else "RK45"
    if requested == "rk4":
        # Legacy fixed-step label maps to SciPy RK45 in the Python-only package.
        return "RK45"
    if requested in _ADAPTIVE_METHODS:
        return _ADAPTIVE_METHODS[requested]
    raise ValueError(f"Unsupported ODE solver method: {requested!r}")


def _adaptive_interval(chi, u_command, dt_sample, par, solver, preg=False, r_preg=1.0):
    """Accurate SciPy integration for stiff or explicitly adaptive models."""
    method = _selected_ode_method(par, solver)
    model = _model_from_par(par)
    u_command = float(u_command)

    if preg:
        def rhs(t_local, state):
            u_phys = float(r_preg) * (u_command - controlled_output(state, par))
            return np.asarray(model.rhs(t_local, state, u_phys, par), dtype=float)
    else:
        def rhs(t_local, state):
            return np.asarray(model.rhs(t_local, state, u_command, par), dtype=float)

    max_step = _internal_step(dt_sample, solver)
    sol = solve_ivp(
        rhs, (0.0, float(dt_sample)), np.asarray(chi, dtype=float),
        method=method,
        rtol=float(getattr(solver, "rtol", 1.0e-8)),
        atol=float(getattr(solver, "atol", 1.0e-10)),
        max_step=max_step,
        t_eval=[float(dt_sample)],
    )
    if not sol.success or sol.y.shape[1] == 0:
        raise RuntimeError(
            f"{method} failed for model '{par.plant_model_name}': {sol.message}"
        )
    state = np.asarray(sol.y[:, -1], dtype=float)
    if not np.all(np.isfinite(state)):
        raise FloatingPointError(
            f"{method} produced a non-finite state for model '{par.plant_model_name}'"
        )
    if preg:
        u_phys = float(r_preg) * (u_command - controlled_output(state, par))
        return state, u_phys
    return state, u_command


def simulate_sample_period_zoh(chi, u_const, dt_sample, par, solver):
    """Integrate one ZOH interval using the selected SciPy backend."""
    result = _adaptive_interval(chi, u_const, dt_sample, par, solver)
    return result[0]


def simulate_sample_period_preg(chi, u_new_const, dt_sample, par, solver, r_preg):
    """Integrate one interval with continuous inner P feedback in Python/SciPy."""
    return _adaptive_interval(
        chi, u_new_const, dt_sample, par, solver, preg=True, r_preg=r_preg
    )


def simulate_one_step(chi, u_const, dt_sample, par, solver):
    """Backward-compatible alias for simulate_sample_period_zoh()."""
    return simulate_sample_period_zoh(chi, u_const, dt_sample, par, solver)


def simulate_zoh(u, dt_sample, par, solver, chi0=None):
    u = np.asarray(u, dtype=float)
    n = len(u)
    if chi0 is None:
        chi = initial_state(par)
    else:
        chi = np.asarray(chi0, dtype=float).copy()

    n_state = len(chi)
    chi_mat = np.zeros((n, n_state), dtype=float)
    chi_mat[0, :] = chi

    for k in range(n - 1):
        chi = simulate_sample_period_zoh(chi, u[k], dt_sample, par, solver)
        chi_mat[k + 1, :] = chi

    return chi_mat


def output_table(t, u, chi_mat, par):
    """Return model-specific physical data with common leading columns t, u, y."""
    model_name = par.plant_model_name
    meta = plant_signal_metadata(model_name)
    columns = signal_columns(model_name)
    data = np.empty((len(t), len(columns)), dtype=float)
    data[:, 0] = np.asarray(t, dtype=float)
    data[:, 1] = np.asarray(u, dtype=float)
    output_key = meta["output"][0]
    for k in range(len(t)):
        out = algebraic_outputs(chi_mat[k, :], par)
        data[k, 2] = float(out.get(output_key, out.get("y2", np.nan)))
        for j, (key, _label, _unit) in enumerate(meta["signals"], start=3):
            data[k, j] = float(out.get(key, np.nan))
    return data, columns
