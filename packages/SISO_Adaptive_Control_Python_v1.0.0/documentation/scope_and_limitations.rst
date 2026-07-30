Purpose, scope and limitations
==============================

Purpose of the software
-----------------------

The software is a research and teaching environment for reproducible
experiments with SISO nonlinear plants, higher-order neural units (HONU),
model-reference adaptive control (MRAC) and HONU-based model predictive
control (MPC).  Its main purpose is to study

* simulation of selected continuous-time physical ODE models,
* generation of identification data,
* LNU and QNU approximation of sampled plant dynamics,
* comparison of Ridge, Levenberg--Marquardt, GD and NGD learning procedures,
* frozen and sliding-window prediction models,
* PCA reduction of HONU regressors,
* reference-model tracking, prediction accuracy and local numerical
  diagnostics.

The project should therefore be interpreted as an experimental simulation
framework.  It is not a complete industrial control system, a safety layer or
a certified plant controller.

Meaning of the common SISO interface
------------------------------------

Every physical model is exposed through one scalar plant input ``u`` and one
scalar controlled output ``y``.  Their physical meanings and units depend on
the selected ODE model and are documented on the corresponding model page.
The common names only provide a uniform software interface; they do not imply
that all models have comparable amplitudes, admissible ranges or actuator
capabilities.

The command signal ``d`` is processed by the selected reference model to form
``y_ref``.  The controller attempts to make ``y`` follow ``y_ref``.  This does
not guarantee that ``d``, ``y_ref``, ``y`` or ``u`` remain inside physically
admissible operating regions.

Stability and admissible identification data
--------------------------------------------

The software is primarily intended for plants that are open-loop stable or
already stabilized by an independent feedback controller, such as a PID
controller. This requirement applies to both simulated and measured data. The
HONU plant model is trained from sampled input-output trajectories; therefore,
all relevant signals must remain bounded and the plant must stay within a safe
operating region during the complete data-acquisition experiment.

For an open-loop unstable physical plant, identification data should be
collected only while an independent stabilizing controller is active. In that
configuration, the learned HONU model represents the dynamics visible in the
selected input-output channels under the stabilizing feedback. Depending on
the signal definitions, this may be the pre-stabilized closed-loop system
rather than the uncontrolled physical plant itself.

MRAC or MPC may subsequently be used to improve the behaviour of this stable
or pre-stabilized system, for example by improving reference tracking,
disturbance rejection, transient response, control smoothness or control
effort. The current implementation must not be interpreted as a general method
for safely identifying or stabilizing an arbitrary uncontrolled unstable
plant.

The LNU and QNU models can approximate linear and moderately nonlinear
input-output dynamics within the region represented by the training data. A
QNU extends local expressiveness through quadratic terms, but it does not
remove the locality of data-driven identification. Strong nonlinearities,
discontinuities, switching behaviour, substantial hysteresis, severe
saturation or operation outside the training domain can invalidate the learned
prediction model. No global nonlinear stability guarantee is implied.

What the software does not solve
--------------------------------

The current implementation does not provide a general treatment of the
following practical control aspects.

Actuator saturation and anti-windup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The controller output is not generally constrained by physical actuator
limits.  In particular, the menu values ``u_min`` and ``u_max`` define the
excitation range used for ODE-data generation and initial identification.
They do **not** clip the MRAC or MPC control signal during closed-loop
operation unless a particular model or module explicitly implements an
additional limitation.

Consequently, changing ``u_min`` or ``u_max`` may change the identification
data and the operating region represented by the learned model, while having
no direct limiting effect on the subsequently computed control signal ``u``.
The closed-loop algorithm can therefore request values that are unavailable,
unsafe or outside the range used for identification.

No general actuator-saturation model, rate limiter, dead zone, hysteresis or
anti-windup mechanism is included.  The absence of anti-windup is particularly
important when an external user adds saturation around an adaptive or
integrating control structure: the internal controller state or adaptive
parameters can continue to evolve although the physical actuator can no
longer follow the requested input.

