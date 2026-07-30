# -*- coding: utf-8 -*-
"""
Central setup for HONU MRAC examples.

This file stores parameters and all file names. It does not launch modules 02, 03, or 04.
Run the desired script manually or use the GUI workflow buttons.
"""


# =============================================================================
# Shared measured dataset
# =============================================================================

data_source = "text"
uy_file = "data_uy.txt"
uy_normalized_file = "data/data_uy_normalized.txt"
simulated_normalization_file = "data/simulated_normalization.npz"

# GUI selections
gui_honu_plant = "LNU"
gui_controller_model = "LNU"

# Sampling period; updated from the imported record by the GUI.
dt = 0.01
t_end = 0.01
tau_u = 0.0
preg_blackbox_enabled = False
r_preg = 0.0

# =============================================================================
# Module 02: plant identification, common embedding setup
# =============================================================================

# These values are used by both LNU and QNU plant scripts.
# tau_u is defined once in the shared sampling section above so the GUI value
# cannot be shadowed by a second assignment.
plant_n_y = 5
plant_n_u = 5

# Select only the source of the already-trained plant file loaded by 03 scripts.
# The actual 02 script is still run manually.
# The HONU architecture is NOT selected here; it is defined by the 03 script name.
plant_training_method = "batch"# "batch" | "gd_ngd" | "lm"

# Trained plant files.
plant_lnu_file_batch = "plant_LNU_batch.txt"
plant_lnu_file_gd_ngd = "plant_LNU_gd_ngd.txt"
plant_qnu_file_batch = "plant_QNU_batch.txt"
plant_qnu_file_gd_ngd = "plant_QNU_gd_ngd.txt"
plant_lnu_file_lm = "plant_LNU_lm.txt"
plant_qnu_file_lm = "plant_QNU_lm.txt"

# Plant BIBS-monitoring files.
bibs_plant_lnu_file_batch = "bibs_plant_LNU_batch.txt"
bibs_plant_lnu_file_gd_ngd = "bibs_plant_LNU_gd_ngd.txt"
bibs_plant_qnu_file_batch = "bibs_plant_QNU_batch.txt"
bibs_plant_qnu_file_gd_ngd = "bibs_plant_QNU_gd_ngd.txt"
bibs_plant_lnu_file_lm = "bibs_plant_LNU_lm.txt"
bibs_plant_qnu_file_lm = "bibs_plant_QNU_lm.txt"
plant_lnu_lm_trace_file = "lm_trace_plant_LNU.txt"
plant_qnu_lm_trace_file = "lm_trace_plant_QNU.txt"

if plant_training_method == "batch":
    controller_lnu_plant_file = plant_lnu_file_batch
    controller_qnu_plant_file = plant_qnu_file_batch
elif plant_training_method == "gd_ngd":
    controller_lnu_plant_file = plant_lnu_file_gd_ngd
    controller_qnu_plant_file = plant_qnu_file_gd_ngd
elif plant_training_method == "lm":
    controller_lnu_plant_file = plant_lnu_file_lm
    controller_qnu_plant_file = plant_qnu_file_lm
else:
    raise ValueError("plant_training_method must be 'batch', 'gd_ngd', or 'lm'.")

# =============================================================================
# Module 02 batch Ridge plant identification
# =============================================================================

# LNU and QNU need different regularization scales.  The original shared
# lambda=1e-4 is retained for LNU.  QNU uses a stronger default and an optional
# local-dynamics guard because the quadratic regressor is much more ill
# conditioned and can otherwise yield a recursively unstable plant model even
# when its one-step prediction error is small.
plant_batch_r_0 = 1.0
plant_qnu_batch_r_0 = 100.0
plant_qnu_batch_stability_guard = True
plant_qnu_batch_rho_target = 0.995
plant_qnu_batch_lambda_growth = 10.0
plant_qnu_batch_lambda_max = 1.0e3

plant_batch_mu_w_bibs = 0.5
plant_batch_eps_bibs = 1.0e-12
plant_batch_plot_bibs_limit = True


# =============================================================================
# Module 02 Levenberg-Marquardt plant identification
# =============================================================================

plant_lm_epochs = 30
plant_lm_lambda = 100.0

# =============================================================================
# Module 02 GD/NGD plant identification
# =============================================================================

plant_gd_ngd_learning = "NGD"
plant_gd_ngd_epochs = 30

# Architecture-specific learning-rate defaults.  mu_w remains the LNU value for
# backward compatibility.  The QNU value is deliberately smaller because its
# quadratic feature vector has a much larger energy.
mu_w = 0.4
plant_qnu_mu_w = 0.03
plant_qnu_gd_stability_guard = True
plant_qnu_gd_mu_safety = 1.0
plant_qnu_ngd_mu_max = 1.9
plant_gd_ngd_eps = 1.0e-4

# Backward-compatible aliases used only by older code paths.
plant_file_batch = plant_lnu_file_batch
plant_file_gd_ngd = plant_lnu_file_gd_ngd
plant_r_0 = plant_batch_r_0
mu_w_bibs = plant_batch_mu_w_bibs
plant_eps_bibs = plant_batch_eps_bibs
plant_plot_bibs_limit = plant_batch_plot_bibs_limit
plant_learning = plant_gd_ngd_learning
plant_epochs = plant_gd_ngd_epochs
plant_eps = plant_gd_ngd_eps

