# -*- coding: utf-8 -*-
"""Generate training data from the selected physical ODE model.

Every model exports its own physical diagnostic quantities.  The first three
columns are invariant and form the complete MRAC data interface: t, u, y.
"""

# =============================================================================
# Setup
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt

from shared_plant_model import (
    algebraic_outputs, initial_state, simulate_sample_period_zoh,
    output_table,
    plant_display_name,
    plant_signal_metadata,
    plant_signal_symbol,
    simulate_zoh,
    simulate_sample_period_preg,
)
from simulated_normalization import fit_and_save
from signal_generation import block_step_signal
from project_setup import (
    dt, dt_sim, t_end, input_type, u_min, u_max, step_hold_sec, sine_freq_hz,
    random_seed, uy_file as out_file, uy_normalized_file,
    simulated_normalization_file, plant_par, solver_setup, line_width, font_size,
    preg_blackbox_enabled, r_preg,
)

# =============================================================================
# Time vector and excitation
# =============================================================================

t = np.arange(0.0, t_end + dt, dt)
if input_type in ("random_steps", "alternating_steps", "steps", "alternating", "random"):
    initial_u = 0.0 if float(u_min) <= 0.0 <= float(u_max) else 0.5 * (float(u_min) + float(u_max))
    u = block_step_signal(
        sample_count=t.size, dt=dt, low=float(u_min), high=float(u_max),
        hold_sec=step_hold_sec, mode=input_type, seed=random_seed, initial=initial_u,
    )
elif input_type == "sine":
    u_center = 0.5 * (float(u_min) + float(u_max))
    u_amplitude = 0.5 * (float(u_max) - float(u_min))
    u = u_center + u_amplitude * np.sin(2.0 * np.pi * sine_freq_hz * t)
else:
    raise ValueError(f"Unknown input_type: {input_type}")

# =============================================================================
# Physical simulation and model-specific table
# =============================================================================

meta = plant_signal_metadata(plant_par.plant_model_name)

if preg_blackbox_enabled:
    # u is the external input u_new of the new black-box plant.
    # The fixed P regulator is internal to the black box.
    chi_state = initial_state(plant_par)
    chi = np.zeros((len(t), len(chi_state)), dtype=float)
    chi[0, :] = chi_state
    output_key = meta["output"][0]
    u_phys = np.zeros_like(u)
    for k in range(len(t) - 1):
        chi_state, u_phys[k] = simulate_sample_period_preg(
            chi_state, u[k], dt, plant_par, solver_setup, r_preg
        )
        chi[k + 1, :] = chi_state
    if len(t) > 1:
        out = algebraic_outputs(chi_state, plant_par)
        y_current = float(out.get(output_key, out.get("y2", np.nan)))
        u_phys[-1] = float(r_preg) * (u[-1] - y_current)
else:
    chi = simulate_zoh(u, dt, plant_par, solver_setup)
    u_phys = u.copy()

data, columns = output_table(t, u, chi, plant_par)

parameter_text = ", ".join(
    f"{key}={value:g}" for key, value in vars(plant_par).items()
    if isinstance(value, (int, float))
)
header = (
    "\t".join(columns) + "\n"
    f"model_name={plant_par.plant_model_name}, controlled_output={meta['output'][0]}, "
    f"dt={dt:g} sec, dt_sim={dt_sim:g} sec, input_type={input_type}, "
    f"preg_blackbox_enabled={preg_blackbox_enabled}, r_preg={r_preg:g}, {parameter_text}"
)
np.savetxt(out_file, data, fmt="%.10e", delimiter="\t", header=header)
stats = fit_and_save(
    data, simulated_normalization_file, uy_normalized_file,
    columns=columns, model_name=plant_par.plant_model_name,
    metadata={
        "preg_blackbox_enabled": bool(preg_blackbox_enabled),
        "r_preg": float(r_preg),
        "dt": float(dt),
        "dt_sim": float(dt_sim),
    },
)

print(f"Plant model: {plant_display_name(plant_par.plant_model_name)}")
print("Columns:", ", ".join(columns))
print(f"Common MRAC channels: u_new={meta['input'][1]}, y={meta['output'][1]}")
if preg_blackbox_enabled:
    print(f"Internal P-regulated black box: u_phys = {r_preg:g} * (u_new - y)")
    print(f"Physical input range: [{np.min(u_phys):.6g}, {np.max(u_phys):.6g}]")
print(f"Saved physical data: {out_file}")
print(f"Saved normalized data: {uy_normalized_file}")
print(f"u_z = (u - {stats['mu_u']:.6g}) / {stats['scale_u']:.6g}")
print(f"y_z = (y - {stats['mu_y']:.6g}) / {stats['scale_y']:.6g}")

# =============================================================================
# Dynamic plots: one axis for each actual model quantity
# =============================================================================

if os.environ.get("HONU_GUI_NO_MPL") != "1":
    plot_columns = columns[1:]
    n_axes = len(plot_columns)
    fig_height = max(7.0, 2.0 * n_axes)
    fig, axes = plt.subplots(n_axes, 1, figsize=(14, fig_height), sharex=True)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(left=0.11, right=0.98, top=0.93, bottom=0.07, hspace=0.22)
    fig.suptitle(plant_display_name(plant_par.plant_model_name), fontsize=font_size + 2)

    label_by_key = {"u": meta["input"], "y": meta["output"]}
    label_by_key.update({key: (key, label, unit) for key, label, unit in meta["signals"]})
    for axis, key in zip(axes, plot_columns):
        index = columns.index(key)
        _symbol, label, unit = label_by_key[key]
        axis_symbol = plant_signal_symbol(plant_par.plant_model_name, key)
        color = "blue" if key == "y" else "black"
        axis.plot(t, data[:, index], color=color, linewidth=line_width)
        axis.set_ylabel(axis_symbol)
        axis.grid(True)
    axes[-1].set_xlabel(f"t [s], dt={dt:g} s, dt_sim={dt_sim:g} s")
    plt.show()
