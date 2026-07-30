Power grid: linear microgrid frequency
======================================

Python model: ``plant_models.microgrid_frequency_linear``

Description
-----------

Linear reduced-order load-frequency-control model: governor, turbine and grid.

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
     - Governor power command
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

   \mathbf{x}(t)=[x_g(t),\,p_m(t),\,\Delta f(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No additional static relation is required; the input enters directly in the state equations.

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}_g(t)&=\dfrac{-x_g(t)+k_u\tanh(u(t))-\Delta f(t)/R}{T_g} \\
   \dot{p}_m(t)&=\dfrac{-p_m(t)+x_g(t)}{T_t} \\
   \dot{\Delta f}(t)&=\dfrac{p_m(t)-P_L-D\Delta f(t)}{2H}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(governor power command)},\\
   y(t)=\Delta f(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/microgrid_frequency_linear.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`H`
     - ``H``
     - ``0.1667``
     - Equivalent grid inertia constant in the swing equation; larger values reduce the rate of frequency change for a given power imbalance.
   * - :math:`D`
     - ``D``
     - ``0.015``
     - Frequency-sensitive load damping coefficient; converts frequency deviation into an opposing power term.
   * - :math:`R`
     - ``R``
     - ``3.0``
     - Governor droop coefficient; sets the strength of frequency-deviation feedback in the governor command.
   * - :math:`k_u`
     - ``control_gain``
     - ``0.3``
     - Gain from normalized control input to the governor power command before the governor dynamics.
   * - :math:`P_L`
     - ``load_bias``
     - ``0.0``
     - Constant net load disturbance subtracted from generated mechanical/electrical power in the grid-frequency balance.

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
     - Governor power command
   * - :math:`\Delta f(t)`
     - ``y`` / ``frequency_deviation``
     - Grid-frequency deviation
   * - :math:`Pg(t)`
     - ``governor_output``
     - Governor output
   * - :math:`Pm(t)`
     - ``mechanical_power``
     - Diesel mechanical power
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
   * - :math:`y(t)`
     - ``y``
     - Grid-frequency deviation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `P. Kundur, Power System Stability and Control (swing equation and governor-turbine models). <https://www.accessengineeringlibrary.com/content/book/9780070359581>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.zeros(4, float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       xg, pm, df = chi[:3]
       return {"frequency_deviation": df, "governor_output": xg,
               "mechanical_power": pm, "load_disturbance": par.load_bias,
               "frequency_hz": 50.0+df}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       xg, pm, df = chi[:3]
       dxg = (-xg+par.control_gain*np.tanh(float(u))-df/par.R)/par.T_g
       dpm = (-pm+xg)/par.T_t
       ddf = (pm-par.load_bias-par.D*df)/(2.0*par.H)
       return np.array([dxg, dpm, ddf, 0.0], float)
