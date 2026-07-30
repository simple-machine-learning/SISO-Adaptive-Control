Bioprocess: dissolved oxygen bioreactor
=======================================

Python model: ``plant_models.bioreactor_dissolved_oxygen``

Description
-----------

Stirred-tank bioreactor: dissolved oxygen control by agitation command.

state vector :math:`\mathbf{x}` = [C, X, N, OUR, 0, 0, 0]. Controlled output y2 = C-C0.
The command u is a dimensionless deviation; N_cmd=N0+N_gain*tanh(u).

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
     - Agitation command
   * - Output
     - :math:`\Delta C_{\mathrm{O_2}}`
     - ``y`` / ``C_O2_deviation``
     - Dissolved oxygen deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[C(t),\,X(t),\,N(t),\,OUR(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   N_{\mathrm{cmd}}(t)&=N_0+k_N\tanh(u(t)) \\
   k_La(t)&=k_{La,0}+k_{La,1}N(t)+k_{La,2}N(t)^2 \\
   \mu(C(t))&=\mu_{\max}\dfrac{C(t)}{K_{O_2}+C(t)} \\
   OUR_{\mathrm{ss}}(t)&=q_{O_2}X(t)\dfrac{C(t)}{K_{O_2}+C(t)}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}(t)&=k_La(t)(C(t)^\ast-C(t))-OUR(t) \\
   \dot{X}(t)&=\left(\mu(C(t))-k_d\right)X(t) \\
   \dot{N}(t)&=\dfrac{N_{\mathrm{cmd}}(t)-N(t)}{\tau_N} \\
   \dot{OUR}(t)&=\dfrac{OUR_{\mathrm{ss}}(t)-OUR(t)}{\tau_{OUR}}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(agitation command)},\\
   y(t)=\Delta C_{\mathrm{O_2}}(t)=C(t)-C_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/bioreactor_dissolved_oxygen.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`C^{\ast}`
     - ``C_star``
     - ``1.0``
     - Saturation dissolved-oxygen concentration.
   * - :math:`C_0`
     - ``C0``
     - ``0.55``
     - Initial dissolved-oxygen concentration and operating-point value used in the output deviation :math:`y=C-C_0`.
   * - :math:`X_0`
     - ``X0``
     - ``1.0``
     - Initial biomass concentration.
   * - :math:`N_0`
     - ``N0``
     - ``0.55``
     - Initial agitation-speed state about which the command law is defined.
   * - :math:`k_N`
     - ``N_gain``
     - ``0.35``
     - Gain from normalized input :math:`u(t)` to the commanded agitation speed :math:`N_{\mathrm{cmd}}(t)`.
   * - :math:`\tau_N`
     - ``tau_N``
     - ``0.3``
     - First-order time constant of the agitation actuator.
   * - :math:`k_{La,0}`
     - ``kla0``
     - ``0.12``
     - Baseline volumetric oxygen-transfer coefficient.
   * - :math:`k_{La,1}`
     - ``kla1``
     - ``0.55``
     - Linear control-dependent contribution to the oxygen-transfer coefficient.
   * - :math:`k_{La,2}`
     - ``kla2``
     - ``0.18``
     - Quadratic control-dependent contribution to the oxygen-transfer coefficient.
   * - :math:`q_{O_2}`
     - ``qO2``
     - ``0.24``
     - Specific cellular oxygen-consumption coefficient.
   * - :math:`\mu_{\max}`
     - ``mu_max``
     - ``0.01``
     - Maximum specific biological growth rate.
   * - :math:`K_{O_2}`
     - ``K_O2``
     - ``0.2``
     - Dissolved-oxygen half-saturation constant for growth.
   * - :math:`k_d`
     - ``k_decay``
     - ``0.004``
     - First-order biomass decay rate.
   * - :math:`\tau_{OUR}`
     - ``tau_our``
     - ``0.7``
     - First-order time constant of the reported oxygen-uptake-rate state.

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
     - Agitation command
   * - :math:`C-C_0(t)`
     - ``y`` / ``C_O2_deviation``
     - Dissolved oxygen deviation
   * - :math:`C(t)`
     - ``C_O2``
     - Dissolved oxygen
   * - :math:`X(t)`
     - ``biomass``
     - Biomass concentration
   * - :math:`N(t)`
     - ``agitation``
     - Agitation speed
   * - :math:`k_La(t)`
     - ``kla``
     - Oxygen transfer coefficient
   * - :math:`OUR(t)`
     - ``OUR``
     - Oxygen uptake rate
   * - :math:`C(t)`
     - ``C``
     - Dissolved-oxygen concentration state used in the oxygen-transfer and Monod terms.
   * - :math:`X(t)`
     - ``X``
     - Biomass concentration.
   * - :math:`N(t)`
     - ``N``
     - Actual agitation-speed state after the first-order actuator dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`\mu(C)`
     - ``mu(C)``
     - Specific oxygen-consumption or growth-rate function evaluated at dissolved oxygen concentration.
   * - :math:`OUR_{\mathrm{ss}}(t)`
     - ``OUR_mathrmss``
     - Steady-state oxygen uptake rate used to define the deviation output.
   * - :math:`y(t)`
     - ``y``
     - Dissolved-oxygen deviation from its steady-state value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `F. Garcia-Ochoa and E. Gomez, Bioreactor scale-up and oxygen transfer rate in microbial processes. <https://doi.org/10.1016/j.biotechadv.2009.10.006>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       our0=par.qO2*par.X0*par.C0/(par.K_O2+par.C0)
       return np.array([par.C0,par.X0,par.N0,our0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       C,X,N,OUR=chi[:4]; kla=par.kla0+par.kla1*N+par.kla2*N*N
       return {"C_O2":C,"C_O2_deviation":C-par.C0,"biomass":X,"agitation":N,"kla":kla,"OUR":OUR}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       C,X,N,OUR=chi[:4]; Ncmd=par.N0+par.N_gain*np.tanh(u)
       kla=par.kla0+par.kla1*N+par.kla2*N*N
       mu=par.mu_max*C/(par.K_O2+C)
       OURss=par.qO2*X*C/(par.K_O2+C)
       return np.array([kla*(par.C_star-C)-OUR, (mu-par.k_decay)*X,
                        (Ncmd-N)/par.tau_N,(OURss-OUR)/par.tau_our,0,0,0],float)
