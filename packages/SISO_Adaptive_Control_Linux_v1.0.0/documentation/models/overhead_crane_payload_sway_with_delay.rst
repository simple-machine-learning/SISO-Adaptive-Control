Mechanical: overhead crane payload sway with delay
==================================================

Python model: ``plant_models.overhead_crane_payload_sway_with_delay``

Description
-----------

Delayed-input variant of ``overhead_crane_payload_sway``.

The transport delay is represented by an 3-stage cascaded lag (Erlang
transport approximation) with mean delay ``input_delay_sec``. This keeps the
plant in finite-dimensional ODE form while producing a substantially delayed,
smooth actuator command.

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

The augmented state consists of the physical-model state vector :math:`\mathbf{x}_{p}(t)` and the delay-chain states :math:`z_1(t),\ldots,z_{n_d}(t)`:

.. math::

   \mathbf{x}(t)=\begin{bmatrix}\mathbf{x}_{p}(t)^{\mathsf T}&z_1(t)&\cdots&z_{n_d}(t)\end{bmatrix}^{\mathsf T}.

This model uses the same physical equations as :doc:`overhead_crane_payload_sway`, but the commanded input is passed through an :math:`n_d`-stage first-order lag cascade. Let :math:`u_0=u(t)` and let :math:`z_i(t)` denote the state of delay stage :math:`i`.

.. math::

   \begin{aligned}
   \tau_s &= \frac{\tau_d(t)}{n_d}, \\
   \dot{z}_1(t) &= \frac{u(t)-z_1(t)}{\tau_s}, \\
   \dot{z}_i(t) &= \frac{z_{i-1}(t)-z_i(t)}{\tau_s},\qquad i=2,\ldots,n_d.
   \end{aligned}

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No additional static relation is required; the input enters directly in the state equations.

State equations
~~~~~~~~~~~~~~~

The base plant receives :math:`u_d(t)=z_{n_d}(t)` instead of :math:`u(t)`. Thus the complete state is the physical state of the base model augmented by :math:`[z_1(t),\ldots,z_{n_d}(t)]^\mathsf{T}`. The cascade is a finite-dimensional approximation of the configured input delay.

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(undelayed trolley-drive command)},\\
   y(t)=x_L(t)=x(t)+\ell\sin\theta(t).
   \end{aligned}

Parameter implementation
------------------------

The delay-specific defaults are defined in ``apps/simulated/plant_models/overhead_crane_payload_sway_with_delay.py``. Its ``PlantParams`` class inherits the physical-model parameters from ``apps/simulated/plant_models/overhead_crane_payload_sway.py`` and adds the delay parameters, such as ``input_delay_sec`` and ``delay_order``. The function ``default_params()`` returns the combined default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`\tau_d(t)`
     - ``input_delay_sec``
     - ``0.12``
     - Mean transport delay represented by the cascaded first-order delay states.
   * - :math:`n_d`
     - ``delay_order``
     - ``3``
     - Number of first-order sections used to approximate the transport delay; higher order gives a sharper delay approximation.

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
   * - :math:`u_{d}(t)`
     - ``effective_input``
     - Delayed effective input
   * - :math:`\tau_{d}(t)`
     - ``input_delay_sec``
     - Nominal input delay

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`\tau_s`
     - ``tau_s``
     - Time constant of one first-order section in the input-delay approximation.
   * - :math:`z_1(t)`
     - ``z_1``
     - First state of the cascaded input-delay approximation.
   * - :math:`y(t)`
     - ``y``
     - Selected crane output with delayed actuator force.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `A. M. M. Abdel-Rahman, A. H. Nayfeh and Z. N. Masoud, Dynamics and Control of Cranes: A Review. <https://doi.org/10.1155/2003/89446>`_
* `Erlang distribution / cascaded first-order lag approximation used for finite-dimensional transport delay. <https://en.wikipedia.org/wiki/Erlang_distribution>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       x0 = np.asarray(base.initial_state(par), dtype=float)
       return np.concatenate((x0, np.zeros(int(par.delay_order), dtype=float)))

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x, z = _split(chi, par)
       out = dict(base.algebraic_outputs(x, par))
       out["effective_input"] = float(z[-1]) if len(z) else 0.0
       out["input_delay_sec"] = float(par.input_delay_sec)
       return out

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x, z = _split(chi, par)
       order = max(1, int(par.delay_order))
       tau_stage = max(float(par.input_delay_sec) / order, 1.0e-12)
       dz = np.empty(order, dtype=float)
       source = float(u)
       for i in range(order):
           dz[i] = (source - z[i]) / tau_stage
           source = z[i]
       dx = np.asarray(base.rhs(t, x, float(z[-1]), par), dtype=float)
       return np.concatenate((dx, dz))
