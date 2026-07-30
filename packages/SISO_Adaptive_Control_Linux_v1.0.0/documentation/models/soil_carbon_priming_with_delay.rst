Soil ecology: carbon priming with delay
=======================================

Python model: ``plant_models.soil_carbon_priming_with_delay``

Description
-----------

Delayed-input variant of ``soil_carbon_priming``.

The transport delay is represented by an 4-stage cascaded lag (Erlang
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
     - Fresh-carbon addition command
   * - Output
     - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The augmented state consists of the physical-model state vector :math:`\mathbf{x}_{p}(t)` and the delay-chain states :math:`z_1(t),\ldots,z_{n_d}(t)`:

.. math::

   \mathbf{x}(t)=\begin{bmatrix}\mathbf{x}_{p}(t)^{\mathsf T}&z_1(t)&\cdots&z_{n_d}(t)\end{bmatrix}^{\mathsf T}.

This model uses the same physical equations as :doc:`soil_carbon_priming`, but the commanded input is passed through an :math:`n_d`-stage first-order lag cascade. Let :math:`u_0=u(t)` and let :math:`z_i(t)` denote the state of delay stage :math:`i`.

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

The continuous-time state equations are given below.

Output equation
~~~~~~~~~~~~~~~

The base plant receives :math:`u_d(t)=z_{n_d}(t)` instead of :math:`u(t)`. Thus the complete state is the physical state of the base model augmented by :math:`[z_1(t),\ldots,z_{n_d}(t)]^\mathsf{T}`. The cascade is a finite-dimensional approximation of the configured input delay.

The total respiration flux used by the controlled output is

.. math::

   R_{\mathrm{CO_2}}(t)=r_l(t)+r_s(t),

so that

.. math::

   y(t)=\Delta R_{\mathrm{CO_2}}(t)=R_{\mathrm{CO_2}}(t)-R_{\mathrm{CO_2},0}.

Parameter implementation
------------------------

The delay-specific defaults are defined in ``apps/simulated/plant_models/soil_carbon_priming_with_delay.py``. Its ``PlantParams`` class inherits the physical-model parameters from ``apps/simulated/plant_models/soil_carbon_priming.py`` and adds the delay parameters, such as ``input_delay_sec`` and ``delay_order``. The function ``default_params()`` returns the combined default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`labile_{nom}`
     - ``labile_nom``
     - ``0.35``
     - Initial or nominal value of labile used to initialize and scale this model.
   * - :math:`stable_{nom}`
     - ``stable_nom``
     - ``3.0``
     - Initial or nominal value of stable used to initialize and scale this model.
   * - :math:`biomass_{nom}`
     - ``biomass_nom``
     - ``0.28``
     - Initial or nominal value of biomass used to initialize and scale this model.
   * - :math:`k_{labile}`
     - ``k_labile``
     - ``0.22``
     - Rate, affinity, or half-saturation coefficient k_labile in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{stable}`
     - ``k_stable``
     - ``0.01``
     - Rate, affinity, or half-saturation coefficient k_stable in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`half_{labile}`
     - ``half_labile``
     - ``0.2``
     - Half-saturation scale in the nonlinear half labile response.
   * - :math:`half_{stable}`
     - ``half_stable``
     - ``1.0``
     - Half-saturation scale in the nonlinear half stable response.
   * - :math:`priming_{strength}`
     - ``priming_strength``
     - ``2.2``
     - Model parameter ``priming_strength``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`priming_{half}`
     - ``priming_half``
     - ``0.3``
     - Half-saturation scale in the nonlinear priming response.
   * - :math:`yield_{labile}`
     - ``yield_labile``
     - ``0.48``
     - Conversion yield relating consumed substrate/resource to produced labile.
   * - :math:`yield_{stable}`
     - ``yield_stable``
     - ``0.32``
     - Conversion yield relating consumed substrate/resource to produced stable.
   * - :math:`mortality`
     - ``mortality``
     - ``0.055``
     - First-order loss coefficient for mortality.
   * - :math:`feed_{nom}`
     - ``feed_nom``
     - ``0.03``
     - Initial or nominal value of feed used to initialize and scale this model.
   * - :math:`k_F`
     - ``feed_gain``
     - ``0.025``
     - Gain converting the normalized control input into the model-specific feed actuation term.
   * - :math:`respiration_{nom}`
     - ``respiration_nom``
     - ``0.028``
     - Initial or nominal value of respiration used to initialize and scale this model.
   * - :math:`\tau_d(t)`
     - ``input_delay_sec``
     - ``6.0``
     - Mean transport delay represented by the cascaded first-order delay states.
   * - :math:`n_d`
     - ``delay_order``
     - ``4``
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
     - Fresh-carbon addition command
   * - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation
   * - :math:`CL(t)`
     - ``labile_carbon``
     - Labile carbon pool
   * - :math:`CS(t)`
     - ``stable_carbon``
     - Stable soil carbon pool
   * - :math:`B(t)`
     - ``microbial_biomass``
     - Microbial biomass
   * - :math:`fp(t)`
     - ``priming_factor``
     - Priming multiplier
   * - :math:`Rco_{2}(t)`
     - ``co2_flux``
     - Soil CO2 flux
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
   * - :math:`R_{\mathrm{CO_2}}`
     - ``R_mathrmCO_2``
     - Total carbon-dioxide respiration rate.
   * - :math:`y(t)`
     - ``y``
     - Carbon-dioxide respiration-rate deviation with delayed carbon input.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `Y. Kuzyakov, Priming effects: Interactions between living and dead organic matter. <https://doi.org/10.1016/j.soilbio.2010.04.003>`_
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
