HONU MPC
========

Purpose and computational structure
-----------------------------------

The **HONU MPC** page combines a physical continuous-time ODE plant, a
sampled-data HONU prediction model and a receding-horizon controller.  The
terms *plant learning* and *learning* in this page refer to identification of
the HONU prediction model.  They do **not** denote learning of a separate
neural controller.

For each MPC sample, the implemented information flow is

.. math::

   \boldsymbol{x}_k
   \longrightarrow
   \boldsymbol{z}_k = \boldsymbol{P}^{\mathsf T}\boldsymbol{x}_k
   \longrightarrow
   \boldsymbol{\varphi}_k
   \longrightarrow
   \hat y_{k+1}
   \longrightarrow
   \boldsymbol{u}^{\star}_k .

Here, :math:`\boldsymbol{x}_k` is the delayed plant regressor,
:math:`\boldsymbol{P}` is a fixed PCA projection, :math:`\boldsymbol{z}_k` is
the compressed regressor, :math:`\boldsymbol{\varphi}_k` is the LNU or QNU
feature vector, and :math:`\boldsymbol{u}^{\star}_k` is the optimized future
input sequence.  Only its first value is applied to the physical plant.

The prediction model is

.. math::

   \hat y_{k+1} = \boldsymbol{c}^{\mathsf T}\boldsymbol{\varphi}_k,

where the weight vector :math:`\boldsymbol{c}` is estimated by either Ridge
regression or Levenberg--Marquardt according to ``plant_learning``.

Application to stable or pre-stabilized plants
-----------------------------------------------

HONU MPC relies on predictions from a model identified from bounded
input-output data. It is therefore intended primarily for open-loop stable
plants or for plants already stabilized by an independent lower-level
controller. For an unstable physical plant, the stabilizing mechanism must be
active during identification and must provide a safe fallback during
validation and operation.

Within that bounded regime, MPC can improve tracking, disturbance rejection,
control smoothness and control effort. The soft penalties implemented in the
current software are not a substitute for a stabilizing terminal controller,
hard constraints, an invariant set or an independent safety layer. The
implementation does not provide a general stabilization guarantee for
arbitrary unstable or strongly nonlinear plants.

Regressor and delays
--------------------

Before PCA, the base regressor is

.. math::

   \boldsymbol{x}_k =
   \begin{bmatrix}
   y_k & y_{k-1} & \cdots & y_{k-n_y+1} &
   u_{k-n_{\tau_u}} & u_{k-n_{\tau_u}-1} & \cdots &
   u_{k-n_{\tau_u}-n_u+1}
   \end{bmatrix}^{\mathsf T},

with

.. math::

   n_{\tau_u}=\operatorname{round}\!\left(\frac{\mathtt{tau\_u\_delay}}
   {\mathtt{dt\_control}}\right).

Thus, ``n_y`` and ``n_u`` specify numbers of stored samples, while
``tau_u_delay`` specifies a pure time delay before the input-memory block.
The reference delay is implemented separately as

.. math::

   n_{\tau_d}=\operatorname{round}\!\left(\frac{\mathtt{tau\_d\_delay}}
   {\mathtt{dt\_control}}\right),
   \qquad d_k^{\mathrm{del}}=d_{k-n_{\tau_d}}.

PCA reduction
-------------

PCA is applied to the base regressor before adding the constant feature and
before constructing the QNU basis.  The implementation first centres the
initial regressor matrix only to determine its SVD directions.  Prediction
and fitting then use the uncentred projection

.. math::

   \boldsymbol{z}_k=\boldsymbol{P}^{\mathsf T}\boldsymbol{x}_k.

The projection matrix ``pca_projection`` is computed once from the initial
identification data and remains frozen during both frozen-HONU and
sliding-retraining MPC.  Consequently, sliding retraining updates
:math:`\boldsymbol{c}`, not the PCA coordinate system.

``pca_selection_mode = "rank"`` retains every numerically independent
component.  ``pca_selection_mode = "variability"`` retains the smallest
number of components whose cumulative squared singular values reach
``pca_retained_variability``.

For :math:`r` selected PCA components, the LNU feature count is

.. math::

   n_{\varphi,\mathrm{LNU}}=1+r,

and the QNU feature count is

.. math::

   n_{\varphi,\mathrm{QNU}}=\frac{(1+r)(2+r)}{2}.

