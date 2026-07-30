Soil ecology: moisture-controlled respiration
=============================================

Python model: ``plant_models.soil_moisture_respiration``

Description
-----------

Reduced soil-water and microbial-respiration SISO ODE benchmark.

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
     - Irrigation command
   * - Output
     - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[\theta(t),\,C(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   I(t)&=k_I\tanh(u(t)) \\
   D(t)&=k_D[\theta(t)-\theta_{fc}]_+^2 \\
   a(\theta(t))&=\exp\!\left[-\dfrac{1}{2}\left(\dfrac{\theta(t)-\theta_{opt}}{\sigma_\theta}\right)^2\right] \\
   R_C(t)&=k_cC^+(t)a(\theta(t))
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{\theta}(t)&=I(t)+k_e(\theta_0-\theta(t))-D(t) \\
   \dot{C}(t)&=F_C-R_C(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(irrigation command)},\\
   y(t)=\Delta R_{\mathrm{CO_2}}(t)=R_{\mathrm{CO_2}}(t)-R_{\mathrm{CO_2},0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_moisture_respiration.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`\theta_{nom}`
     - ``theta_nom``
     - ``0.55``
     - Initial or nominal value of theta used to initialize and scale this model.
   * - :math:`\theta_{opt}`
     - ``theta_opt``
     - ``0.58``
     - Optimal operating value at which the corresponding nonlinear response is maximal.
   * - :math:`\theta_{width}`
     - ``theta_width``
     - ``0.2``
     - Width parameter controlling how rapidly the corresponding nonlinear response decreases away from its optimum.
   * - :math:`carbon_{nom}`
     - ``carbon_nom``
     - ``1.0``
     - Initial or nominal value of carbon used to initialize and scale this model.
   * - :math:`carbon_{input}`
     - ``carbon_input``
     - ``0.018``
     - Constant exogenous carbon input entering the corresponding material balance.
   * - :math:`decay_{rate}`
     - ``decay_rate``
     - ``0.02``
     - Rate coefficient governing decay conversion or loss in this model.
   * - :math:`k_I`
     - ``irrigation_gain``
     - ``0.035``
     - Gain converting the normalized control input into the model-specific irrigation actuation term.
   * - :math:`evap_{rate}`
     - ``evap_rate``
     - ``0.01``
     - Rate coefficient governing evap conversion or loss in this model.
   * - :math:`drainage_{rate}`
     - ``drainage_rate``
     - ``0.16``
     - Rate coefficient governing drainage conversion or loss in this model.
   * - :math:`field_{capacity}`
     - ``field_capacity``
     - ``0.72``
     - Capacity or storage scaling associated with field.
   * - :math:`respiration_{nom}`
     - ``respiration_nom``
     - ``0.02``
     - Initial or nominal value of respiration used to initialize and scale this model.

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
     - Irrigation command
   * - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation
   * - :math:`\theta(t)`
     - ``soil_moisture``
     - Volumetric soil moisture
   * - :math:`Cs(t)`
     - ``available_carbon``
     - Available carbon
   * - :math:`Rco_{2}(t)`
     - ``co2_flux``
     - Soil CO2 flux
   * - :math:`ftheta(t)`
     - ``moisture_activity``
     - Moisture activity factor
   * - :math:`\theta(t)`
     - ``theta``
     - Volumetric soil-moisture state.
   * - :math:`carbon(t)`
     - ``carbon``
     - Soil-carbon pool state.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`C(t)`
     - ``C``
     - Respirable soil-carbon pool.
   * - :math:`I(t)`
     - ``I``
     - Moisture-dependent carbon-input rate.
   * - :math:`D(t)`
     - ``D``
     - Carbon-decomposition rate.
   * - :math:`a(\theta)`
     - ``a(theta)``
     - Moisture activity factor.
   * - :math:`R_C(t)`
     - ``R_C``
     - Soil-carbon respiration rate.
   * - :math:`y(t)`
     - ``y``
     - Soil respiration-rate deviation from its baseline value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `W. J. Parton et al., Analysis of factors controlling soil organic matter levels in Great Plains grasslands. <https://doi.org/10.2136/sssaj1987.03615995005100050015x>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.theta_nom, par.carbon_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       theta, carbon = chi[:2]
       activity = _activity(theta, par)
       respiration = par.decay_rate*max(carbon,0.0)*activity
       return {"respiration_deviation": respiration-par.respiration_nom,
               "soil_moisture": theta, "available_carbon": carbon,
               "co2_flux": respiration, "moisture_activity": activity}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       theta, carbon = chi[:2]
       irrigation = par.irrigation_gain*np.tanh(float(u))
       drainage = par.drainage_rate*max(theta-par.field_capacity, 0.0)**2
       dtheta = irrigation + par.evap_rate*(par.theta_nom-theta) - drainage
       activity = _activity(theta, par)
       respiration = par.decay_rate*max(carbon,0.0)*activity
       dcarbon = par.carbon_input-respiration
       return np.array([dtheta, dcarbon, 0.0], float)
