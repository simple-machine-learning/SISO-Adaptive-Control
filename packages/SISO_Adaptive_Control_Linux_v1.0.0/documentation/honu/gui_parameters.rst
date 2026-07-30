HONU MRAC menu parameters
=========================

The table below maps each **HONU MRAC** GUI control to the exact Python configuration field, its mathematical or algorithmic role, and the practical consequence of changing it. The Python names correspond to ``project_setup.py`` after the GUI saves the active setup.

Model and signal selectors
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 22 35 25

   * - GUI control
     - Python value
     - Meaning
     - Effect of selection
   * - physical plant
     - ``plant_model_name``
     - Physical ODE model simulated in modules 01 and 04.
     - Changes the state equations, physical parameters, units, and definition of :math:`y`.
   * - HONU plant
     - ``gui_honu_plant``
     - Identified plant architecture: ``LNU`` or ``QNU``.
     - QNU is more expressive but larger and generally less well conditioned.
   * - controller
     - ``gui_controller_model``
     - Adaptive controller architecture: ``LNU`` or ``QNU``.
     - QNU yields a nonlinear controller with more trainable weights.
   * - plant learning
     - ``plant_training_method`` and method-specific fields
     - Batch/Ridge, L-M, GD, or NGD identification.
     - Determines the module-02 algorithm and trained plant file used by module 03.
   * - controller learning
     - ``ctrl_learning`` or ``ctrl_qnu_learning``
     - ``GD`` or ``NGD`` controller adaptation.
     - NGD reduces sensitivity to regressor magnitude.
   * - excitation u / reference d
     - ``input_type`` and ``reference_type``
     - Alternating steps, random steps, or replay of plant excitation.
     - Random steps improve amplitude diversity; alternating steps are deterministic and reproducible.

Simulation parameters
---------------------

.. list-table::
   :header-rows: 1
   :widths: 16 18 36 30

   * - GUI label
     - Python name
     - Meaning
     - Increase / decrease
   * - ``t_sim [s]``
     - ``t_end``
     - Duration of module-01 physical-plant data generation.
     - Increase: more data and computation, usually better dynamic coverage. Decrease: faster run, higher risk of insufficient excitation.
   * - ``u step width [s]``
     - ``step_hold_sec``
     - Duration of each constant excitation level.
     - Increase: slower switching and better observation of slow transients. Decrease: richer high-frequency excitation, but possibly inadequate settling and more demanding integration.
   * - ``tau_u [s]``
     - ``tau_u``
     - Input-delay embedding interval used by HONU identification. In the GUI it is synchronized with ``tau_d``.
     - Increase: represents a longer physical time between embedded input samples. Decrease: represents finer input history; too small can make neighboring regressors strongly correlated.
   * - ``dt MRAC [s]``
     - ``dt``
     - Sample period of generated data, HONU identification, reference model, and MRAC.
     - Increase: fewer samples and lower cost but coarser dynamics and potentially poorer discrete-time stability. Decrease: finer dynamics and larger datasets; learning rates may need retuning.
   * - ``dt_sim [s]``
     - ``dt_sim``
     - Internal maximum ODE integration step inside one zero-order-hold interval.
     - Increase: faster but less accurate integration. Decrease: more accurate and usually more robust for stiff/fast dynamics, with greater cost.
   * - ``u_min``
     - ``u_min``
     - Minimum excitation value used only by module 01.
     - Lower value: wider negative excitation and better coverage, but potentially nonphysical or unsafe model regions. Higher value: narrower excitation.
   * - ``u_max``
     - ``u_max``
     - Maximum excitation value used only by module 01.
     - Higher value: wider positive excitation, but greater nonlinear/stability stress. Lower value: narrower excitation. Controller :math:`u` in modules 03/04 is not clipped by these fields.
   * - ``P regulator``
     - ``preg_blackbox_enabled``
     - Enables the inner fixed proportional loop around the physical ODE plant.
     - Enabled: HONU identifies the external mapping from ``u_new`` to :math:`y`; disabled: HONU identifies the original plant from :math:`u` to :math:`y`.
   * - ``r_Preg``
     - ``r_preg``
     - Inner proportional gain in :math:`u_{phys}=r_{Preg}(u_{new}-y)`.
     - Larger magnitude: stronger inner feedback and faster response, but more oscillation/instability risk. Sign must match the plant input-output direction.
   * - ``line width [px]``
     - GUI plotting state
     - Width of plotted curves.
     - Visual only; no effect on simulation or learning.

Reference-model parameters
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 16 18 36 30

   * - GUI label
     - Python name
     - Meaning
     - Increase / decrease
   * - ``d duration [s]``
     - ``reference_duration_sec``
     - Total reference duration in modules 03 and 04.
     - Increase: longer training/test record and more computation. Decrease: shorter validation and fewer reference transitions.
   * - ``d step width [s]``
     - ``reference_step_hold_sec``
     - Duration of one constant reference level, rounded to an integer number of ``dt`` samples.
     - Increase: slower commands and easier tracking. Decrease: faster commands and a more demanding bandwidth test.
   * - ``tau_d [s]``
     - ``tau_d``
     - Reference switching period parameter; synchronized with ``tau_u`` in the current GUI.
     - Its practical effect follows ``tau_u`` because editing either control updates the other.
   * - ``tau_1 [s]``
     - ``Tau_1``
     - First time constant of the cascaded first-order reference model.
     - Increase: slower, smoother reference dynamics. Decrease: faster desired response and larger control demand.
   * - ``tau_2 [s]``
     - ``Tau_2``
     - Second time constant of the cascaded reference model.
     - Increase: more smoothing and slower settling. Decrease: higher desired bandwidth; too small relative to ``dt`` gives a poor discrete approximation.
   * - ``d_min``
     - ``d_min``
     - Minimum normalized reference level.
     - Decrease: extends commanded operation downward and increases extrapolation risk.
   * - ``d_max``
     - ``d_max``
     - Maximum normalized reference level.
     - Increase: extends commanded operation upward and increases extrapolation/control-effort risk.

