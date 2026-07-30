Mechanical: two masses, LuGre friction
======================================

Python model: ``plant_models.two_mass_actuator_grounded_m2_lugre``

Description
-----------

Two-mass plant with second-order actuator, grounded masses, and LuGre friction
acting on m2.

This file contains the complete setup of this physical model. Algorithmic setup
for scripts 01, 02 and 03 remains in project_setup.py.

State vector:

    chi = [y1, dy1, y2, dy2, F1, dF1, z_f]

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
     - Actuator command
   * - Output
     - :math:`y_2(t)`
     - ``y`` / ``y2``
     - Mass 2 displacement


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[y_1(t),\,v_1(t),\,y_2(t),\,v_2(t),\,F_1(t),\,q_F(t),\,z_f(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No additional static relation is required; the input enters directly in the state equations.

State equations
~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   F_2(t)&=k_p \cdot (y_1(t)-y_2(t))+b_p \cdot (v_1(t)-v_2(t)) \\
   F_c&=\mu_kN,\qquad F_s=\mu_sN \\
   g(v_2(t))&=\max\!\left(F_c+(F_s-F_c)\exp\!\left[-\left|\dfrac{v_2(t)}{v_s}\right|^\alpha\right],\varepsilon_g\right) \\
   \dot{z}_f(t)&=v_2(t)-\dfrac{\sigma_0|v_2(t)|}{g(v_2(t))}z_f(t) \\
   F_f(t)&=\sigma_0z_f(t)+\sigma_1\dot z_f(t)+\sigma_2v_2(t)
   \end{aligned}

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{y}_1(t)&=v_1(t) \\
   \dot{v}_1(t)&=\dfrac{F_1(t)-F_2(t)-k_{g1} \cdot y_1(t)-k_1 \cdot v_1(t)}{m_1} \\
   \dot{y}_2(t)&=v_2(t) \\
   \dot{v}_2(t)&=\dfrac{F_2(t)-k_{g2} \cdot y_2(t)-k_2 \cdot v_2(t)-F_f(t)}{m_2} \\
   \dot{F}_1(t)&=q_F(t) \\
   \dot{q}_F(t)&=\omega_a^2 \cdot k_a \cdot u(t)-2 \cdot \zeta_a \cdot \omega_a \cdot q_F(t)-\omega_a^2 \cdot F_1(t) \\
   \dot{z}_f(t)&=v_2(t)-\dfrac{\sigma_0|v_2(t)|}{g(v_2(t))}z_f(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(actuator command)},\\
   y(t)=y_2(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/two_mass_actuator_grounded_m2_lugre.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`m_1`
     - ``m1``
     - ``1.0``
     - Mass of the first mechanical body.
   * - :math:`m_2`
     - ``m2``
     - ``1.0``
     - Mass of the second mechanical body.
   * - :math:`k_p`
     - ``kp``
     - ``25.0``
     - Linear coupling-spring stiffness between the two masses.
   * - :math:`b_p`
     - ``bp``
     - ``0.0``
     - Viscous coupling damping between the two masses.
   * - :math:`k_1`
     - ``k1``
     - ``0.35``
     - Linear grounding stiffness of mass 1.
   * - :math:`k_2`
     - ``k2``
     - ``0.2``
     - Linear grounding stiffness of mass 2.
   * - :math:`k_{g1}`
     - ``kg1``
     - ``0.0``
     - Additional grounding stiffness acting on mass 1.
   * - :math:`k_{g2}`
     - ``kg2``
     - ``2.0``
     - Additional grounding stiffness acting on mass 2.
   * - :math:`k_a`
     - ``ka``
     - ``1.0``
     - Static gain of the second-order actuator.
   * - :math:`\omega_a`
     - ``omega_a``
     - ``18.0``
     - Natural angular frequency of the second-order actuator.
   * - :math:`\zeta_a`
     - ``zeta_a``
     - ``0.65``
     - Damping ratio of the second-order actuator.
   * - :math:`N`
     - ``normal_force``
     - ``1.0``
     - Normal force scaling the LuGre friction force.
   * - :math:`\mu_k`
     - ``mu_k``
     - ``0.1``
     - Kinetic friction coefficient in the LuGre Stribeck curve.
   * - :math:`\mu_s`
     - ``mu_s``
     - ``0.2``
     - Static friction coefficient in the LuGre Stribeck curve.
   * - :math:`\sigma_0`
     - ``sigma_0``
     - ``10000.0``
     - LuGre bristle stiffness coefficient.
   * - :math:`\sigma_1`
     - ``sigma_1``
     - ``40.0``
     - LuGre bristle damping coefficient.
   * - :math:`\sigma_2`
     - ``sigma_2``
     - ``0.02``
     - Viscous friction coefficient in the LuGre model.
   * - :math:`v_s`
     - ``v_s``
     - ``0.01``
     - Stribeck characteristic velocity.
   * - :math:`\alpha`
     - ``friction_shape_alpha``
     - ``1.0``
     - Exponent controlling the shape of the Stribeck friction transition.
   * - :math:`\varepsilon_g`
     - ``g_eps``
     - ``1e-12``
     - Small positive floor preventing division by zero in the LuGre friction law.

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
     - Actuator command
   * - :math:`y_{2}(t)`
     - ``y`` / ``y2``
     - Mass 2 displacement
   * - :math:`y_{1}(t)`
     - ``y1``
     - Mass 1 displacement
   * - :math:`v_{1}(t)`
     - ``dy1``
     - Mass 1 velocity
   * - :math:`v_{2}(t)`
     - ``dy2``
     - Mass 2 velocity
   * - :math:`F_{1}(t)`
     - ``F1``
     - Actuator force
   * - :math:`q_F(t)`
     - ``dF1``
     - Actuator-force rate, equal to :math:`\dot F_1`
   * - :math:`F_{2}(t)`
     - ``F2``
     - Coupling force
   * - :math:`zf(t)`
     - ``z_f``
     - LuGre internal state
   * - :math:`z_f(t)`
     - ``z_f``
     - Friction internal state; retained for interface compatibility and constant in the viscous model
   * - :math:`Ff(t)`
     - ``F_f``
     - Friction force

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`F_c`
     - ``F_c``
     - Coulomb component of the friction force.
   * - :math:`g(v_2)`
     - ``g(v_2)``
     - Stribeck friction-magnitude function evaluated at the second-mass velocity.
   * - :math:`F_f(t)`
     - ``F_f``
     - Friction force acting on the mechanical subsystem.
   * - :math:`y(t)`
     - ``y``
     - Mass-2 displacement used as the controlled output.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `C. Canudas de Wit et al., A New Model for Control of Systems with Friction. <https://doi.org/10.1109/9.376053>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       return np.zeros(7, dtype=float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       y1 = chi[0]
       dy1 = chi[1]
       y2 = chi[2]
       dy2 = chi[3]
       F1 = chi[4]
       z_f = chi[6]
   
       F2 = par.kp * (y1 - y2) + par.bp * (dy1 - dy2)
       F_f, dz_f, g_f = friction_force(dy2, z_f, par)
   
       return {
           "y1": y1,
           "dy1": dy1,
           "y2": y2,
           "dy2": dy2,
           "F1": F1,
           "F2": F2,
           "z_f": z_f,
           "F_f": F_f,
           "dz_f": dz_f,
           "g_f": g_f,
       }

ODE right-hand side:

.. code-block:: python

   def rhs(t_local, chi, u_const, par):
       y1 = chi[0]
       dy1 = chi[1]
       y2 = chi[2]
       dy2 = chi[3]
       F1 = chi[4]
       dF1 = chi[5]
       z_f = chi[6]
   
       F2 = par.kp * (y1 - y2) + par.bp * (dy1 - dy2)
       F_f, dz_f, _ = friction_force(dy2, z_f, par)
   
       ddy1 = (F1 - F2 - par.kg1 * y1 - par.k1 * dy1) / par.m1
       ddy2 = (F2 - par.kg2 * y2 - par.k2 * dy2 - F_f) / par.m2
       ddF1 = (
           par.omega_a**2 * par.ka * u_const
           - 2.0 * par.zeta_a * par.omega_a * dF1
           - par.omega_a**2 * F1
       )
   
       return np.array([dy1, ddy1, dy2, ddy2, dF1, ddF1, dz_f], dtype=float)