Increasing the retained PCA dimension preserves more regressor information
but increases identification and MPC cost.  The increase is particularly
important for QNU because its feature count grows quadratically.  Reducing the
dimension improves conditioning and speed but can remove dynamically useful
information and increase prediction bias.

HONU feature construction
-------------------------

After PCA, the constant component is added:

.. math::

   \tilde{\boldsymbol{z}}_k =
   \begin{bmatrix}1 & \boldsymbol{z}_k^{\mathsf T}\end{bmatrix}^{\mathsf T}.

For LNU,

.. math::

   \boldsymbol{\varphi}_k=\tilde{\boldsymbol{z}}_k.

For QNU, ``qnu_features`` constructs all upper-triangular products
:math:`\tilde z_{k,i}\tilde z_{k,j}` for :math:`i\leq j`.  The order is
therefore **PCA first, constant feature second, QNU expansion third**.

Identification by Ridge or L-M
------------------------------

The GUI selector **learning** sets ``plant_learning``.

Ridge
~~~~~

For ``plant_learning = "ridge"``, the prediction weights are obtained in one
batch solve:

.. math::

   \boldsymbol{c}=
   \left(\boldsymbol{\Phi}^{\mathsf T}\boldsymbol{\Phi}
   +\lambda\boldsymbol{I}_0\right)^{-1}
   \boldsymbol{\Phi}^{\mathsf T}\boldsymbol{y},

where the constant-feature weight is not regularized.  ``lambda`` is the
Ridge regularization coefficient.

Increasing ``lambda`` usually reduces weight magnitude and sensitivity to
collinearity, but increases bias and may underfit.  Decreasing it improves
training fit but can amplify noise and numerical ill-conditioning.

Levenberg--Marquardt
~~~~~~~~~~~~~~~~~~~~

For ``plant_learning = "lm"``, ``solve_linear_lm`` performs
``lm_epochs`` damped iterations.  In this mode, ``lambda`` is the initial L-M
damping, not a Ridge penalty.

Increasing ``lm_epochs`` permits more damping adaptation and convergence but
increases computation, especially in sliding retraining.  Increasing the
initial ``lambda`` makes early updates more conservative and gradient-like;
decreasing it makes them more Gauss--Newton-like and potentially faster, but
less robust when the feature matrix is ill-conditioned.

Because the HONU model is linear in :math:`\boldsymbol{c}`, Ridge normally
provides the direct and computationally cheaper fit.  L-M is retained as an
iterative damped alternative and exposes its weight, RMSE, damping and local
update-map diagnostics.

MPC objective
-------------

At time :math:`k`, the optimizer computes the candidate sequence

.. math::

   \boldsymbol{u}_k=
   \begin{bmatrix}u_{k|k}&\cdots&u_{k+N_p-1|k}\end{bmatrix}^{\mathsf T},

where ``horizon`` is :math:`N_p`.  The implemented objective is

.. math::

   J =
   Q\sum_{i=1}^{N_p}(\hat y_{k+i|k}-y_{\mathrm{ref},k+i})^2
   +R_{\Delta u}\sum_{i=0}^{N_p-1}(\Delta u_{k+i|k})^2
   +R_{\Delta^2u}\sum_{i=0}^{N_p-1}(\Delta^2u_{k+i|k})^2
   +R_u\sum_{i=0}^{N_p-1}u_{k+i|k}^2.

The Python coefficients are ``q_track``, ``r_du``, ``r_ddu`` and ``r_u``.
All are clipped internally to non-negative values.

The future output sequence and its exact local Jacobian with respect to the
candidate input sequence are propagated recursively through the HONU model.
The optimizer then performs at most ``opt_iter`` damped Gauss--Newton steps.
It solves an augmented least-squares problem directly, uses a trust radius and
accepts only cost-reducing steps.  The previous optimum is shifted to form a
warm start.  Only :math:`u_{k|k}^{\star}` is applied; the procedure repeats at
the next sample.

The MPC signal is not clipped by ``u_min`` and ``u_max``.  These values define
the excitation range used for physical-plant simulation and initial
identification.  They are not actuator constraints.  Regularization by
``r_u``, ``r_du`` and ``r_ddu`` can discourage large or rapidly changing
inputs, but it cannot guarantee an admissible input range.  The current MPC
implementation also has no general hard state, output or input-rate
constraints and no anti-windup mechanism.  See :doc:`../scope_and_limitations`.

