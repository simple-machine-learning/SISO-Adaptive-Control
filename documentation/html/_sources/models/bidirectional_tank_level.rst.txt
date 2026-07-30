Process: bidirectional-pump nonlinear tank
==========================================

Python model: ``plant_models.bidirectional_tank_level``

Description
-----------

Nonlinear SISO tank-level plant with a bidirectional pump.

The same signed pump command fills or drains the tank. Gravity outflow is
proportional to sqrt(h), which makes upward and downward transients different,
while the bidirectional pump preserves SISO control authority in both
directions around the nominal operating point.

state vector :math:`\mathbf{x}` = [h, q_pump, 0, 0, 0, 0, 0]
The controlled output is :math:`y=h-h_0` [m].

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
     - Bidirectional pump command
   * - Output
     - :math:`\Delta h(t)`
     - ``y`` / ``level_deviation``
     - Tank-level deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[h(t),\,q_p(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   q_{\mathrm{cmd}}(t)&=q_0+k_p\tanh(u(t)) \\
   q_{\mathrm{out}}(t)&=c_o\sqrt{\max(h(t),0)}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{h}(t)&=\dfrac{q_p(t)-q_{\mathrm{out}}(t)}{A} \\
   \dot{q}_p(t)&=\dfrac{q_{\mathrm{cmd}}(t)-q_p(t)}{\tau_p}
   \end{aligned}

At the physical boundary :math:`h(t)=0`, the implementation prevents a negative level; if a numerical integration stage crosses below zero, a restoring derivative is applied.

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(bidirectional pump command)},\\
   y(t)=\Delta h(t)=h(t)-h_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/bidirectional_tank_level.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`h_0`
     - ``h0``
     - ``1.0``
     - Initial or nominal liquid level.
   * - :math:`A`
     - ``area``
     - ``1.6``
     - Tank cross-sectional area converting net volumetric flow into level rate.
   * - :math:`c_o`
     - ``outflow_coeff``
     - ``0.34``
     - Coefficient of the gravity-driven outlet flow.
   * - :math:`k_p`
     - ``pump_gain``
     - ``0.62``
     - Gain from normalized input to signed pump-flow command.
   * - :math:`\tau_p`
     - ``tau_pump``
     - ``0.22``
     - First-order time constant of the infusion/pump actuator.

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
     - Bidirectional pump command
   * - :math:`\Delta h(t)`
     - ``y`` / ``level_deviation``
     - Tank-level deviation
   * - :math:`h(t)`
     - ``level``
     - Liquid level
   * - :math:`q_p(t)`
     - ``pump_flow``
     - Signed pump flow
   * - :math:`q_{\mathrm{out}}(t)`
     - ``gravity_outflow``
     - Gravity outflow
   * - :math:`q_{\mathrm{net}}(t)`
     - ``net_flow``
     - Net tank flow

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`q_{\mathrm{cmd}}(t)`
     - ``q_mathrmcmd``
     - Saturated bidirectional flow command generated from the control input.
   * - :math:`y(t)`
     - ``y``
     - Liquid-level deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `Feedback Instruments, Coupled Tanks control-system model (mass balance and Torricelli outflow). <https://www.feedback-instruments.com/products/process-control/coupled-tanks/>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       return np.array([par.h0, par.q0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       h, q_pump = np.asarray(chi, dtype=float)[:2]
       q_out = par.outflow_coeff * np.sqrt(max(h, 0.0))
       return {
           "level": h,
           "level_deviation": h - par.h0,
           "pump_flow": q_pump,
           "gravity_outflow": q_out,
           "net_flow": q_pump - q_out,
       }

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       h, q_pump = np.asarray(chi, dtype=float)[:2]
       q_cmd = par.q0 + par.pump_gain * np.tanh(float(u))
       dq_pump = (q_cmd - q_pump) / par.tau_pump
       q_out = par.outflow_coeff * np.sqrt(max(h, 0.0))
       dh = (q_pump - q_out) / par.area
       # Keep the continuous state on the physical half-line. If a numerical
       # integration stage crosses slightly below zero, drive it smoothly back
       # instead of leaving it trapped at a negative level.
       if h < 0.0:
           dh = max(dh, -h / 0.01)
       elif h == 0.0 and dh < 0.0:
           dh = 0.0
       return np.array([dh, dq_pump, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)
