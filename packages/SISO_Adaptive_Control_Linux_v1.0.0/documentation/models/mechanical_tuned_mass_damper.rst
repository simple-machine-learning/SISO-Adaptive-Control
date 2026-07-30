Mechanical: tuned mass vibration absorber
=========================================

Python model: ``plant_models.mechanical_tuned_mass_damper``

Description
-----------

Primary structure with a passive tuned-mass vibration absorber.

SISO input: commanded actuator force applied to the primary structure.
SISO output: primary-structure displacement.

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
     - Actuator-force command
   * - Output
     - :math:`x_p(t)`
     - ``y`` / ``primary_displacement``
     - Primary-structure displacement


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[x_p(t),\,v_p(t),\,x_a(t),\,v_a(t),\,F(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   F_{\mathrm{cmd}}(t)&=F_{\max}\tanh(u(t)) \\
   \Delta x(t)&=x_a(t)-x_p(t),\qquad \Delta v(t)=v_a(t)-v_p(t) \\
   F_a(t)&=k_a\Delta x(t)+k_{a3}\Delta x^3(t)+c_a\Delta v(t) \\
   F_g(t)&=k_px_p(t)+k_{p3}x_p(t)^3+c_pv_p(t)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}_p(t)&=v_p(t) \\
   \dot{v}_p(t)&=\dfrac{F(t)-F_g(t)+F_a(t)}{m_p} \\
   \dot{x}_a(t)&=v_a(t) \\
   \dot{v}_a(t)&=-\dfrac{F_a(t)}{m_a} \\
   \dot{F}(t)&=\dfrac{F_{\mathrm{cmd}}(t)-F(t)}{\tau_F}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(actuator-force command)},\\
   y(t)=x_p(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/mechanical_tuned_mass_damper.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`m_p`
     - ``m_primary``
     - ``1.0``
     - Mass of the primary mechanical body.
   * - :math:`m_a`
     - ``m_absorber``
     - ``0.12``
     - Mass of the tuned vibration absorber.
   * - :math:`k_p`
     - ``k_primary``
     - ``42.0``
     - Linear stiffness connecting the primary body to ground.
   * - :math:`c_p`
     - ``c_primary``
     - ``0.45``
     - Viscous damping connecting the primary body to ground.
   * - :math:`k_a`
     - ``k_absorber``
     - ``5.0``
     - Linear coupling stiffness between the primary body and absorber.
   * - :math:`c_a`
     - ``c_absorber``
     - ``0.16``
     - Viscous coupling damping between the primary body and absorber.
   * - :math:`k_{p3}`
     - ``k_primary_cubic``
     - ``55.0``
     - Cubic stiffness coefficient of the primary-body restoring force.
   * - :math:`k_{a3}`
     - ``k_absorber_cubic``
     - ``18.0``
     - Cubic stiffness coefficient of the absorber coupling.
   * - :math:`F_{\max}`
     - ``actuator_force_max``
     - ``12.0``
     - Symmetric saturation limit of the applied actuator force.
   * - :math:`\tau_F`
     - ``actuator_tau``
     - ``0.025``
     - First-order time constant of the force actuator.

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
     - Actuator-force command
   * - :math:`xp(t)`
     - ``y`` / ``primary_displacement``
     - Primary-structure displacement
   * - :math:`vp(t)`
     - ``primary_velocity``
     - Primary-structure velocity
   * - :math:`xa(t)`
     - ``absorber_displacement``
     - Absorber displacement
   * - :math:`va(t)`
     - ``absorber_velocity``
     - Absorber velocity
   * - :math:`xr(t)`
     - ``relative_displacement``
     - Absorber relative displacement
   * - :math:`Fa(t)`
     - ``actuator_force``
     - Actuator force
   * - :math:`Ftmd(t)`
     - ``absorber_force``
     - Absorber coupling force
   * - :math:`Fp(t)`
     - ``primary_restoring_force``
     - Primary restoring force
   * - :math:`x_{p}(t)`
     - ``x_p``
     - Primary-body displacement state.
   * - :math:`v_{p}(t)`
     - ``v_p``
     - Primary-body velocity state.
   * - :math:`x_{a}(t)`
     - ``x_a``
     - Actuator displacement state.
   * - :math:`v_{a}(t)`
     - ``v_a``
     - Actuator velocity state.
   * - :math:`force(t)`
     - ``force``
     - Actual actuator-force state after actuator dynamics and saturation.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`F(t)`
     - ``F``
     - Actuator force after actuator dynamics.
   * - :math:`F_{\mathrm{cmd}}`
     - ``F_mathrmcmd``
     - Saturated actuator-force command generated from the control input.
   * - :math:`\Delta x(t)`
     - ``Deltax``
     - Relative displacement between the primary mass and the tuned absorber mass.
   * - :math:`F_a(t)`
     - ``F_a``
     - Actuator force applied to the plant.
   * - :math:`F_g(t)`
     - ``F_g``
     - Force transmitted through the ground or support element.
   * - :math:`y(t)`
     - ``y``
     - Primary-mass displacement used as the controlled output.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `J. P. Den Hartog, Mechanical Vibrations (classical tuned-mass absorber). <https://archive.org/details/mechanicalvibrat00denh>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       # [x_primary, v_primary, x_absorber, v_absorber, actuator_force]
       return np.zeros(5, dtype=float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x_p, v_p, x_a, v_a, force = chi[:5]
       rel_x = x_a - x_p
       rel_v = v_a - v_p
       absorber_force = par.k_absorber * rel_x + par.k_absorber_cubic * rel_x**3 + par.c_absorber * rel_v
       primary_restoring = par.k_primary * x_p + par.k_primary_cubic * x_p**3 + par.c_primary * v_p
       return {
           "primary_displacement": x_p,
           "primary_velocity": v_p,
           "absorber_displacement": x_a,
           "absorber_velocity": v_a,
           "relative_displacement": rel_x,
           "actuator_force": force,
           "absorber_force": absorber_force,
           "primary_restoring_force": primary_restoring,
       }

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x_p, v_p, x_a, v_a, force = chi[:5]
       force_cmd = par.actuator_force_max * np.tanh(float(u))
       rel_x = x_a - x_p
       rel_v = v_a - v_p
       f_abs = par.k_absorber * rel_x + par.k_absorber_cubic * rel_x**3 + par.c_absorber * rel_v
       f_ground = par.k_primary * x_p + par.k_primary_cubic * x_p**3 + par.c_primary * v_p
       a_p = (force - f_ground + f_abs) / par.m_primary
       a_a = -f_abs / par.m_absorber
       return np.array([v_p, a_p, v_a, a_a, (force_cmd - force) / par.actuator_tau], dtype=float)