In module 04 the GUI additionally constrains the admissible test reference to
the measured controlled-output range obtained from ``data_uy.txt``. Therefore
``d_min`` and ``d_max`` should be interpreted in normalized controlled-output
coordinates and should remain inside the supported physical-data domain.

Plant HONU parameters
---------------------

.. list-table::
   :header-rows: 1
   :widths: 16 18 36 30

   * - GUI label
     - Python name
     - Meaning
     - Increase / decrease
   * - ``n_y``
     - ``plant_n_y``
     - Number of delayed output samples in the plant regressor.
     - Increase: longer autoregressive memory and more weights; may improve slow dynamics but worsen conditioning and recursive instability. Decrease: simpler, more robust model that may underfit dynamics.
   * - ``n_u``
     - ``plant_n_u``
     - Number of delayed input samples in the plant regressor.
     - Increase: longer input-memory representation and more weights. Decrease: simpler model with less ability to represent delayed dynamics.
   * - ``epochs``
     - ``plant_lm_epochs`` or ``plant_gd_ngd_epochs``
     - Number of plant-learning epochs.
     - Increase: more opportunity to converge, with more cost and possible overfitting/instability. Decrease: faster but potentially undertrained. Not material for Batch/Ridge.
   * - ``mu_w``
     - ``mu_w`` or ``plant_qnu_mu_w``
     - Plant-weight learning rate for GD/NGD.
     - Increase: faster learning and higher divergence risk. Decrease: slower, more conservative learning. Not the Ridge regularizer.
   * - ``lambda``
     - ``plant_batch_r_0`` / ``plant_qnu_batch_r_0`` or ``plant_lm_lambda``
     - Ridge penalty for Batch or damping for L-M, according to selected method.
     - Batch: increase means stronger shrinkage. L-M: increase means more conservative gradient-like steps. It is not used as the GD/NGD learning rate.

Controller-learning parameters
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 16 18 36 30

   * - GUI label
     - Python name
     - Meaning
     - Increase / decrease
   * - ``epochs``
     - ``ctrl_epochs`` or ``ctrl_qnu_epochs``
     - Number of controller-training passes over the module-03 trajectory.
     - Increase: potentially lower model-based training error, but more computation and over-adaptation risk. Decrease: faster, possibly insufficient training.
   * - ``mu_v``
     - ``mu_v`` or ``mu_v_qnu``
     - Learning rate of controller weight vector :math:`\boldsymbol{v}`.
     - Increase: faster controller adaptation and more oscillation/divergence risk. Decrease: slower adaptation. QNU normally needs a smaller value.
   * - ``mu_(r_0)``
     - ``mu_r_0`` or ``mu_r_0_qnu``
     - Learning rate of scalar adaptive gain :math:`r_0`.
     - Increase: faster gain correction but greater sensitivity and possible sign/magnitude excursions. Decrease: slower correction and more persistent gain mismatch.
   * - ``alpha_v``
     - ``alpha_v`` or ``alpha_v_qnu``
     - Exponential smoothing factor for controller-weight increments: :math:`\Delta\boldsymbol{v}_s=\alpha_v\Delta\boldsymbol{v}_{raw}+(1-\alpha_v)\Delta\boldsymbol{v}_{s,prev}`.
     - Increase toward 1: less smoothing and faster/noisier updates. Decrease toward 0: stronger smoothing and slower adaptation.
   * - ``alpha_(r_0)``
     - ``alpha_r_0`` or ``alpha_r_0_qnu``
     - Exponential smoothing factor for :math:`r_0` increments.
     - Increase toward 1: more immediate updates. Decrease toward 0: smoother, slower gain adaptation.
   * - ``r_(0,init)``
     - ``r_0_init``
     - Initial value of adaptive gain :math:`r_0`.
     - Larger magnitude increases initial direct control action. A wrong sign can initially drive the loop in the wrong direction; a value too close to zero can give weak initial control authority.

Parameter interactions and cautions
-----------------------------------

The effective memory length is governed jointly by ``n_y``, ``n_u``, ``tau_u``,
and ``dt``. The QNU parameter count grows quadratically with regressor length,
so changing either memory order can require substantial retuning of ``lambda``
and ``mu_w``.

Changing ``dt`` changes the discrete-time plant, reference-model update factors
``dt/Tau_1`` and ``dt/Tau_2``, the number of samples per step, and the effective
size of sample-wise adaptive updates. It should therefore be treated as a model
and controller redesign parameter rather than only a plotting resolution.

The excitation interval ``[u_min, u_max]`` and reference interval
``[d_min, d_max]`` serve different purposes. The first determines the module-01
identification domain; the second determines the desired controlled-output
domain. Reliable module-04 operation generally requires the reference trajectory
to remain within the behavior covered by module-01 data.


HONU MPC parameters
-------------------

The complete HONU MPC signal flow, PCA procedure, Ridge/L-M identification,
frozen and sliding model modes, objective function, optimizer, and all MPC-page
parameters are documented in :doc:`honu_mpc`.  In particular, the Ridge or
L-M selection identifies the HONU **plant prediction model**; it does not train
a separate neural controller.
