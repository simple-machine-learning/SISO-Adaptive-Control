Mechanical: overhead crane payload sway
=======================================

Python model: ``plant_models.overhead_crane_payload_sway``

Description
-----------

Nonlinear overhead-crane trolley and suspended-payload dynamics.

SISO input: trolley-drive force command.
SISO output: horizontal payload position. Payload sway angle is diagnostic.

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
     - Trolley-drive command
   * - Output
     - :math:`x_L(t)`
     - ``y`` / ``payload_position``
     - Horizontal payload position


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[x(t),\,v(t),\,\theta(t),\,\omega(t),\,F(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   F_{\mathrm{cmd}}(t)&=F_{\max}\tanh(u(t)) \\
   F_e(t)(x(t),v(t))&=\begin{cases}0,&|x(t)|\leq x_{\max},\\-\operatorname{sgn}(x(t))k_e(|x(t)|-x_{\max})-c_e v(t),&|x(t)|>x_{\max},\end{cases} \\
   F_a(t)&=F(t)-c_tv(t)+F_e(t)(x(t),v(t)) \\
   r_1(t)&=F_a(t)+ml\sin\theta(t)\,\omega(t)^2 \\
   r_2(t)&=-g\sin\theta(t)-\dfrac{c_p}{ml}\omega(t) \\
   \Delta(t)&=l\left(M+m\sin^2\theta(t)\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}(t)&=v(t) \\
   \dot{v}(t)&=\dfrac{lr_1(t)-ml\cos\theta(t)\,r_2(t)}{\Delta(t)} \\
   \dot{\theta}(t)&=\omega(t) \\
   \dot{\omega}(t)&=\dfrac{(M+m)r_2(t)-\cos\theta(t)\,r_1(t)}{\Delta(t)} \\
   \dot{F}(t)&=\dfrac{F_{\mathrm{cmd}}(t)-F(t)}{\tau_F}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(trolley-drive command)},\\
   y(t)=x_L(t)=x(t)+\ell\sin\theta(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/overhead_crane_payload_sway.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`M`
     - ``trolley_mass``
     - ``1.8``
     - Mass of the crane trolley.
   * - :math:`m`
     - ``payload_mass``
     - ``0.45``
     - Suspended payload mass.
   * - :math:`l`
     - ``cable_length``
     - ``0.75``
     - Length of the rigid massless suspension cable.
   * - :math:`g`
     - ``gravity``
     - ``9.81``
     - Gravitational acceleration used in the crane pendulum equations.
   * - :math:`c_t`
     - ``trolley_damping``
     - ``0.32``
     - Viscous damping coefficient acting on trolley velocity.
   * - :math:`c_p`
     - ``pivot_damping``
     - ``0.035``
     - Damping coefficient opposing payload swing rate.
   * - :math:`F_{\max}`
     - ``drive_force_max``
     - ``14.0``
     - Symmetric saturation limit of the actuator force.
   * - :math:`\tau_F`
     - ``drive_tau``
     - ``0.035``
     - First-order time constant of the force actuator.
   * - :math:`x_{\max}`
     - ``travel_limit``
     - ``1.5``
     - Absolute trolley-position limit at which the nonlinear end stop becomes active.
   * - :math:`k_e`
     - ``end_stop_stiffness``
     - ``250.0``
     - Stiffness of the nonlinear end-stop restoring force outside the travel limit.
   * - :math:`c_e`
     - ``end_stop_damping``
     - ``8.0``
     - Damping of the end-stop force when the trolley moves into the stop.

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
     - Trolley-drive command
   * - :math:`x_L(t)`
     - ``y`` / ``payload_position``
     - Horizontal payload position
   * - :math:`x(t)`
     - ``trolley_position``
     - Trolley position
   * - :math:`v(t)`
     - ``trolley_velocity``
     - Trolley velocity
   * - :math:`\theta(t)`
     - ``sway_angle``
     - Payload sway angle
   * - :math:`\omega(t)`
     - ``sway_rate``
     - Payload sway rate
   * - :math:`y_L(t)`
     - ``payload_vertical_position``
     - Payload vertical position
   * - :math:`F(t)`
     - ``drive_force``
     - Trolley drive force
   * - :math:`F_e(t)`
     - ``end_stop_force``
     - Travel-limit force
   * - :math:`x(t)`
     - ``x``
     - Trolley-position state.
   * - :math:`v(t)`
     - ``v``
     - Velocity state associated with the corresponding position state.
   * - :math:`\theta(t)`
     - ``theta``
     - Payload sway-angle state.
   * - :math:`\omega(t)`
     - ``omega``
     - Angular velocity state.
   * - :math:`F(t)`
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
   * - :math:`F_{\mathrm{cmd}}`
     - ``F_mathrmcmd``
     - Saturated actuator-force command generated from the control input.
   * - :math:`F_e(x,v)`
     - ``F_e(x,v)``
     - Nonlinear end-stop force as a function of trolley position and velocity.
   * - :math:`F_a(t)`
     - ``F_a``
     - Actuator force applied to the plant.
   * - :math:`r_1(t)`
     - ``r_1``
     - First geometric or dynamic coupling coefficient used in the crane equations.
   * - :math:`r_2(t)`
     - ``r_2``
     - Second geometric or dynamic coupling coefficient used in the crane equations.
   * - :math:`\Delta(t)`
     - ``Delta``
     - Common denominator of the coupled crane acceleration equations.
   * - :math:`y(t)`
     - ``y``
     - Selected crane output combining trolley position and payload sway according to the output equation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `A. M. M. Abdel-Rahman, A. H. Nayfeh and Z. N. Masoud, Dynamics and Control of Cranes: A Review. <https://doi.org/10.1155/2003/89446>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       # [trolley_position, trolley_velocity, sway_angle, sway_rate, drive_force]
       return np.zeros(5, dtype=float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x, v, theta, omega, force = chi[:5]
       payload_x = x + par.cable_length * np.sin(theta)
       payload_y = -par.cable_length * np.cos(theta)
       return {
           "payload_position": payload_x,
           "trolley_position": x,
           "trolley_velocity": v,
           "sway_angle": theta,
           "sway_rate": omega,
           "payload_vertical_position": payload_y,
           "drive_force": force,
           "end_stop_force": _end_stop_force(x, v, par),
       }

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x, v, theta, omega, force = chi[:5]
       M = par.trolley_mass
       m = par.payload_mass
       l = par.cable_length
       s = np.sin(theta)
       c = np.cos(theta)
   
       force_cmd = par.drive_force_max * np.tanh(float(u))
       applied_force = force - par.trolley_damping * v + _end_stop_force(x, v, par)
   
       rhs_1 = applied_force + m * l * s * omega**2
       rhs_2 = -par.gravity * s - (par.pivot_damping / (m * l)) * omega
       det = l * (M + m * s**2)
       x_ddot = (l * rhs_1 - m * l * c * rhs_2) / det
       theta_ddot = ((M + m) * rhs_2 - c * rhs_1) / det
   
       return np.array([v, x_ddot, omega, theta_ddot, (force_cmd - force) / par.drive_tau], dtype=float)