What is learned and what is optimized
-------------------------------------

HONU MPC contains two mathematically different adaptation problems.
Identification changes the prediction-model weights
:math:`\boldsymbol{c}`. Receding-horizon optimization changes the temporary
candidate control sequence :math:`\boldsymbol{u}_k`; it does not create a
separate neural-controller weight vector.

For a frozen model,

.. math::

   \boldsymbol{c}(k+1)=\boldsymbol{c}(k),

and only :math:`\boldsymbol{u}_k` is reoptimized at every sample. In sliding
mode, a new model estimate is computed from the latest data window,

.. math::

   \boldsymbol{c}(k)=
   \arg\min_{\boldsymbol{c}}
   \left\|\boldsymbol{y}_w(k)-
   \boldsymbol{\Phi}_w(k)\boldsymbol{c}\right\|_2^2
   +\lambda\left\|\boldsymbol{L}\boldsymbol{c}\right\|_2^2,

or by the equivalent damped L-M iterations. The refitted model is then held
fixed during the inner optimization of the current future input sequence.
There is therefore no simultaneous gradient update of model weights inside one
Gauss--Newton control-sequence step.

Recursive prediction
--------------------

For a candidate sequence, the predictor is rolled forward recursively. The
first prediction uses measured output and input histories. Later predictions
replace unavailable future outputs by earlier HONU predictions and unavailable
future inputs by entries of the candidate sequence:

.. math::

   \hat y_{k+i|k}=
   \boldsymbol{c}^{\mathsf T}
   \boldsymbol{\varphi}
   \left(\boldsymbol{x}_{k+i-1|k}\right),
   \qquad i=1,\ldots,N_p.

This is not a collection of independent one-step predictions. Prediction error
can accumulate through the autoregressive output history, which is why a good
one-step RMSE does not guarantee accurate long-horizon MPC behavior.

Prediction Jacobian
-------------------

Let

.. math::

   \boldsymbol{Y}(\boldsymbol{u}_k)=
   \begin{bmatrix}
   \hat y_{k+1|k}&\cdots&\hat y_{k+N_p|k}
   \end{bmatrix}^{\mathsf T}.

The optimizer requires

.. math::

   \boldsymbol{G}_k=
   \frac{\partial\boldsymbol{Y}}
   {\partial\boldsymbol{u}_k^{\mathsf T}}.

For each future step, the chain rule is propagated through the PCA projection,
HONU feature map and recursive regressor:

.. math::

   \frac{\partial\hat y_{k+i|k}}
   {\partial\boldsymbol{u}_k^{\mathsf T}}
   =
   \boldsymbol{c}^{\mathsf T}
   \frac{\partial\boldsymbol{\varphi}_i}
   {\partial\tilde{\boldsymbol{z}}_i^{\mathsf T}}
   \begin{bmatrix}0&\boldsymbol{P}^{\mathsf T}\end{bmatrix}
   \frac{\partial\boldsymbol{x}_{k+i-1|k}}
   {\partial\boldsymbol{u}_k^{\mathsf T}}.

For LNU,
:math:`\partial\boldsymbol{\varphi}/\partial\tilde{\boldsymbol{z}}^{\mathsf T}
=\boldsymbol{I}`. For QNU, each row corresponding to
:math:`\tilde z_a\tilde z_b` contains
:math:`\tilde z_b` in column :math:`a` and :math:`\tilde z_a` in column
:math:`b`; the diagonal term contributes :math:`2\tilde z_a`. The final factor
contains both direct candidate-input derivatives and derivatives inherited
through previous predicted outputs. This recursive Jacobian is the MPC analogue
of recurrent sensitivity propagation in MRAC controller training.

Residual form of the MPC objective
----------------------------------

Define the tracking residual

.. math::

   \boldsymbol{r}_y(\boldsymbol{u}_k)=
   \sqrt{Q}\left[
   \boldsymbol{Y}(\boldsymbol{u}_k)-\boldsymbol{Y}_{ref,k}
   \right].

Let :math:`\boldsymbol{D}_1` and :math:`\boldsymbol{D}_2` denote the first- and
second-difference operators, with boundary terms formed from the previously
applied inputs. The complete least-squares residual is

