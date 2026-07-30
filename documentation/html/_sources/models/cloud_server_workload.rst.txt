IT: cloud-server workload
=========================

Python model: ``plant_models.cloud_server_workload``

Description
-----------

Aggregate cloud-server backlog with saturating service and actuator lag.

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

The controlled input :math:`u(t)` enters the capacity command
:math:`c_{\mathrm{cmd}}=c_0+k_c\tanh(u)`.  This command drives the state
:math:`c(t)` through :math:`\dot c=(c_{\mathrm{cmd}}-c)/\tau_c`.  The allocated
capacity :math:`c(t)` changes the service rate :math:`s(x,c)`, which drives the
backlog state :math:`x(t)`.  The reported response-time proxy and controlled
output are

.. math::

   \tau(t)=k_L x(t),\qquad y(t)=\Delta\tau(t)=\tau(t)-k_Lx_0=k_L(x(t)-x_0).

Hence the complete signal path is

.. math::

   u(t)\;\longrightarrow\;c_{\mathrm{cmd}}(t)\;\longrightarrow\;c(t)
   \;\longrightarrow\;s(x(t),c(t))\;\longrightarrow\;x(t)
   \;\longrightarrow\;y(t)=\Delta\tau(t).


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[x(t),\,c(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   c_{\mathrm{cmd}}(t)&=c_0+k_c\tanh(u(t)) \\
   s(x(t),c(t))&=\dfrac{[c(t)]_+[x(t)]_+}{K_s+[x(t)]_+} \\
   [r]_+&=\max(r,0)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{x}(t)&=\lambda-s(x(t),c(t))-k_a x(t) \\
   \dot{c}(t)&=\dfrac{c_{\mathrm{cmd}}(t)-c(t)}{\tau_c}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The implementation clips the backlog derivative at zero when :math:`x(t) \leq 0` and the unconstrained value of :math:`\dot{x}(t)` is negative.

The response-time proxy and controlled output are

.. math::

   \begin{aligned}
   \tau(t)&=k_Lx(t),\\
   y(t)&=\Delta\tau(t)=\tau(t)-\tau_0=k_L(x(t)-x_0).
   \end{aligned}

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(compute-capacity command)},\\
   y(t)=\Delta\tau(t)=\tau(t)-\tau_0=k_L\bigl(x(t)-x_0\bigr).
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/cloud_server_workload.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`x(t)`
     - ``x``
     - Pending-workload or backlog state.
   * - :math:`c(t)`
     - ``c``
     - Allocated compute-capacity state after first-order provisioning dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`c_{\mathrm{cmd}}(t)`
     - ``c_mathrmcmd``
     - Saturated server-capacity command generated from the control input.
   * - :math:`[r]_+`
     - ``[r]_+``
     - Nonnegative part of the incoming workload rate.
   * - :math:`y(t)`
     - ``y``
     - Server-response-time deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `L. Kleinrock, Queueing Systems, Volume 1: Theory (fluid backlog and response-time foundations). <https://www.wiley.com/en-us/Queueing+Systems%2C+Volume+1%3A+Theory-p-9780471491101>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.backlog_nom, par.service_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       x, c = chi[:2]
       service = c*x/(par.half_saturation+max(x,0.0))
       latency = par.latency_gain*x
       return {"latency_deviation": latency-par.latency_gain*par.backlog_nom,
               "backlog": x, "allocated_capacity": c, "service_rate": service,
               "response_time": latency}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       x, c = chi[:2]
       c_cmd = par.service_nom + par.service_gain*np.tanh(float(u))
       service = max(c,0.0)*max(x,0.0)/(par.half_saturation+max(x,0.0))
       dx = par.arrival_rate-service-par.abandonment*x
       if x <= 0.0 and dx < 0.0: dx = 0.0
       return np.array([dx, (c_cmd-c)/par.tau_capacity, 0.0], float)
