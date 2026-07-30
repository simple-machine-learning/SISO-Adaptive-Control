Bioprocess: photobioreactor pH / CO2
====================================

Python model: ``plant_models.photobioreactor_ph_co2``

Description
-----------

Photobioreactor: pH control by CO2 dosing with light-driven uptake.
state vector :math:`\mathbf{x}` = [C_CO2, X, Q_CO2, I, pH_filter,0,0], y2=pH-pH0.

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
     - CO2 dosing command
   * - Output
     - :math:`\Delta\mathrm{pH}`
     - ``y`` / ``pH_deviation``
     - pH deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[C(t),\,X(t),\,Q(t),\,I(t),\,pH(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   Q_{\mathrm{cmd}}(t)&=Q_0+k_Q\tanh(u(t)) \\
   I_{\mathrm{target}}(t)&=I_0+A_I\sin\!\left(\dfrac{2\pi t}{T_I}\right) \\
   r_p(t)&=v_{\max}X(t)\dfrac{I(t)}{K_I+I(t)}\dfrac{C(t)}{K_C+C(t)} \\
   C_g(t)&=k_gQ(t) \\
   pH_{\mathrm{eq}}(t)&=pH_0-\beta_{pH}(C(t)-C_0) \\
   \mu(t)&=\mu_{\max}\dfrac{I(t)}{K_I+I(t)}\dfrac{C(t)}{K_C+C(t)}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}(t)&=k_La(C_g(t)-C(t))-r_p(t) \\
   \dot{X}(t)&=(\mu(t)-k_d)X(t) \\
   \dot{Q}(t)&=\dfrac{Q_{\mathrm{cmd}}(t)-Q(t)}{\tau_Q} \\
   \dot{I}(t)&=\dfrac{I_{\mathrm{target}}(t)-I(t)}{0.5} \\
   \dot{pH}(t)&=\dfrac{pH_{\mathrm{eq}}(t)-pH(t)}{\tau_{pH}}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(CO_2 dosing command)},\\
   y(t)=\Delta pH(t)=pH(t)-pH_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/photobioreactor_ph_co2.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`C_0`
     - ``C0``
     - ``0.35``
     - Initial dissolved concentration/state specified by the model context.
   * - :math:`X_0`
     - ``X0``
     - ``0.8``
     - Initial biomass concentration.
   * - :math:`Q_0`
     - ``Q0``
     - ``0.25``
     - Initial gas/flow actuator state.
   * - :math:`I_0`
     - ``I0``
     - ``0.65``
     - Nominal incident-light intensity.
   * - :math:`pH_0`
     - ``pH0``
     - ``7.2``
     - Initial or nominal culture pH.
   * - :math:`k_Q`
     - ``Q_gain``
     - ``0.22``
     - Gain from normalized input to gas-flow command.
   * - :math:`\tau_Q`
     - ``tau_Q``
     - ``0.25``
     - First-order time constant of gas-flow dynamics.
   * - :math:`k_La`
     - ``kla``
     - ``0.45``
     - Volumetric gas-liquid mass-transfer coefficient.
   * - :math:`k_g`
     - ``C_gas_gain``
     - ``1.15``
     - Gain converting gas-flow state to equilibrium dissolved CO2 concentration.
   * - :math:`v_{\max}`
     - ``uptake_max``
     - ``0.18``
     - Maximum cellular CO2 uptake rate.
   * - :math:`K_C`
     - ``K_C``
     - ``0.2``
     - CO2 half-saturation constant for uptake.
   * - :math:`K_I`
     - ``K_I``
     - ``0.25``
     - Light half-saturation constant for growth or uptake.
   * - :math:`\mu_{\max}`
     - ``mu_max``
     - ``0.006``
     - Maximum specific biological growth rate.
   * - :math:`k_d`
     - ``k_decay``
     - ``0.002``
     - First-order biomass decay rate.
   * - :math:`\beta_{pH}`
     - ``beta_pH``
     - ``1.35``
     - Sensitivity of pH equilibrium to dissolved CO2.
   * - :math:`\tau_{pH}`
     - ``tau_pH``
     - ``0.2``
     - First-order pH-response time constant.
   * - :math:`A_I`
     - ``light_amp``
     - ``0.18``
     - Amplitude of the periodic light-intensity variation.
   * - :math:`T_I`
     - ``light_period``
     - ``60.0``
     - Period of the light-intensity variation.

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
     - CO2 dosing command
   * - :math:`pH(t)`
     - ``y`` / ``pH_deviation``
     - pH deviation
   * - :math:`pH(t)`
     - ``pH``
     - pH
   * - :math:`C(t)`
     - ``CO2``
     - Dissolved CO2
   * - :math:`X(t)`
     - ``biomass``
     - Biomass concentration
   * - :math:`Q(t)`
     - ``CO2_flow``
     - CO2 flow
   * - :math:`I(t)`
     - ``light``
     - Light intensity
   * - :math:`C(t)`
     - ``C``
     - Dissolved-CO2 concentration state.
   * - :math:`X(t)`
     - ``X``
     - Biomass concentration.
   * - :math:`Q(t)`
     - ``Q``
     - Actual gas-flow or infusion-flow state after actuator dynamics.
   * - :math:`I(t)`
     - ``I``
     - Light-intensity state following the imposed illumination profile.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`Q_{\mathrm{cmd}}`
     - ``Q_mathrmcmd``
     - Saturated carbon-dioxide flow command generated from the control input.
   * - :math:`I_{\mathrm{target}}`
     - ``I_mathrmtarget``
     - Target light-intensity profile used by the photobioreactor model.
   * - :math:`r_p(t)`
     - ``r_p``
     - Photosynthetic or biological production rate.
   * - :math:`C_g(t)`
     - ``C_g``
     - Dissolved carbon-dioxide concentration in equilibrium with the gas phase.
   * - :math:`pH_{\mathrm{eq}}`
     - ``pH_mathrmeq``
     - Equilibrium pH associated with the current dissolved carbon-dioxide state.
   * - :math:`\mu(t)`
     - ``mu``
     - Specific biomass growth rate.
   * - :math:`y(t)`
     - ``y``
     - Culture pH deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `W. Stumm and J. J. Morgan, Aquatic Chemistry (carbonate equilibria and pH/CO2 relations). <https://www.wiley.com/en-us/Aquatic+Chemistry%3A+Chemical+Equilibria+and+Rates+in+Natural+Waters%2C+3rd+Edition-p-9780471511854>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.C0,par.X0,par.Q0,par.I0,par.pH0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       C,X,Q,I,pH=chi[:5]
       return {"CO2":C,"biomass":X,"CO2_flow":Q,"light":I,"pH":pH,"pH_deviation":pH-par.pH0}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       C,X,Q,I,pH=chi[:5]; Qcmd=par.Q0+par.Q_gain*np.tanh(u)
       Itarget=par.I0+par.light_amp*np.sin(2*np.pi*t/par.light_period)
       photo=par.uptake_max*X*(I/(par.K_I+I))*(C/(par.K_C+C))
       Cgas=par.C_gas_gain*Q
       pHeq=par.pH0-par.beta_pH*(C-par.C0)
       mu=par.mu_max*(I/(par.K_I+I))*(C/(par.K_C+C))
       return np.array([par.kla*(Cgas-C)-photo,(mu-par.k_decay)*X,
                        (Qcmd-Q)/par.tau_Q,(Itarget-I)/0.5,(pHeq-pH)/par.tau_pH,0,0],float)