.. math::

   \boldsymbol{r}(\boldsymbol{u}_k)=
   \begin{bmatrix}
   \boldsymbol{r}_y(\boldsymbol{u}_k)\\
   \sqrt{R_{\Delta u}}\,\boldsymbol{D}_1\boldsymbol{u}_k\\
   \sqrt{R_{\Delta^2u}}\,\boldsymbol{D}_2\boldsymbol{u}_k\\
   \sqrt{R_u}\,\boldsymbol{u}_k
   \end{bmatrix},
   \qquad
   J=\boldsymbol{r}^{\mathsf T}\boldsymbol{r}.

Its Jacobian is

.. math::

   \boldsymbol{J}_r=
   \begin{bmatrix}
   \sqrt{Q}\,\boldsymbol{G}_k\\
   \sqrt{R_{\Delta u}}\,\boldsymbol{D}_1\\
   \sqrt{R_{\Delta^2u}}\,\boldsymbol{D}_2\\
   \sqrt{R_u}\,\boldsymbol{I}
   \end{bmatrix}.

Damped Gauss--Newton control update
-----------------------------------

At inner iteration :math:`\ell`, the candidate sequence is updated by solving

.. math::

   \left(\boldsymbol{J}_r^{\mathsf T}\boldsymbol{J}_r
   +\lambda_{GN}\boldsymbol{I}\right)
   \Delta\boldsymbol{u}^{(\ell)}
   =-\boldsymbol{J}_r^{\mathsf T}
   \boldsymbol{r}(\boldsymbol{u}^{(\ell)}).

The step is limited by the trust radius and accepted only when it decreases the
nonlinear objective. Damping is increased after a rejected trial and reduced
after a successful trial. The iteration stops after ``opt_iter`` iterations or
when the accepted step/cost improvement becomes sufficiently small.

The accepted optimum is shifted to initialize the next sample,

.. math::

   \boldsymbol{u}^{(0)}_{k+1}=
   \begin{bmatrix}
   u^{\star}_{k+1|k}&\cdots&u^{\star}_{k+N_p-1|k}&
   u^{\star}_{k+N_p-1|k}
   \end{bmatrix}^{\mathsf T}.

Only :math:`u^{\star}_{k|k}` is applied. The remainder is a plan, not an open-
loop command sequence.

Interpretation of MPC learning
------------------------------

The sliding-window option is adaptive model predictive control in the limited
sense that the prediction-model weights are repeatedly reidentified from recent
input-output data. It is not a general dual controller: the optimized input does
not explicitly trade tracking against future information gain, and persistent
excitation is not guaranteed. A short window can follow time variation but may
be ill-conditioned; a long window lowers variance but can hide recent plant
changes.

The regularization terms are soft penalties. Since the current implementation
has no general hard bounds on :math:`u`, :math:`\Delta u`, states or outputs,
large values remain possible when the learned model, reference or optimizer
requires them. ``u_min`` and ``u_max`` describe identification excitation, not
MPC constraints.

Frozen and sliding model modes
------------------------------

``run_mode = "identify"``
   Generates a batch identification record, computes PCA, fits the selected
   HONU model by Ridge or L-M and saves both the model weights and PCA basis.

``run_mode = "mpc_frozen"``
   Loads the model produced by **Identify HONU Plant**.  Both
   :math:`\boldsymbol{P}` and :math:`\boldsymbol{c}` remain fixed throughout
   closed-loop operation.  A configuration consistency check rejects a saved
   model if an identification-dependent setting has changed.

``run_mode = "mpc_sliding"``
   Uses the initial excitation interval to compute one PCA basis.  During
   closed-loop operation, the prediction weights :math:`\boldsymbol{c}` are
   repeatedly refitted from the latest sliding window by the selected Ridge or
   L-M method.  PCA remains frozen.

The effective sliding-window sample count is

.. math::

   N_w = \max\!\left(
   \left\lceil\frac{\mathtt{window\_length\_sec}}
   {\mathtt{dt\_control}}\right\rceil,
   \max(n_y,n_{\tau_u}+n_u)+3
   \right).

A longer window reduces estimation variance and usually gives smoother model
changes, but adapts more slowly to nonstationarity and costs more.  A shorter
window adapts faster but has less excitation information and can become noisy
or poorly conditioned.

Reference model
---------------

The MPC reference model is the cascade of two stable first-order systems. Its
continuous-time transfer function is

