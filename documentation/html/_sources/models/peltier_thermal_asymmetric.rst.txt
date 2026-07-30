Thermal: asymmetric Peltier system
==================================

Python model: ``plant_models.peltier_thermal_asymmetric``

Description
-----------

Asymmetric SISO thermoelectric (Peltier) temperature-control plant.

The single manipulated input is the signed electrical-current command. Positive
current heats the controlled plate; negative current cools it. The Peltier term
is odd in current while Joule heating is even, so heating and cooling have
physically different dynamics although the plant remains controllable from one
input over the recommended operating range.

state vector :math:`\mathbf{x}` = [T_hot, T_cold, I, 0, 0, 0, 0]
The controlled output is :math:`y=T_h-T_{\mathrm{amb}}` [deg C].

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
     - Signed current command
   * - Output
     - :math:`\Delta T(t)`
     - ``y`` / ``temperature_deviation``
     - Controlled-plate temperature deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[T_h(t),\,T_c(t),\,I(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   I_{\mathrm{cmd}}(t)&=k_I\tanh(u(t)) \\
   T_{h,K}(t)&=T_h(t)+273.15,\qquad T_{c,K}(t)=T_c(t)+273.15 \\
   Q_{P,h}(t)&=\alpha T_{h,K}(t)I(t),\qquad Q_{P,c}(t)=\alpha T_{c,K}(t)I(t) \\
   Q_J(t)&=\dfrac{1}{2}R[I(t)]^2,\qquad Q_K(t)=K(T_h(t)-T_c(t))
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{T}_h(t)&=\dfrac{Q_{P,h}(t)+Q_J(t)-Q_K(t)-h_h(T_h(t)-T_a)}{C_h} \\
   \dot{T}_c(t)&=\dfrac{-Q_{P,c}(t)+Q_J(t)+Q_K(t)-h_c(T_c(t)-T_a)}{C_c} \\
   \dot{I}(t)&=\dfrac{I_{\mathrm{cmd}}(t)-I(t)}{\tau_I}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(signed current command)},\\
   y(t)=\Delta T(t)=T_h(t)-T_{\mathrm{amb}}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/peltier_thermal_asymmetric.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`T_a`
     - ``T_ambient``
     - ``25.0``
     - Ambient temperature of the Peltier assembly.
   * - :math:`C_h`
     - ``C_hot``
     - ``28.0``
     - Thermal capacitance of the hot side.
   * - :math:`C_c`
     - ``C_cold``
     - ``42.0``
     - Thermal capacitance of the cold side.
   * - :math:`\alpha`
     - ``alpha``
     - ``0.018``
     - Peltier thermoelectric coefficient.
   * - :math:`R`
     - ``resistance``
     - ``1.15``
     - Electrical resistance of the Peltier element, governing Joule heating.
   * - :math:`K`
     - ``conductance``
     - ``0.65``
     - Thermal conductance between hot and cold sides.
   * - :math:`h_h`
     - ``h_hot``
     - ``0.55``
     - Heat-transfer coefficient from the hot side to ambient.
   * - :math:`h_c`
     - ``h_cold``
     - ``1.25``
     - Heat-transfer coefficient from the cold side to ambient.
   * - :math:`k_I`
     - ``current_gain``
     - ``2.2``
     - Gain from normalized control input to Peltier current command.
   * - :math:`\tau_I`
     - ``tau_current``
     - ``0.18``
     - First-order time constant of the current actuator.

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
     - Signed current command
   * - :math:`\Delta T(t)`
     - ``y`` / ``temperature_deviation``
     - Controlled-plate temperature deviation
   * - :math:`T_h(t)`
     - ``temperature_hot``
     - Controlled-plate temperature
   * - :math:`T_c(t)`
     - ``temperature_cold``
     - Heat-sink temperature
   * - :math:`I(t)`
     - ``current``
     - Peltier current
   * - :math:`Q_{P,h}(t)`
     - ``peltier_heat``
     - Peltier heat rate
   * - :math:`Q_J(t)`
     - ``joule_heat``
     - Joule heat rate

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`I_{\mathrm{cmd}}`
     - ``I_mathrmcmd``
     - Saturated Peltier-current command generated from the control input.
   * - :math:`T_{h,K}(t)`
     - ``T_h,K``
     - Hot-side absolute temperature used in the Peltier heat-flow relations.
   * - :math:`y(t)`
     - ``y``
     - Cold-side temperature deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `D. M. Rowe (ed.), Thermoelectrics Handbook: Macro to Nano (Peltier, Joule, and conductive heat terms). <https://doi.org/10.1201/9781420038903>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       return np.array([par.T_ambient, par.T_ambient, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       T_hot, T_cold, current = np.asarray(chi, dtype=float)[:3]
       T_hot_K = T_hot + 273.15
       peltier_heat = par.alpha * T_hot_K * current
       joule_heat = par.resistance * current * current
       return {
           "temperature_hot": T_hot,
           "temperature_deviation": T_hot - par.T_ambient,
           "temperature_cold": T_cold,
           "current": current,
           "peltier_heat": peltier_heat,
           "joule_heat": joule_heat,
       }

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       T_hot, T_cold, current = np.asarray(chi, dtype=float)[:3]
       current_cmd = par.current_gain * np.tanh(float(u))
       dcurrent = (current_cmd - current) / par.tau_current
   
       T_hot_K = T_hot + 273.15
       T_cold_K = T_cold + 273.15
       peltier_hot = par.alpha * T_hot_K * current
       peltier_cold = par.alpha * T_cold_K * current
       joule_half = 0.5 * par.resistance * current * current
       conduction = par.conductance * (T_hot - T_cold)
   
       dT_hot = (
           peltier_hot + joule_half - conduction
           - par.h_hot * (T_hot - par.T_ambient)
       ) / par.C_hot
       dT_cold = (
           -peltier_cold + joule_half + conduction
           - par.h_cold * (T_cold - par.T_ambient)
       ) / par.C_cold
   
       return np.array([dT_hot, dT_cold, dcurrent, 0.0, 0.0, 0.0, 0.0], dtype=float)
