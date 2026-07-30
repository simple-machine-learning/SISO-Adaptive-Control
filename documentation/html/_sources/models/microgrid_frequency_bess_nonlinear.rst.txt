Power grid: nonlinear BESS microgrid frequency
==============================================

Python model: ``plant_models.microgrid_frequency_bess_nonlinear``

Description
-----------

Nonlinear microgrid frequency model with diesel governor and BESS actuator/SOC.

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

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[x_g(t),\,p_m(t),\,\Delta f(t),\,p_b(t),\,SOC(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   \Delta f_{db}(t)&=\begin{cases}0,&|\Delta f(t)|\leq f_{db},\\ \Delta f(t)-\operatorname{sgn}(\Delta f(t))f_{db},&|\Delta f(t)|>f_{db},\end{cases} \\
   a(SOC(t))&=\operatorname{clip}\!\left(4SOC(t)(1-SOC(t)),0,1\right) \\
   p_{b,\mathrm{cmd}}(t)&=P_{b,\max}a(SOC(t))\tanh(u(t))
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}_g(t)&=\dfrac{-x_g(t)+p_{d,0}-\Delta f_{db}(t)/R}{T_g} \\
   \dot{p}_m(t)&=\dfrac{-p_m(t)+x_g(t)}{T_t} \\
   \dot{\Delta f}(t)&=\dfrac{p_m(t)+p_b(t)-P_L-D\Delta f(t)}{2H} \\
   \dot{p}_b(t)&=\dfrac{p_{b,\mathrm{cmd}}(t)-p_b(t)}{T_b} \\
   \dot{SOC}(t)&=-\dfrac{p_b(t)}{E_b}
   \end{aligned}

The implementation prevents :math:`SOC(t)` from being driven further outside the interval :math:`[0.02,0.98]`.

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(BESS power command)},\\
   y(t)=\Delta f(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/microgrid_frequency_bess_nonlinear.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`xg(t)`
     - ``xg``
     - Governor output state that drives the turbine mechanical-power dynamics.
   * - :math:`pm(t)`
     - ``pm``
     - Turbine mechanical-power state entering the grid power-balance equation.
   * - :math:`df(t)`
     - ``df``
     - Grid-frequency deviation; this is the controlled output returned as ``y``.
   * - :math:`pb(t)`
     - ``pb``
     - BESS power state.
   * - :math:`soc(t)`
     - ``soc``
     - Battery state of charge.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`x_g(t)`
     - ``x_g``
     - Governor-valve or governor-control state.
   * - :math:`p_m(t)`
     - ``p_m``
     - Mechanical-power state or mechanical power supplied to the grid.
   * - :math:`p_b(t)`
     - ``p_b``
     - Battery-power state or commanded BESS power after saturation and availability limits.
   * - :math:`\Delta f_{db}(t)`
     - ``Deltaf_db``
     - Frequency deviation after application of the deadband nonlinearity.
   * - :math:`a(SOC(t))`
     - ``a(SOC(t))``
     - State-of-charge-dependent BESS availability factor.
   * - :math:`p_{b,\mathrm{cmd}}`
     - ``p_b,mathrmcmd``
     - BESS power command after saturation and state-of-charge availability limiting.
   * - :math:`y(t)`
     - ``y``
     - Grid-frequency deviation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `H. Bevrani, Robust Power System Frequency Control (load-frequency control and storage concepts). <https://doi.org/10.1007/978-3-319-07278-4>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([0.0, 0.0, 0.0, 0.0, par.soc_nom], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       xg, pm, df, pb, soc = chi[:5]
       return {"frequency_deviation": df, "governor_output": xg,
               "diesel_power": pm, "bess_power": pb, "state_of_charge": soc,
               "load_disturbance": par.load_bias, "frequency_hz": 50.0+df}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       xg, pm, df, pb, soc = chi[:5]
       db = 0.0 if abs(df) <= par.deadband_hz else df-np.sign(df)*par.deadband_hz
       dxg = (-xg+par.diesel_bias-db/par.R)/par.T_g
       dpm = (-pm+xg)/par.T_t
       availability = np.clip(4.0*soc*(1.0-soc), 0.0, 1.0)
       pb_cmd = par.bess_power_max*availability*np.tanh(float(u))
       dpb = (pb_cmd-pb)/par.T_bess
       ddf = (pm+pb-par.load_bias-par.D*df)/(2.0*par.H)
       dsoc = -pb/par.energy_capacity
       if soc <= 0.02 and dsoc < 0.0: dsoc = 0.0
       if soc >= 0.98 and dsoc > 0.0: dsoc = 0.0
       return np.array([dxg, dpm, ddf, dpb, dsoc], float)