.. math::

   G_{\mathrm{ref}}(s)
   =\frac{Y_{\mathrm{ref}}(s)}{D(s)}
   =\frac{e^{-\tau_d s}}
   {(\tau_1 s+1)(\tau_2 s+1)},

where :math:`\tau_d=\mathtt{tau\_d\_delay}`. In the Python configuration,
:math:`\tau_1=\mathtt{tau1}` and :math:`\tau_2=\mathtt{tau2}`. The exact
sampled poles used by ``HONU_MPC_runner.py`` are

.. math::

   a_1=\exp(-\mathtt{dt\_control}/\mathtt{tau1}),\qquad
   a_2=\exp(-\mathtt{dt\_control}/\mathtt{tau2}).

The notation is intentionally separated from the PCA notation:
:math:`d` is the command, :math:`y_{\mathrm{ref}}` is the reference-model
output, :math:`\boldsymbol{x}` is the HONU regressor, and
:math:`\boldsymbol{z}=\boldsymbol{P}^{\mathsf T}\boldsymbol{x}` is the
PCA-reduced regressor. No scalar :math:`z` is introduced for the reference
model.

Increasing either time constant makes :math:`y_{\mathrm{ref}}` slower and
smoother. Decreasing it demands faster closed-loop dynamics and generally
increases required control action.

Parameter reference
-------------------

