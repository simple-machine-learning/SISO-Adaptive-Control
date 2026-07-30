Network: nonlinear router fluid queue
=====================================

Python model: ``plant_models.network_router_fluid_queue``

Description
-----------

Reduced fluid model of an actively controlled router queue.
The physical states are :math:`q(t)` (buffer occupancy) and :math:`r(t)` (admitted traffic rate).
The command u changes the admitted rate around the nominal link capacity.

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
     - Admission-rate command
   * - Output
     - :math:`\Delta q(t)`
     - ``y`` / ``queue_deviation``
     - Queue occupancy deviation, :math:`\Delta q=q-q_0`


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The two physical states are

.. math::

   \mathbf{x}_{\mathrm{phys}}(t)=[q(t),\,r(t)]^\mathsf{T}.

The Python state array also contains one constant compatibility entry. It is not a physical state and does not enter the model equations or output.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   r_{\mathrm{cmd}}(t)&=C+k_r\tanh(u(t)) \\
   s(q(t))&=C\left[s_0+(1-s_0)\left(1-\exp\!\left(-\dfrac{[q(t)]_+}{q_s}\right)\right)\right]
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{q}(t)&=r(t)-s(q(t))-k_\ell q(t) \\
   \dot{r}(t)&=\dfrac{r_{\mathrm{cmd}}(t)-r(t)}{\tau_r}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The input-state-output connection is

.. math::

   u(t) \longrightarrow r_{\mathrm{cmd}}(t) \longrightarrow r(t) \longrightarrow q(t)
   \longrightarrow y(t)=\Delta q(t)=q(t)-q_0.

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/network_router_fluid_queue.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`C`
     - ``capacity``
     - ``12.0``
     - Maximum router service capacity used in the queue outflow law.
   * - :math:`q_0`
     - ``q_nom``
     - ``4.0``
     - Initial or nominal queue length.
   * - :math:`q_s`
     - ``q_scale``
     - ``3.0``
     - Queue-length scale in the nonlinear service/latency relation.
   * - :math:`\tau_r`
     - ``tau_rate``
     - ``0.35``
     - First-order time constant of the commanded arrival/service-rate state.
   * - :math:`k_r`
     - ``rate_gain``
     - ``4.0``
     - Gain from normalized control input to the controllable packet-rate command.
   * - :math:`s_0`
     - ``service_floor``
     - ``0.15``
     - Minimum fraction of service capacity retained at low queue load.
   * - :math:`k_\ell`
     - ``leakage``
     - ``0.03``
     - Proportional packet-loss or queue-drain coefficient.
   * - :math:`q_{\max}`
     - ``q_max``
     - ``20.0``
     - Upper queue-length limit used by the model saturation logic.

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
     - Admission-rate command
   * - :math:`\Delta q(t)`
     - ``y`` / ``queue_deviation``
     - Queue occupancy deviation, :math:`\Delta q=q-q_0`
   * - :math:`q(t)`
     - ``queue``
     - Queue occupancy
   * - :math:`r_{\mathrm{in}}(t)`
     - ``admitted_rate``
     - Admitted traffic rate
   * - :math:`r_{\mathrm{out}}(t)`
     - ``service_rate``
     - Service rate
   * - :math:`\tau_q(t)`
     - ``delay``
     - Queueing-delay proxy
   * - :math:`q(t)`
     - ``q``
     - Queue/backlog state; this quantity determines the reported latency or queue output.
   * - :math:`r(t)`
     - ``r``
     - Actual controllable rate state after first-order actuator dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`r_{\mathrm{cmd}}`
     - ``r_mathrmcmd``
     - Saturated packet-arrival-rate command generated from the control input.
   * - :math:`s(q)`
     - ``s(q)``
     - Queue-dependent service-rate function.
   * - :math:`y(t)`
     - ``y``
     - Queue-length deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `C. V. Hollot et al., Analysis and design of controllers for AQM routers supporting TCP flows. <https://ieeexplore.ieee.org/document/1008360>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.q_nom, par.capacity, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       q, r = chi[:2]
       service = par.capacity * (par.service_floor + (1.0-par.service_floor)*(1.0-np.exp(-max(q,0.0)/par.q_scale)))
       return {"queue_deviation": q-par.q_nom, "queue": q, "admitted_rate": r,
               "service_rate": service, "delay": q/max(service,1.0e-9)}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       q, r = chi[:2]
       r_cmd = par.capacity + par.rate_gain*np.tanh(float(u))
       service = par.capacity * (par.service_floor + (1.0-par.service_floor)*(1.0-np.exp(-max(q,0.0)/par.q_scale)))
       dq = r-service-par.leakage*q
       if q <= 0.0 and dq < 0.0: dq = 0.0
       if q >= par.q_max and dq > 0.0: dq = 0.0
       return np.array([dq, (r_cmd-r)/par.tau_rate, 0.0], float)
