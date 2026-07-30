Bioprocess: Monod chemostat biomass
===================================

Python model: ``plant_models.chemostat_monod_biomass``

Description
-----------

Chemostat with Monod kinetics: biomass control by dilution-rate command.
state vector :math:`\mathbf{x}` = [X,S,D,0,0,0,0], y2=X-X0.

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
     - Dilution-rate command
   * - Output
     - :math:`\Delta X(t)`
     - ``y`` / ``biomass_deviation``
     - Biomass deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[X(t),\,S(t),\,D(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   D_{\mathrm{cmd}}(t)&=\max\!\left(0.01,\,D_0+k_D\tanh(u(t))\right) \\
   \mu(t)(S(t))&=\mu_{\max}\dfrac{S(t)}{K_S+S(t)}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{X}(t)&=\left(\mu(t)(S(t))-D(t)-k_d\right)X(t) \\
   \dot{S}(t)&=D(t)(S_{\mathrm{in}}-S(t))-\dfrac{\mu(t)(S(t))}{Y_{X/S}}X(t) \\
   \dot{D}(t)&=\dfrac{D_{\mathrm{cmd}}(t)-D(t)}{\tau_D}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(dilution-rate command)},\\
   y(t)=\Delta X(t)=X(t)-X_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/chemostat_monod_biomass.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`X_0`
     - ``X0``
     - ``0.6``
     - Initial biomass concentration.
   * - :math:`S_0`
     - ``S0``
     - ``0.4``
     - Initial substrate concentration.
   * - :math:`D_0`
     - ``D0``
     - ``0.18``
     - Initial dilution-rate state.
   * - :math:`k_D`
     - ``D_gain``
     - ``0.12``
     - Gain from normalized input to dilution-rate command.
   * - :math:`\tau_D`
     - ``tau_D``
     - ``0.25``
     - First-order time constant of dilution-rate dynamics.
   * - :math:`\mu_{\max}`
     - ``mu_max``
     - ``0.55``
     - Maximum specific biological growth rate.
   * - :math:`K_S`
     - ``K_S``
     - ``0.18``
     - Substrate half-saturation constant in the Monod growth law.
   * - :math:`k_d`
     - ``k_decay``
     - ``0.015``
     - First-order biomass decay rate.
   * - :math:`Y_{X/S}`
     - ``Y_XS``
     - ``0.62``
     - Biomass yield per consumed substrate.
   * - :math:`S_{\mathrm{in}}`
     - ``S_in``
     - ``1.0``
     - Substrate concentration in the inlet stream.

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
     - Dilution-rate command
   * - :math:`X-X_0(t)`
     - ``y`` / ``biomass_deviation``
     - Biomass deviation
   * - :math:`X(t)`
     - ``biomass``
     - Biomass concentration
   * - :math:`S(t)`
     - ``substrate``
     - Substrate concentration
   * - :math:`D(t)`
     - ``dilution``
     - Dilution rate
   * - :math:`\mu(t)`
     - ``growth_rate``
     - Specific growth rate
   * - :math:`X(t)`
     - ``X``
     - Biomass concentration.
   * - :math:`S(t)`
     - ``S``
     - Substrate concentration.
   * - :math:`D(t)`
     - ``D``
     - Actual dilution-rate state after actuator dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`D_{\mathrm{cmd}}(t)`
     - ``D_mathrmcmd``
     - Saturated dilution-rate command generated from the control input.
   * - :math:`\mu(S)`
     - ``mu(S)``
     - Monod specific growth-rate function evaluated at substrate concentration.
   * - :math:`y(t)`
     - ``y``
     - Biomass-concentration deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `J. Monod, The Growth of Bacterial Cultures. <https://doi.org/10.1146/annurev.mi.03.100149.002103>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.X0,par.S0,par.D0,0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       X,S,D=chi[:3]; mu=par.mu_max*S/(par.K_S+S)
       return {"biomass":X,"biomass_deviation":X-par.X0,"substrate":S,"dilution":D,"growth_rate":mu}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       X,S,D=chi[:3]; Dcmd=max(0.01,par.D0+par.D_gain*np.tanh(u)); mu=par.mu_max*S/(par.K_S+S)
       dX=(mu-D-par.k_decay)*X
       dS=D*(par.S_in-S)-(mu/par.Y_XS)*X
       return np.array([dX,dS,(Dcmd-D)/par.tau_D,0,0,0,0],float)