Active physical operating ranges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The software does not automatically determine or enforce the actual active
range of plant states, outputs, inputs or internal physical variables.  A
simulation can therefore enter a region where

* the ODE model is no longer physically credible,
* parameters identified around one operating point are no longer valid,
* a HONU model extrapolates outside its training domain,
* state variables become negative although the represented quantity should be
  non-negative,
* thermal, mechanical, biological, electrical or pharmacological limits are
  violated.

The displayed trajectories are numerical simulation results, not a proof that
the corresponding operation is feasible for a real plant.  The user must
select excitation, command ranges, initial conditions and reference-model
speed consistently with the physical interpretation of the chosen model.

Constraint handling
~~~~~~~~~~~~~~~~~~~

The current HONU MPC formulation penalizes tracking error, absolute input and
input differences through ``q_track``, ``r_u``, ``r_du`` and ``r_ddu``.  These
terms are soft quadratic penalties.  They are not hard constraints and do not
guarantee

* input bounds,
* input-rate bounds,
* output bounds,
* state bounds,
* terminal constraints,
* invariant-set conditions,
* recursive feasibility.

A large ``r_u`` can reduce the magnitude of ``u`` and large ``r_du`` or
``r_ddu`` can smooth it, but none of these weights replaces explicit actuator
or state constraints.

Closed-loop stability and robustness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Local quantities such as prediction RMSE, spectral radii or
:math:`\rho(A_y)` are diagnostics of a fitted local model or update map.  They
are not, by themselves, a proof of global nonlinear closed-loop stability,
robustness or boundedness of all signals.

The software does not provide a general proof or guarantee of

* global asymptotic stability,
* input-to-state stability,
* robust stability under model uncertainty,
* robustness margins against delay mismatch,
* guaranteed BIBS stability of the complete adaptive closed loop,
* safe convergence of online or sliding-window adaptation.

A successful simulation for one seed, command sequence or parameter set must
not be generalized automatically to other operating conditions.

Noise, disturbances and unmodelled dynamics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unless explicitly introduced by the selected model or experiment, the
software does not reproduce the full sensor, actuator and environmental
uncertainty of a real system.  It does not automatically account for sensor
bias, quantization, packet loss, asynchronous sampling, actuator dynamics,
measurement filtering, unknown disturbances or structural model error.

Identification quality can degrade when the training data are insufficiently
exciting, noisy, strongly correlated or restricted to a narrow operating
range.  Low training error does not guarantee accurate multi-step prediction
or closed-loop performance.

Real-time implementation
~~~~~~~~~~~~~~~~~~~~~~~~

The simulation uses desktop Python execution.  It does not guarantee that the
selected ODE integration, sliding retraining or MPC optimization can finish
within ``dt_control`` on a target real-time platform.  Computational timing,
missed deadlines, numerical precision, communication delays and hardware
interfaces must be evaluated separately.

Safety and application-specific supervision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No emergency shutdown, fault detection, watchdog, supervisory state machine,
redundancy, validation monitor or safety interlock is supplied.  Models
related to biomedical, energy, mechanical or infrastructure systems are
illustrative simulation models and must not be used directly for safety-
critical decisions, treatment or equipment operation.

Interpretation of results
-------------------------

The software is appropriate for comparing algorithms under explicitly stated
simulation assumptions.  A result should always be reported together with

* the physical model and its parameters,
* definitions and units of ``u`` and ``y``,
* initial conditions,
* ``dt_sim`` and ``dt_control``,
* excitation and command ranges,
* identification interval and learning method,
* HONU type and regressor orders,
* PCA settings,
* controller settings,
* random seed,
* any externally added saturation or constraint handling.

Before applying an algorithm to a real plant, the missing practical layers
must be designed explicitly.  These normally include physical range checks,
actuator and rate constraints, anti-windup, state and output constraints,
noise filtering, disturbance handling, fault supervision, real-time timing
verification and an application-specific stability and safety analysis.
