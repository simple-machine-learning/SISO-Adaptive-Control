Mechanical: voice-coil servo
============================

Python model: ``plant_models.voice_coil_servo``

Description
-----------

Electromechanical position servo driven by a voice-coil actuator. The model
contains amplifier dynamics, coil resistance and inductance, back electromotive
force, carriage inertia, suspension stiffness, viscous damping, smooth Coulomb
friction, and a cubic restoring term.

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
     - Drive-voltage command
   * - Output
     - :math:`x(t)`
     - ``y`` / ``position``
     - Carriage position


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector is

.. math::

   \mathbf{x}(t)=[x(t),\,v(t),\,i(t),\,V_a(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The amplifier command and mechanical forces are

.. math::

   \begin{aligned}
   V_{cmd}(t) &= K_a \cdot \tanh(u(t)), \\
   F_{em}(t) &= K_t \cdot i(t), \\
   F_f(t) &= c \cdot v(t) + F_c \cdot \tanh\!\left(\frac{v(t)}{v_s}\right), \\
   F_s(t) &= k \cdot x(t) + k_3 \cdot x^3(t).
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}(t) &= v(t), \\
   m \cdot \dot{v}(t) &= F_{em}(t)-F_f(t)-F_s(t), \\
   L \cdot \dot{i}(t) &= V_a(t)-R \cdot i(t)-K_e \cdot v(t), \\
   \tau_a \cdot \dot{V}_a(t) &= V_{cmd}(t)-V_a(t).
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(drive-voltage command)},\\
   y(t)=x(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/voice_coil_servo.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 20 28 18 34

   * - Symbol
     - Python name
     - Default
     - Meaning
   * - :math:`m`
     - ``mass``
     - ``0.12``
     - Moving carriage mass.
   * - :math:`R`
     - ``resistance``
     - ``3.2``
     - Coil resistance.
   * - :math:`L`
     - ``inductance``
     - ``0.018``
     - Coil inductance.
   * - :math:`K_t`
     - ``force_constant``
     - ``4.5``
     - Voice-coil force constant.
   * - :math:`K_e`
     - ``back_emf_constant``
     - ``4.5``
     - Back-EMF constant.
   * - :math:`c`
     - ``damping``
     - ``1.1``
     - Viscous damping.
   * - :math:`k`
     - ``stiffness``
     - ``18.0``
     - Linear suspension stiffness.
   * - :math:`k_3`
     - ``cubic_stiffness``
     - ``1.8e4``
     - Cubic suspension stiffness.
   * - :math:`F_c`
     - ``coulomb_friction``
     - ``0.18``
     - Smooth Coulomb-friction level.
   * - :math:`v_s`
     - ``stribeck_velocity``
     - ``0.004``
     - Friction smoothing velocity.
   * - :math:`K_a`
     - ``amplifier_gain``
     - ``8.0``
     - Maximum amplifier output scale.
   * - :math:`\tau_a`
     - ``amplifier_time_constant``
     - ``0.004``
     - Amplifier time constant.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`v(t)`
     - ``v``
     - Carriage velocity state.
   * - :math:`i(t)`
     - ``i``
     - Voice-coil current state.
   * - :math:`V_a(t)`
     - ``V_a``
     - Amplifier output-voltage state.
   * - :math:`V_{cmd}(t)`
     - ``V_cmd``
     - Saturated amplifier voltage command generated from the control input.
   * - :math:`F_{em}(t)`
     - ``F_em``
     - Electromagnetic force produced by the voice coil.
   * - :math:`F_f(t)`
     - ``F_f``
     - Friction force acting on the mechanical subsystem.
   * - :math:`F_s(t)`
     - ``F_s``
     - Elastic suspension force.
   * - :math:`y(t)`
     - ``y``
     - Carriage-position deviation from the operating point.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `P. C. Sen, Principles of Electric Machines and Power Electronics (voice-coil electromechanical force and back-EMF foundations). <https://www.wiley.com/en-us/Principles+of+Electric+Machines+and+Power+Electronics%2C+3rd+Edition-p-9781118078877>`_

Implementation reference
------------------------

The implementation is contained in
``apps/simulated/plant_models/voice_coil_servo.py`` and follows the common
``default_params``, ``initial_state``, ``rhs``, and ``algebraic_outputs``
interface used by all physical ODE plants.