# =============================================================================
# Modules 03 and 04: controller training and physical ODE testing
# =============================================================================

# Module 03 trains the selected controller only on the identified HONU plant.
# To preserve the original, verified learning experiment, module 03 always uses
# the module-01 excitation as its desired trajectory: d = u_data, with the
# reference-model delay equal to the identified plant delay n_u1.
#
# Module 04 loads the saved controller and tests it on the selected physical ODE
# plant. The script name defines the plant-controller architecture.
# plant_training_method only selects which already-trained HONU plant file is
# loaded by module 03.

controller_seed = 1
Tau_1 = 0.3
Tau_2 = 0.3

# Reference d used by module 03 training and module 04 physical testing.
# "steps" deterministically alternates d_max, d_min, d_max, ... after one initial block.
# "random_steps" draws a new random level for every equal-duration block.
# "plant_input" replays the module-01 excitation, bounded as described below.
reference_type = "alternating_steps"# "steps" | "random_steps" | "plant_input"
reference_seed = 17
tau_d = 0.0

# Reference interval in normalized controlled-output coordinates, used unchanged
# by both module 03 and module 04.
# The physical ODE controlled output y is normalized with the fixed module-01 statistics. y is column 2
# (zero based). These limits do not modify module-03 controller training.
d_min = -7.0
d_max = 7.0
reference_measured_y_column = 4
reference_duration_sec = 60.0
reference_step_hold_sec = 10.0

plot_measured_plant_output = False

r_0_min = 0.0
r_0_max = 20.0
u_min = -2.0
u_max = 2.0
v_norm_max = 100.0
alpha_min = 1.0e-4
r_0_init = 0.4

# Exponential smoothing of controller increments:
# delta_s(k) = alpha*delta_raw(k) + (1-alpha)*delta_s(k-1).
# alpha=1 disables smoothing.
alpha_v = 0.7
alpha_r_0 = 0.7
alpha_v_qnu = 1.0
alpha_r_0_qnu = 1.0

# Common LNU-controller learning setup.
ctrl_learning = "NGD"
ctrl_epochs = 10
mu_v = 0.01
mu_r_0 = 0.0001
ctrl_eps = 1.0e-4

# Common QNU-controller learning setup.
ctrl_qnu_learning = "GD"
ctrl_qnu_epochs = 30
mu_v_qnu = 0.02
mu_r_0_qnu = 0.001

# Module 04 offset-free online adaptation. This is an explicit integral gain
# for the constant controller weight v_0 (xi_0 = 1). The update uses dt, so
# mu_i_04 has continuous-time integral-gain meaning. Set to 0 to disable it.
mu_i_04 = 0.001
mu_i_04_qnu = 0.001
# Direct normalized integral correction of r_0 for multiplicative/static-gain
# mismatch between the HONU model and the physical ODE plant.
mu_i_r_0_04 = 0.02
mu_i_r_0_04_qnu = 0.02
ctrl_qnu_eps = 1.0e-3
qnu_v_norm_max = 100.0

# Trained controller files.
ctrl_lnu_lnu_file = "controller_LNU_LNU_gd_ngd.txt"
ctrl_lnu_qnu_file = "controller_LNU_QNU_gd_ngd.txt"
ctrl_qnu_lnu_file = "controller_QNU_LNU_gd_ngd.txt"
ctrl_qnu_qnu_file = "controller_QNU_QNU_gd_ngd.txt"

# Module 04 physical ODE-test setup and output files.
ctrl_lnu_lnu_eval_file = "eval_LNU_LNU_physical.txt"
ctrl_lnu_qnu_eval_file = "eval_LNU_QNU_physical.txt"
ctrl_qnu_lnu_eval_file = "eval_QNU_LNU_physical.txt"
ctrl_qnu_qnu_eval_file = "eval_QNU_QNU_physical.txt"

# Backward-compatible switches retained for older external scripts. Module 04
# always runs when its script is launched.
physical_eval_gd_ngd_enabled = True
physical_eval_enabled = physical_eval_gd_ngd_enabled

# Controller BIBS-monitoring files.
bibs_ctrl_lnu_lnu_file = "bibs_controller_LNU_LNU_gd_ngd.txt"
bibs_ctrl_lnu_qnu_file = "bibs_controller_LNU_QNU_gd_ngd.txt"
bibs_ctrl_qnu_lnu_file = "bibs_controller_QNU_LNU_gd_ngd.txt"
bibs_ctrl_qnu_qnu_file = "bibs_controller_QNU_QNU_gd_ngd.txt"

# Backward-compatible aliases for older 03 scripts.
controller_plant_source = plant_training_method
controller_training_method = "gd_ngd"
ctrl_gd_ngd_file = ctrl_lnu_lnu_file
ctrl_gd_ngd_eval_file = ctrl_lnu_lnu_eval_file
ctrl_qnu_gd_ngd_file = ctrl_lnu_qnu_file
ctrl_qnu_gd_ngd_eval_file = ctrl_lnu_qnu_eval_file

# =============================================================================
# Plot setup
# =============================================================================

line_width = 4.0
font_size = 12
plant_model_name = "measured"
step_hold_sec = 3.0
u_amp = 2.0
input_type = "alternating_steps"
