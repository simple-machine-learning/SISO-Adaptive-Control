Soil ecology: carbon priming
============================

Python model: ``plant_models.soil_carbon_priming``

Description
-----------

Labile-carbon induced priming of stable soil organic matter.

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
     - Fresh-carbon addition command
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

   \mathbf{x}(t)=[C_l(t),\,C_s(t),\,B(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   C_l^+(t)&=[C_l(t)]_+,\quad C_s^+(t)=[C_s(t)]_+,\quad B^+(t)=[B(t)]_+ \\
   r_l(t)&=k_lB^+(t)\dfrac{C_l^+(t)}{K_l+C_l^+(t)+10^{-12}} \\
   P(t)&=1+k_p\dfrac{C_l^+(t)}{K_p+C_l^+(t)+10^{-12}} \\
   r_s(t)&=k_sP(t)B^+(t)\dfrac{C_s^+(t)}{K_s+C_s^+(t)+10^{-12}} \\
   F_C(t)&=F_0+k_F\tanh(u(t)) \\
   m_B(t)&=k_mB^+(t)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}_l(t)&=F_C(t)-r_l(t) \\
   \dot{C}_s(t)&=-r_s(t) \\
   \dot{B}(t)&=Y_lr_l(t)+Y_sr_s(t)-m_B(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The total respiration flux used by the controlled output is

.. math::

   R_{\mathrm{CO_2}}(t)=r_l(t)+r_s(t),

so that

.. math::

   y(t)=\Delta R_{\mathrm{CO_2}}(t)=R_{\mathrm{CO_2}}(t)-R_{\mathrm{CO_2},0}.

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_carbon_priming.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`labile_{nom}`
     - ``labile_nom``
     - ``0.35``
     - Initial or nominal value of labile used to initialize and scale this model.
   * - :math:`stable_{nom}`
     - ``stable_nom``
     - ``3.0``
     - Initial or nominal value of stable used to initialize and scale this model.
   * - :math:`biomass_{nom}`
     - ``biomass_nom``
     - ``0.28``
     - Initial or nominal value of biomass used to initialize and scale this model.
   * - :math:`k_{labile}`
     - ``k_labile``
     - ``0.22``
     - Rate, affinity, or half-saturation coefficient k_labile in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{stable}`
     - ``k_stable``
     - ``0.01``
     - Rate, affinity, or half-saturation coefficient k_stable in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`half_{labile}`
     - ``half_labile``
     - ``0.2``
     - Half-saturation scale in the nonlinear half labile response.
   * - :math:`half_{stable}`
     - ``half_stable``
     - ``1.0``
     - Half-saturation scale in the nonlinear half stable response.
   * - :math:`priming_{strength}`
     - ``priming_strength``
     - ``2.2``
     - Model parameter ``priming_strength``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`priming_{half}`
     - ``priming_half``
     - ``0.3``
     - Half-saturation scale in the nonlinear priming response.
   * - :math:`yield_{labile}`
     - ``yield_labile``
     - ``0.48``
     - Conversion yield relating consumed substrate/resource to produced labile.
   * - :math:`yield_{stable}`
     - ``yield_stable``
     - ``0.32``
     - Conversion yield relating consumed substrate/resource to produced stable.
   * - :math:`mortality`
     - ``mortality``
     - ``0.055``
     - First-order loss coefficient for mortality.
   * - :math:`feed_{nom}`
     - ``feed_nom``
     - ``0.03``
     - Initial or nominal value of feed used to initialize and scale this model.
   * - :math:`k_F`
     - ``feed_gain``
     - ``0.025``
     - Gain converting the normalized control input into the model-specific feed actuation term.
   * - :math:`respiration_{nom}`
     - ``respiration_nom``
     - ``0.028``
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
     - Fresh-carbon addition command
   * - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation
   * - :math:`CL(t)`
     - ``labile_carbon``
     - Labile carbon pool
   * - :math:`CS(t)`
     - ``stable_carbon``
     - Stable soil carbon pool
   * - :math:`B(t)`
     - ``microbial_biomass``
     - Microbial biomass
   * - :math:`fp(t)`
     - ``priming_factor``
     - Priming multiplier
   * - :math:`Rco_{2}(t)`
     - ``co2_flux``
     - Soil CO2 flux
   * - :math:`cl(t)`
     - ``cl``
     - Labile-carbon pool.
   * - :math:`cs(t)`
     - ``cs``
     - Stable-carbon pool.
   * - :math:`b(t)`
     - ``b``
     - Microbial biomass state.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`C_l(t)`
     - ``C_l``
     - Labile-carbon pool.
   * - :math:`C_s(t)`
     - ``C_s``
     - Slow-carbon pool.
   * - :math:`C_l^+(t)`
     - ``C_l^+(t)``
     - Nonnegative labile-carbon pool used in rate expressions.
   * - :math:`r_l(t)`
     - ``r_l``
     - Labile-carbon decomposition rate.
   * - :math:`P(t)`
     - ``P``
     - Priming multiplier for slow-carbon decomposition.
   * - :math:`r_s(t)`
     - ``r_s``
     - Slow-carbon decomposition rate.
   * - :math:`F_C(t)`
     - ``F_C``
     - External carbon-input flux generated from the control input.
   * - :math:`m_B(t)`
     - ``m_B``
     - Microbial maintenance or decay flux.
   * - :math:`R_{\mathrm{CO_2}}`
     - ``R_mathrmCO_2``
     - Total carbon-dioxide respiration rate.
   * - :math:`y(t)`
     - ``y``
     - Carbon-dioxide respiration-rate deviation from its baseline value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `Y. Kuzyakov, Priming effects: Interactions between living and dead organic matter. <https://doi.org/10.1016/j.soilbio.2010.04.003>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.labile_nom, par.stable_nom, par.biomass_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       cl, cs, b = chi[:3]
       rl, rs, prime = _rates(cl,cs,b,par)
       respiration = (1-par.yield_labile)*rl+(1-par.yield_stable)*rs+0.35*par.mortality*max(b,0.0)
       return {"respiration_deviation": respiration-par.respiration_nom,
               "labile_carbon": cl, "stable_carbon": cs, "microbial_biomass": b,
               "priming_factor": prime, "co2_flux": respiration}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       cl, cs, b = chi[:3]
       rl, rs, prime = _rates(cl,cs,b,par)
       mortality = par.mortality*max(b,0.0)
       feed = par.feed_nom+par.feed_gain*np.tanh(float(u))
       return np.array([feed-rl, -rs, par.yield_labile*rl+par.yield_stable*rs-mortality, 0.0], float)
