Power grid: nonlinear BESS microgrid frequency with delay
=========================================================

Python model: ``plant_models.microgrid_frequency_bess_nonlinear_with_delay``

Description
-----------

Delayed-input variant of ``microgrid_frequency_bess_nonlinear``.

The transport delay is represented by an 3-stage cascaded lag (Erlang
transport approximation) with mean delay ``input_delay_sec``. This keeps the
plant in finite-dimensional ODE form while producing a substantially delayed,
smooth actuator command.

Controlled input and output
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 14 22 28 36

   * - Role
     - Mathematical notation
     - Python/interface name
     - Meaning
   * - Input
     - :math:`u(t)`
     - ``u``
     - BESS power command
   * - Output
     - :math:`\Delta f(t)`
     - ``y`` / ``frequency_deviation``
     - Grid-frequency deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The augmented state consists of the physical-model state vector :math:`\mathbf{x}_{p}(t)` and the delay-chain states :math:`z_1(t),\ldots,z_{n_d}(t)`:

.. math::

   \mathbf{x}(t)=\begin{bmatrix}\mathbf{x}_{p}(t)^{\mathsf T}&z_1(t)&\cdots&z_{n_d}(t)\end{bmatrix}^{\mathsf T}.

This model uses the same physical equations as :doc:`microgrid_frequency_bess_nonlinear`, but the commanded input is passed through an :math:`n_d`-stage first-order lag cascade. Let :math:`u_0=u(t)` and let :math:`z_i(t)` denote the state of delay stage :math:`i`.

.. math::

   \begin{aligned}
   \tau_s &= \frac{\tau_d(t)}{n_d}, \\
   \dot{z}_1(t) &= \frac{u(t)-z_1(t)}{\tau_s}, \\
   \dot{z}_i(t) &= \frac{z_{i-1}(t)-z_i(t)}{\tau_s},\qquad i=2,\ldots,n_d.
   \end{aligned}

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No additional static relation is required; the input enters directly in the state equations.

State equations
~~~~~~~~~~~~~~~

The base plant receives :math:`u_d(t)=z_{n_d}(t)` instead of :math:`u(t)`. Thus the complete state is the physical state of the base model augmented by :math:`[z_1(t),\ldots,z_{n_d}(t)]^\mathsf{T}`. The cascade is a finite-dimensional approximation of the configured input delay.

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(undelayed BESS power command)},\\
   y(t)=\Delta f(t).
   \end{aligned}

Parameter implementation
------------------------

The delay-specific defaults are defined in ``apps/simulated/plant_models/microgrid_frequency_bess_nonlinear_with_delay.py``. Its ``PlantParams`` class inherits the physical-model parameters from ``apps/simulated/plant_models/microgrid_frequency_bess_nonlinear.py`` and adds the delay parameters, such as ``input_delay_sec`` and ``delay_order``. The function ``default_params()`` returns the combined default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

Parameters
----------

The mathematical notation is used in the equations above. The Python name is the exact field in ``PlantParams``; the last column explains how the parameter enters this specific model.

