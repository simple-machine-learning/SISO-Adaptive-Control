Drone: quadrotor roll
=====================

Python model: ``plant_models.quadrotor_roll``

Description
-----------

Quadrotor roll channel with actuator lag and changing inertia.
state vector :math:`\mathbf{x}` = [phi,omega,tau,J,0,0,0], y2=phi.

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
     - Roll-torque command
   * - Output
     - :math:`\phi(t)`
     - ``y`` / ``roll``
     - Roll angle


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[\phi(t),\,\omega(t),\,\tau(t),\,J(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   J_{\mathrm{target}}(t)&=J_0+\begin{cases}0,&t<t_c,\\ \Delta J(t),&t\geq t_c,\end{cases} \\
   \tau_{\mathrm{cmd}}(t)&=k_\tau\tanh(u(t)) \\
   \tau_d(t)&=A_d\sin\!\left(\dfrac{2\pi t}{T_d}\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{\phi}(t)&=\omega(t) \\
   \dot{\omega}(t)&=\dfrac{\tau(t)-c\omega(t)-k_\phi\phi(t)-c_n\omega(t)|\omega(t)|+\tau_d(t)}{J(t)} \\
   \dot{\tau}(t)&=\dfrac{\tau_{\mathrm{cmd}}(t)-\tau(t)}{\tau_a} \\
   \dot{J}(t)&=\dfrac{J_{\mathrm{target}}(t)-J(t)}{0.20}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(roll-torque command)},\\
   y(t)=\phi(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/quadrotor_roll.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`J_0`
     - ``J0``
     - ``0.022``
     - Nominal roll-axis moment of inertia.
   * - :math:`\Delta J(t)`
     - ``J_delta``
     - ``0.008``
     - Increment in roll-axis inertia applied at the scheduled change time.
   * - :math:`t_c`
     - ``change_time``
     - ``60.0``
     - Simulation time at which the scheduled parameter change is applied.
   * - :math:`\tau_a`
     - ``tau_act``
     - ``0.06``
     - Actuator first-order time constant.
   * - :math:`k_\tau`
     - ``torque_gain``
     - ``0.16``
     - Gain from normalized control input to actuator torque.
   * - :math:`c`
     - ``damping``
     - ``0.025``
     - Linear angular-velocity damping coefficient.
   * - :math:`c_n`
     - ``nonlinear_drag``
     - ``0.01``
     - Coefficient of nonlinear angular-velocity drag.
   * - :math:`A_d`
     - ``disturbance_amp``
     - ``0.015``
     - Amplitude of the periodic external disturbance torque.
   * - :math:`T_d`
     - ``disturbance_period``
     - ``13.0``
     - Period of the periodic external disturbance.
   * - :math:`k_\phi`
     - ``attitude_stiffness``
     - ``0.12``
     - Restoring-torque coefficient proportional to roll angle.

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
     - Roll-torque command
   * - :math:`\phi(t)`
     - ``y`` / ``roll``
     - Roll angle
   * - :math:`\omega(t)`
     - ``roll_rate``
     - Roll rate
   * - :math:`\tau(t)`
     - ``torque``
     - Roll torque
   * - :math:`J(t)`
     - ``inertia``
     - Roll inertia
   * - :math:`\phi(t)`
     - ``phi``
     - Roll-angle state.
   * - :math:`\omega(t)`
     - ``w``
     - Roll angular-velocity state.
   * - :math:`\tau(t)`
     - ``tau``
     - Actual actuator torque state after the first-order torque dynamics.
   * - :math:`J(t)`
     - ``J``
     - Time-varying roll-axis moment-of-inertia state.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`J_{\mathrm{target}}(t)`
     - ``J_mathrmtarget``
     - Time-varying target inertia used as an external scheduling signal in the roll model.
   * - :math:`\tau_{\mathrm{cmd}}`
     - ``tau_mathrmcmd``
     - Saturated roll-torque command generated from the control input.
   * - :math:`\tau_d(t)`
     - ``tau_d``
     - External roll-disturbance torque.
   * - :math:`y(t)`
     - ``y``
     - Quadrotor roll-angle deviation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `S. Bouabdallah, Design and Control of Quadrotors with Application to Autonomous Flying. <https://infoscience.epfl.ch/record/95939>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([0,0,0,par.J0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       phi,w,tau,J=chi[:4]
       return {"roll":phi,"roll_rate":w,"torque":tau,"inertia":J}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       phi,w,tau,J=chi[:4]; Jtarget=par.J0+(par.J_delta if t>=par.change_time else 0.0)
       taucmd=par.torque_gain*np.tanh(u); dist=par.disturbance_amp*np.sin(2*np.pi*t/par.disturbance_period)
       return np.array([w,(tau-par.damping*w-par.attitude_stiffness*phi-par.nonlinear_drag*w*abs(w)+dist)/J,
                        (taucmd-tau)/par.tau_act,(Jtarget-J)/0.20,0,0,0],float)
