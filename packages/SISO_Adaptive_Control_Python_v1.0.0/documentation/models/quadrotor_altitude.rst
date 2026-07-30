Drone: quadrotor altitude
=========================

Python model: ``plant_models.quadrotor_altitude``

Description
-----------

Quadrotor vertical channel with motor lag, quadratic drag and payload change.
state vector :math:`\mathbf{x}` = [z,v,T,m,0,0,0], y2=z. Command u is collective-thrust deviation.

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
     - Collective-thrust command
   * - Output
     - :math:`z(t)`
     - ``y`` / ``altitude``
     - Altitude


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[z(t),\,v(t),\,T(t),\,m(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   m_{\mathrm{target}}(t)&=m_0+\begin{cases}0,&t<t_p,\\ \Delta m(t),&t\geq t_p,\end{cases} \\
   T_{\mathrm{cmd}}(t)&=\max\!\left(0,\,m_{\mathrm{target}}(t)g+k_T\tanh(u(t))\right) \\
   F_d(t)&=c_1v(t)+c_2v(t)|v(t)| \\
   F_w(t)&=A_w\sin\!\left(\dfrac{2\pi t}{T_w}\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{z}(t)&=v(t) \\
   \dot{v}(t)&=\dfrac{T(t)-m(t)g-F_d(t)-k_z z(t)+F_w(t)}{m(t)} \\
   \dot{T}(t)&=\dfrac{T_{\mathrm{cmd}}(t)-T(t)}{\tau_T} \\
   \dot{m}(t)&=\dfrac{m_{\mathrm{target}}(t)-m(t)}{0.25}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(collective-thrust command)},\\
   y(t)=z(t).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/quadrotor_altitude.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`m_0`
     - ``m0``
     - ``1.2``
     - Nominal quadrotor mass before the scheduled payload change.
   * - :math:`g`
     - ``g``
     - ``9.81``
     - Gravitational acceleration used in the vertical force balance.
   * - :math:`\tau_T`
     - ``tau_motor``
     - ``0.1``
     - Motor/thrust first-order time constant.
   * - :math:`k_T`
     - ``thrust_gain``
     - ``5.0``
     - Gain from normalized control input to commanded rotor thrust.
   * - :math:`c_1`
     - ``drag_linear``
     - ``0.35``
     - Coefficient of velocity-proportional aerodynamic drag.
   * - :math:`c_2`
     - ``drag_quadratic``
     - ``0.08``
     - Coefficient of quadratic aerodynamic drag.
   * - :math:`\Delta m(t)`
     - ``payload_delta``
     - ``0.25``
     - Mass increment applied at the scheduled payload-change time.
   * - :math:`t_p`
     - ``payload_time``
     - ``60.0``
     - Simulation time at which the payload mass changes.
   * - :math:`A_w`
     - ``wind_amp``
     - ``0.5``
     - Amplitude of the sinusoidal vertical wind-force disturbance.
   * - :math:`T_w`
     - ``wind_period``
     - ``17.0``
     - Period of the sinusoidal wind disturbance.
   * - :math:`k_z`
     - ``position_stiffness``
     - ``0.8``
     - Restoring-force coefficient proportional to altitude displacement.

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
     - Collective-thrust command
   * - :math:`h(t)`
     - ``y`` / ``altitude``
     - Altitude
   * - :math:`v(t)`
     - ``vertical_velocity``
     - Vertical velocity
   * - :math:`T(t)`
     - ``thrust``
     - Collective thrust
   * - :math:`m(t)`
     - ``mass``
     - Vehicle mass
   * - :math:`z(t)`
     - ``z``
     - LuGre internal bristle-deflection state used to compute friction force.
   * - :math:`v(t)`
     - ``v``
     - Velocity state associated with the corresponding position state.
   * - :math:`T(t)`
     - ``T``
     - Altitude state.
   * - :math:`m(t)`
     - ``m``
     - Vehicle-mass state.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`m_{\mathrm{target}}(t)`
     - ``m_mathrmtarget``
     - Time-varying target mass used as an external scheduling signal in the altitude model.
   * - :math:`T_{\mathrm{cmd}}`
     - ``T_mathrmcmd``
     - Saturated total-thrust command generated from the control input.
   * - :math:`F_d(t)`
     - ``F_d``
     - Aerodynamic drag force.
   * - :math:`F_w(t)`
     - ``F_w``
     - External vertical disturbance force.
   * - :math:`y(t)`
     - ``y``
     - Quadrotor altitude deviation from the reference operating point.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `S. Bouabdallah, Design and Control of Quadrotors with Application to Autonomous Flying. <https://infoscience.epfl.ch/record/95939>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([0,0,par.m0*par.g,par.m0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       z,v,T,m=chi[:4]
       return {"altitude":z,"vertical_velocity":v,"thrust":T,"mass":m}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       z,v,T,m=chi[:4]; mtarget=par.m0+(par.payload_delta if t>=par.payload_time else 0.0)
       Tcmd=max(0.0,mtarget*par.g+par.thrust_gain*np.tanh(u))
       drag=par.drag_linear*v+par.drag_quadratic*v*abs(v)
       wind=par.wind_amp*np.sin(2*np.pi*t/par.wind_period)
       return np.array([v,(T-m*par.g-drag-par.position_stiffness*z+wind)/m,(Tcmd-T)/par.tau_motor,(mtarget-m)/0.25,0,0,0],float)
