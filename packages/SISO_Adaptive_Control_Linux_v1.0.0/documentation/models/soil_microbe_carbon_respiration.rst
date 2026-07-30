Soil ecology: microbial carbon respiration
==========================================

Python model: ``plant_models.soil_microbe_carbon_respiration``

Description
-----------

Substrate-microbial-biomass carbon respiration benchmark.

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
     - Labile-carbon addition command
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

   \mathbf{x}(t)=[S(t),\,B(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   r_u(t)&=v_{\max}B(t)^+\dfrac{S^+(t)}{K_S+S^+(t)+10^{-12}} \\
   m_B(t)&=k_mB^+(t) \\
   F_S(t)&=F_0+k_F\tanh(u(t))
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{S}(t)&=F_S(t)-r_u(t)+k_rm_B(t) \\
   \dot{B}(t)&=Y r_u(t)-m_B(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(labile-carbon addition command)},\\
   y(t)=\Delta R_{\mathrm{CO_2}}(t)=R_{\mathrm{CO_2}}(t)-R_{\mathrm{CO_2},0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_microbe_carbon_respiration.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`substrate_{nom}`
     - ``substrate_nom``
     - ``1.2``
     - Initial or nominal value of substrate used to initialize and scale this model.
   * - :math:`biomass_{nom}`
     - ``biomass_nom``
     - ``0.3``
     - Initial or nominal value of biomass used to initialize and scale this model.
   * - :math:`vmax`
     - ``vmax``
     - ``0.18``
     - Maximum value of the vmax process or actuator term.
   * - :math:`k_{substrate}`
     - ``k_substrate``
     - ``0.45``
     - Rate, affinity, or half-saturation coefficient k_substrate in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`yield_{coeff}`
     - ``yield_coeff``
     - ``0.42``
     - Conversion yield relating consumed substrate/resource to produced coeff.
   * - :math:`mortality`
     - ``mortality``
     - ``0.045``
     - First-order loss coefficient for mortality.
   * - :math:`recycling`
     - ``recycling``
     - ``0.35``
     - Model parameter ``recycling``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`feed_{nom}`
     - ``feed_nom``
     - ``0.054``
     - Initial or nominal value of feed used to initialize and scale this model.
   * - :math:`k_F`
     - ``feed_gain``
     - ``0.03``
     - Gain converting the normalized control input into the model-specific feed actuation term.
   * - :math:`respiration_{nom}`
     - ``respiration_nom``
     - ``0.033``
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
     - Labile-carbon addition command
   * - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation
   * - :math:`Cs(t)`
     - ``labile_carbon``
     - Labile carbon pool
   * - :math:`B(t)`
     - ``microbial_biomass``
     - Microbial biomass
   * - :math:`ru(t)`
     - ``carbon_uptake``
     - Microbial carbon uptake
   * - :math:`Rco_{2}(t)`
     - ``co2_flux``
     - Soil CO2 flux
   * - :math:`s(t)`
     - ``s``
     - Substrate/resource state.
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
   * - :math:`S(t)`
     - ``S``
     - Available soil-carbon substrate.
   * - :math:`r_u(t)`
     - ``r_u``
     - Microbial substrate-uptake rate.
   * - :math:`m_B(t)`
     - ``m_B``
     - Microbial maintenance or decay flux.
   * - :math:`F_S(t)`
     - ``F_S``
     - External substrate-input flux.
   * - :math:`y(t)`
     - ``y``
     - Soil respiration-rate deviation from its baseline value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `S. D. Allison, M. D. Wallenstein and M. A. Bradford, Soil-carbon response to warming dependent on microbial physiology. <https://doi.org/10.1038/ngeo846>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.substrate_nom, par.biomass_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       s, b = chi[:2]
       uptake = _uptake(s,b,par)
       maintenance = par.mortality*max(b,0.0)
       respiration = (1.0-par.yield_coeff)*uptake + (1.0-par.recycling)*maintenance
       return {"respiration_deviation": respiration-par.respiration_nom,
               "labile_carbon": s, "microbial_biomass": b,
               "carbon_uptake": uptake, "co2_flux": respiration}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       s, b = chi[:2]
       uptake = _uptake(s,b,par)
       mortality = par.mortality*max(b,0.0)
       feed = par.feed_nom + par.feed_gain*np.tanh(float(u))
       ds = feed-uptake+par.recycling*mortality
       db = par.yield_coeff*uptake-mortality
       return np.array([ds, db, 0.0], float)