.. list-table::
   :header-rows: 1
   :widths: 20 25 18 37

   * - Mathematical notation
     - Python name
     - Default
     - Meaning
   * - :math:`T_g`
     - ``T_g``
     - ``0.08``
     - Governor first-order time constant; determines how quickly the governor state follows the commanded power and frequency-droop feedback.
   * - :math:`T_t`
     - ``T_t``
     - ``0.4``
     - Turbine first-order time constant; determines how quickly mechanical power follows the governor output.
   * - :math:`T_b`
     - ``T_bess``
     - ``0.1``
     - BESS power-converter time constant; determines how quickly battery power follows its command.
   * - :math:`H`
     - ``H``
     - ``0.1667``
     - Equivalent grid inertia constant in the swing equation; larger values reduce the rate of frequency change for a given power imbalance.
   * - :math:`D`
     - ``D``
     - ``0.02``
     - Frequency-sensitive load damping coefficient; converts frequency deviation into an opposing power term.
   * - :math:`R`
     - ``R``
     - ``3.0``
     - Governor droop coefficient; sets the strength of frequency-deviation feedback in the governor command.
   * - :math:`P_{b,\max}`
     - ``bess_power_max``
     - ``0.45``
     - Symmetric saturation limit of commanded BESS power.
   * - :math:`p_{d,0}`
     - ``diesel_bias``
     - ``0.0``
     - Constant bias added to the diesel-generator power channel.
   * - :math:`P_L`
     - ``load_bias``
     - ``0.0``
     - Constant net load disturbance subtracted from generated mechanical/electrical power in the grid-frequency balance.
   * - :math:`SOC_0`
     - ``soc_nom``
     - ``0.6``
     - Initial or nominal battery state of charge used by the model.
   * - :math:`E_b`
     - ``energy_capacity``
     - ``1800.0``
     - Battery energy-capacity scaling used to convert BESS power into state-of-charge rate.
   * - :math:`f_{db}`
     - ``deadband_hz``
     - ``0.005``
     - Frequency-deviation deadband below which the corresponding corrective action is suppressed.
   * - :math:`\tau_d(t)`
     - ``input_delay_sec``
     - ``0.3``
     - Mean transport delay represented by the cascaded first-order delay states.
   * - :math:`n_d`
     - ``delay_order``
     - ``3``
     - Number of first-order sections used to approximate the transport delay; higher order gives a sharper delay approximation.

Variables
---------

The first column gives the readable mathematical notation, the second gives the exact Python or SISO-interface name, and the third states the model-specific physical meaning. The table contains ODE states and algebraic signals reported by ``algebraic_outputs()``. A reported signal need not be an independent state, but it must be explicitly defined by the equations, an auxiliary relation, or the implementation reference below.

.. list-table::
   :header-rows: 1
   :widths: 22 28 50

   * - Mathematical notation
     - Python name
     - Meaning
   * - :math:`u(t)`
     - ``u``
     - BESS power command
   * - :math:`\Delta f(t)`
     - ``y`` / ``frequency_deviation``
     - Grid-frequency deviation
   * - :math:`Pg(t)`
     - ``governor_output``
     - Governor output
   * - :math:`Pm(t)`
     - ``diesel_power``
     - Diesel mechanical power
   * - :math:`Pb(t)`
     - ``bess_power``
     - BESS power
   * - :math:`z(t)`
     - ``state_of_charge``
     - Battery state of charge
   * - :math:`PL(t)`
     - ``load_disturbance``
     - Load disturbance
   * - :math:`f(t)`
     - ``frequency_hz``
     - Grid frequency
   * - :math:`u_{d}(t)`
     - ``effective_input``
     - Delayed effective input
   * - :math:`\tau_{d}(t)`
     - ``input_delay_sec``
     - Nominal input delay

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`\tau_s`
     - ``tau_s``
     - Time constant of one first-order section in the input-delay approximation.
   * - :math:`z_1(t)`
     - ``z_1``
     - First state of the cascaded input-delay approximation.
   * - :math:`y(t)`
     - ``y``
     - Grid-frequency deviation with delayed BESS actuation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `H. Bevrani, Robust Power System Frequency Control (load-frequency control and storage concepts). <https://doi.org/10.1007/978-3-319-07278-4>`_
* `Erlang distribution / cascaded first-order lag approximation used for finite-dimensional transport delay. <https://en.wikipedia.org/wiki/Erlang_distribution>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       x0 = np.asarray(base.initial_state(par), dtype=float)
       return np.concatenate((x0, np.zeros(int(par.delay_order), dtype=float)))

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x, z = _split(chi, par)
       out = dict(base.algebraic_outputs(x, par))
       out["effective_input"] = float(z[-1]) if len(z) else 0.0
       out["input_delay_sec"] = float(par.input_delay_sec)
       return out

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x, z = _split(chi, par)
       order = max(1, int(par.delay_order))
       tau_stage = max(float(par.input_delay_sec) / order, 1.0e-12)
       dz = np.empty(order, dtype=float)
       source = float(u)
       for i in range(order):
           dz[i] = (source - z[i]) / tau_stage
           source = z[i]
       dx = np.asarray(base.rhs(t, x, float(z[-1]), par), dtype=float)
       return np.concatenate((dx, dz))