.. list-table::
   :header-rows: 1
   :widths: 19 21 35 25

   * - GUI label
     - Python name
     - Meaning and use
     - Increase / decrease
   * - physical plant
     - ``physical_model``
     - Continuous-time ODE model used as the controlled plant.
     - Changes equations, units, state dimension and definitions of :math:`u` and :math:`y`.
   * - HONU
     - ``honu``
     - ``LNU`` or ``QNU`` prediction architecture.
     - QNU increases nonlinear expressiveness and parameter count; LNU is cheaper and usually better conditioned.
   * - Use P regulator
     - ``preg_blackbox_enabled``
     - Uses :math:`u_{phys}=r_{Preg}(u_{new}-y)` inside the ODE plant.
     - Enabling changes the externally identified and controlled plant mapping.
   * - learning
     - ``plant_learning``
     - ``ridge`` or ``lm`` identification of HONU weights.
     - Ridge is a direct regularized solve; L-M is iterative and more expensive.
   * - excitation
     - ``excitation_mode``
     - Random or alternating steps for ODE simulation, initial identification and command generation.
     - Random steps improve amplitude diversity; alternating steps are deterministic.
   * - ``dt MPC [s]``
     - ``dt_control``
     - Sampling period of HONU data, reference model and MPC action.
     - Larger: lower cost and coarser dynamics. Smaller: finer dynamics and higher cost.
   * - ``dt sim [s]``
     - ``dt_sim``
     - Internal ODE integration step; must not exceed ``dt_control``.
     - Larger: faster, less accurate. Smaller: more accurate, more expensive.
   * - ``t sim [s]``
     - ``duration_sec``
     - ODE simulation and batch-identification duration.
     - Larger: more identification data and cost. Smaller: less coverage.
   * - ``d duration [s]``
     - ``reference_duration_sec``
     - Closed-loop run duration.
     - Larger: longer test and cost. Smaller: fewer command transitions.
   * - ``u step width [s]``
     - ``hold_sec``
     - Duration of one excitation step.
     - Larger emphasizes slower dynamics; smaller adds faster excitation.
   * - ``d step width [s]``
     - ``reference_hold_sec``
     - Duration of one command step.
     - Larger is easier to track; smaller is a more demanding bandwidth test.
   * - ``u_min``, ``u_max``
     - ``u_min``, ``u_max``
     - Excitation range for ODE simulation and initial identification only.
     - Wider improves coverage but can excite unsafe or strongly nonlinear regions. It does not clip MPC control.
   * - ``d_min``, ``d_max``
     - ``d_min``, ``d_max``
     - Command range before reference filtering.
     - Wider tests more operating points but increases extrapolation and control demand.
   * - ``tau_u [s]``
     - ``tau_u_delay``
     - Pure input delay in the HONU regressor.
     - Larger shifts input history farther into the past; incorrect values degrade identification.
   * - ``tau_d [s]``
     - ``tau_d_delay``
     - Pure delay applied to command :math:`d` before the reference model.
     - Larger delays desired output changes; smaller makes them occur earlier.
   * - ``n_y``
     - ``n_y``
     - Number of past output samples in the HONU regressor.
     - Larger gives longer output memory but increases dimension and recursive-instability risk.
   * - ``n_u``
     - ``n_u``
     - Number of delayed input samples in the HONU regressor.
     - Larger represents longer input dynamics but increases dimension and collinearity.
   * - ``training length [s]``
     - ``window_length_sec``
     - Sliding fit window and initial excitation duration.
     - Larger is smoother and slower to adapt; smaller is faster and noisier.
   * - ``lambda``
     - ``lambda``
     - Ridge coefficient or initial L-M damping, depending on ``plant_learning``.
     - Larger regularizes or damps more; smaller fits more aggressively.
   * - ``epochs``
     - ``lm_epochs``
     - Number of L-M iterations for each fit; disabled for Ridge.
     - Larger can improve convergence but directly increases retraining cost.
   * - ``normalized gain``
     - ``mu_bibs``
     - Reserved GUI/configuration value for a normalized online correction. In the current ``HONU_MPC_runner.py`` it is logged but is not applied to the fitted weights or MPC law.
     - Changing it currently has no numerical effect on HONU MPC results.
   * - ``denominator eps``
     - ``eps_bibs``
     - Reserved denominator regularization for the normalized correction. In the current ``HONU_MPC_runner.py`` it is logged but not used.
     - Changing it currently has no numerical effect on HONU MPC results.
   * - ``PCA mode``
     - ``pca_selection_mode``
     - ``rank`` or ``variability`` component selection.
     - Rank preserves all independent directions; variability permits dimension reduction.
   * - ``retained variability``
     - ``pca_retained_variability``
     - Target cumulative SVD energy in variability mode.
     - Larger retains more information and features; smaller compresses more aggressively.
   * - ``tau 1 [s]``
     - ``tau1``
     - First reference-model time constant.
     - Larger slows and smooths the desired response; smaller accelerates it.
   * - ``tau 2 [s]``
     - ``tau2``
     - Second reference-model time constant.
     - Larger slows and smooths the desired response; smaller accelerates it.
   * - ``r_Preg``
     - ``r_preg``
     - Gain of the optional internal P regulator.
     - Larger magnitude strengthens the inner loop but can increase oscillation or instability.
   * - ``MPC horizon``
     - ``horizon``
     - Prediction and optimized-input horizon :math:`N_p`.
     - Larger gives more foresight but increases Jacobian and optimization cost; smaller is more myopic.
   * - ``Q tracking``
     - ``q_track``
     - Weight on predicted tracking error.
     - Larger prioritizes tracking and usually increases control action; smaller tolerates more error.
   * - ``R delta u``
     - ``r_du``
     - Weight on first input differences.
     - Larger smooths input changes; smaller permits faster movement.
   * - ``R delta2 u``
     - ``r_ddu``
     - Weight on second input differences.
     - Larger suppresses curvature and input chattering; smaller permits sharper changes.
   * - ``R u``
     - ``r_u``
     - Weight on absolute input magnitude.
     - Larger keeps :math:`u` near zero; smaller permits larger steady control values.
   * - ``optimizer iter.``
     - ``opt_iter``
     - Maximum damped Gauss--Newton iterations per MPC sample.
     - Larger can reduce the local cost but increases real-time computation; smaller may stop early.
   * - ``seed``
     - ``seed``
     - Random generator seed for reproducible excitation and command sequences.
     - Changes the realization, not the algorithmic gain or time scale.
   * - ``line width [px]``
     - GUI plotting state
     - Plot-curve width only.
     - No effect on identification, prediction or control.

Workflow buttons
----------------

``1. Simulate physical ODE plant`` runs the selected ODE plant without HONU
identification or MPC.  ``2. Identify HONU Plant`` creates the batch model and
PCA basis required by frozen mode.  ``3.1 MPC - Frozen HONU`` uses that saved
model without weight updates.  ``3.2 MPC - Sliding Retraining`` computes one
initial PCA basis and repeatedly refits the HONU weights on the active window.

Implementation diagnostics
--------------------------

The result files store the selected PCA dimension, numerical rank, retained
variability, singular values, projection matrix, HONU weights, identification
RMSE, local :math:`\rho(A_y)` and, for L-M, local weight-update spectral-radius
information.  These diagnostics describe the fitted prediction model; they
are not additional controller-learning laws.
