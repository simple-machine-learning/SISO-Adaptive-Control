IT: cloud-server workload with delay
====================================

Python model: ``plant_models.cloud_server_workload_with_delay``

Description
-----------

Delayed-input variant of ``cloud_server_workload``.

The transport delay is represented by an 4-stage cascaded lag (Erlang
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
     - Compute-capacity command
   * - Output
     - :math:`\Delta \tau`
     - ``y`` / ``latency_deviation``
     - Response-time deviation

Input-output connection
-----------------------

The external command :math:`u(t)` first passes through the delay cascade.  With
:math:`u_d=z_{n_d}`, the base cloud-server model receives :math:`u_d(t)` in place
of :math:`u(t)`.  The physical states and controlled output then satisfy

.. math::

   c_{\mathrm{cmd}}(t)=c_0+k_c\tanh(u_d(t)),\qquad
   \tau(t)=k_Lx(t),\qquad
   y(t)=\Delta\tau(t)=k_L(x(t)-x_0).

Thus

.. math::

   u(t)\;\longrightarrow\;z_1(t),\ldots,z_{n_d}(t)\;\longrightarrow\;u_d(t)
   \;\longrightarrow\;c(t)\;\longrightarrow\;x(t)
   \;\longrightarrow\;y(t)=\Delta\tau(t).


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The augmented state consists of the physical-model state vector :math:`\mathbf{x}_{p}(t)` and the delay-chain states :math:`z_1(t),\ldots,z_{n_d}(t)`:

.. math::

   \mathbf{x}(t)=\begin{bmatrix}\mathbf{x}_{p}(t)^{\mathsf T}&z_1(t)&\cdots&z_{n_d}(t)\end{bmatrix}^{\mathsf T}.

This model uses the same physical equations as :doc:`cloud_server_workload`, but the commanded input is passed through an :math:`n_d`-stage first-order lag cascade. Let :math:`u_0=u(t)` and let :math:`z_i(t)` denote the state of delay stage :math:`i`.

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

The continuous-time state equations are given below.

Output equation
~~~~~~~~~~~~~~~

The base plant receives :math:`u_d(t)=z_{n_d}(t)` instead of :math:`u(t)`. Thus the complete state is the physical state of the base model augmented by :math:`[z_1(t),\ldots,z_{n_d}(t)]^\mathsf{T}`. The cascade is a finite-dimensional approximation of the configured input delay.

The response-time proxy and controlled output are

.. math::

   \begin{aligned}
   \tau(t)&=k_Lx(t),\\
   y(t)&=\Delta\tau(t)=\tau(t)-\tau_0=k_L(x(t)-x_0).
   \end{aligned}

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(undelayed compute-capacity command)},\\
   y(t)=\Delta\tau(t)=\tau(t)-\tau_0=k_L\bigl(x(t)-x_0\bigr).
   \end{aligned}

Parameter implementation
------------------------

The delay-specific defaults are defined in ``apps/simulated/plant_models/cloud_server_workload_with_delay.py``. Its ``PlantParams`` class inherits the physical-model parameters from ``apps/simulated/plant_models/cloud_server_workload.py`` and adds the delay parameters, such as ``input_delay_sec`` and ``delay_order``. The function ``default_params()`` returns the combined default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`x_0`
     - ``backlog_nom``
     - ``8.0``
     - Initial or nominal pending-work backlog.
   * - :math:`\lambda`
     - ``arrival_rate``
     - ``5.0``
     - External work-arrival rate.
   * - :math:`c_0`
     - ``service_nom``
     - ``5.0``
     - Nominal server service rate.
   * - :math:`k_c`
     - ``service_gain``
     - ``3.0``
     - Gain from normalized control input to additional service capacity.
   * - :math:`\tau_c`
     - ``tau_capacity``
     - ``1.5``
     - First-order time constant of provisioned server capacity.
   * - :math:`K_s`
     - ``half_saturation``
     - ``2.0``
     - Backlog at which the nonlinear service-utilization term reaches half of its asymptotic value.
   * - :math:`k_a`
     - ``abandonment``
     - ``0.03``
     - Rate at which queued work abandons or expires.
   * - :math:`k_L`
     - ``latency_gain``
     - ``0.18``
     - Conversion from backlog to reported service latency.
   * - :math:`\tau_d(t)`
     - ``input_delay_sec``
     - ``8.0``
     - Mean transport delay represented by the cascaded first-order delay states.
   * - :math:`n_d`
     - ``delay_order``
     - ``4``
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
     - Compute-capacity command
   * - :math:`\Delta \tau`
     - ``y`` / ``latency_deviation``
     - Response-time deviation
   * - :math:`x(t)`
     - ``backlog``
     - Pending workload
   * - :math:`c(t)`
     - ``allocated_capacity``
     - Allocated compute capacity
   * - :math:`s(x,c)`
     - ``service_rate``
     - Completed workload rate
   * - :math:`\tau(t)`
     - ``response_time``
     - Response-time proxy
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
     - Delayed server-response-time deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `L. Kleinrock, Queueing Systems, Volume 1: Theory (fluid backlog and response-time foundations). <https://www.wiley.com/en-us/Queueing+Systems%2C+Volume+1%3A+Theory-p-9780471491101>`_
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
