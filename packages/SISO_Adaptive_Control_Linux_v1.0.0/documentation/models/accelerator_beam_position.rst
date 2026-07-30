Accelerator: transverse beam position
=====================================

Python model: ``plant_models.accelerator_beam_position``

Description
-----------

Transverse beam-position dynamics controlled by a corrector magnet.

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
     - Corrector-magnet command
   * - Output
     - :math:`x(t)`
     - ``y`` / ``position``
     - Transverse beam position


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[x(t),\,v(t),\,m(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   m_{\mathrm{cmd}}(t)&=\tanh(u(t)) \\
   a(t)&=-2\zeta\omega_\beta v(t)-\omega_\beta^2x(t)-k_3x^3(t)+k_m m(t)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}(t)&=v(t) \\
   \dot{v}(t)&=a(t) \\
   \dot{m}(t)&=\dfrac{m_{\mathrm{cmd}}(t)-m(t)}{\tau_m}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(corrector-magnet command)},\\
   y(t)=x(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/accelerator_beam_position.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`\omega_\beta`
     - ``omega_beta``
     - ``18.0``
     - Natural betatron angular frequency of the beam-position dynamics.
   * - :math:`\zeta`
     - ``damping_ratio``
     - ``0.12``
     - Damping ratio of the beam-position oscillation.
   * - :math:`k_m`
     - ``magnet_gain``
     - ``8.0``
     - Static gain from magnet-current state to beam deflection.
   * - :math:`\tau_m`
     - ``tau_magnet``
     - ``0.012``
     - Magnet-current actuator time constant.
   * - :math:`k_3`
     - ``cubic_stiffness``
     - ``45.0``
     - Coefficient of the cubic beam-restoring term.
   * - :math:`x_b`
     - ``orbit_bias``
     - ``0.0``
     - Constant orbit-offset disturbance in the beam-position equation.

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
     - Corrector-magnet command
   * - :math:`x(t)`
     - ``y`` / ``position``
     - Transverse beam position
   * - :math:`v(t)`
     - ``beam_velocity``
     - Transverse beam velocity
   * - :math:`m(t)`
     - ``magnet_field``
     - Corrector field
   * - :math:`F_r(t)`
     - ``restoring_force``
     - Effective restoring term
   * - :math:`x(t)`
     - ``x``
     - Transverse beam-position state.
   * - :math:`v(t)`
     - ``v``
     - Velocity state associated with the corresponding position state.
   * - :math:`m(t)`
     - ``m``
     - Actual corrector-magnet field state after first-order actuator dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`m_{\mathrm{cmd}}(t)`
     - ``m_mathrmcmd``
     - Saturated magnet-current command generated from the control input.
   * - :math:`a(t)`
     - ``a``
     - Beam acceleration produced by the commanded magnet action and plant dynamics.
   * - :math:`y(t)`
     - ``y``
     - Beam-position deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `H. Wiedemann, Particle Accelerator Physics (standard transverse dynamics reference). <https://doi.org/10.1007/978-3-319-18317-6>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.orbit_bias, 0.0, 0.0, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x, v, m = chi[:3]
       return {"position": x, "beam_velocity": v, "magnet_field": m,
               "restoring_force": par.omega_beta**2*x+par.cubic_stiffness*x**3}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x, v, m = chi[:3]
       m_cmd = np.tanh(float(u))
       a = (-2.0*par.damping_ratio*par.omega_beta*v-par.omega_beta**2*x
            -par.cubic_stiffness*x**3+par.magnet_gain*m)
       return np.array([v, a, (m_cmd-m)/par.tau_magnet, 0.0], float)
