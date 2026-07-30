Soil ecology: microbial C-N stoichiometry
=========================================

Python model: ``plant_models.soil_microbe_cn_stoichiometry``

Description
-----------

Carbon-nitrogen co-limitation with smooth stoichiometric limitation.

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
     - Carbon-addition command
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

   \mathbf{x}(t)=[C(t),\,N(t),\,B(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   r_C(t)&=k_CB^+(t)\dfrac{C(t)^+}{K_C+C(t)^++10^{-12}} \\
   r_N(t)&=k_NB^+(t)\dfrac{N(t)^+}{K_N+N(t)^++10^{-12}} \\
   g(t)&=\max\!\left(\operatorname{smin}(0.48r_C(t),\,\rho_{CN}r_N(t);\beta),0\right) \\
   \operatorname{smin}(a,b(t);\beta)&=m-\dfrac{\ln(e^{-\beta(a-m)}+e^{-\beta(b-m)})}{\beta},\quad m=\min(a,b(t)) \\
   m_B(t)&=k_mB^+(t) \\
   F_C(t)&=F_{C,0}+k_F\tanh(u(t))
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}(t)&=F_C(t)-r_C(t)+0.25m_B(t) \\
   \dot{N}(t)&=F_N-r_N(t)+\dfrac{0.15m_B(t)}{\rho_{CN}} \\
   \dot{B}(t)&=g(t)-m_B(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(carbon-addition command)},\\
   y(t)=\Delta R_{\mathrm{CO_2}}(t)=R_{\mathrm{CO_2}}(t)-R_{\mathrm{CO_2},0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_microbe_cn_stoichiometry.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`carbon_{nom}`
     - ``carbon_nom``
     - ``1.0``
     - Initial or nominal value of carbon used to initialize and scale this model.
   * - :math:`nitrogen_{nom}`
     - ``nitrogen_nom``
     - ``0.45``
     - Initial or nominal value of nitrogen used to initialize and scale this model.
   * - :math:`biomass_{nom}`
     - ``biomass_nom``
     - ``0.25``
     - Initial or nominal value of biomass used to initialize and scale this model.
   * - :math:`carbon_{rate}`
     - ``carbon_rate``
     - ``0.16``
     - Rate coefficient governing carbon conversion or loss in this model.
   * - :math:`nitrogen_{rate}`
     - ``nitrogen_rate``
     - ``0.1``
     - Rate coefficient governing nitrogen conversion or loss in this model.
   * - :math:`k_{carbon}`
     - ``k_carbon``
     - ``0.35``
     - Rate, affinity, or half-saturation coefficient k_carbon in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{nitrogen}`
     - ``k_nitrogen``
     - ``0.2``
     - Rate, affinity, or half-saturation coefficient k_nitrogen in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`biomass_{cn}`
     - ``biomass_cn``
     - ``6.0``
     - Model parameter ``biomass_cn``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`mortality`
     - ``mortality``
     - ``0.04``
     - First-order loss coefficient for mortality.
   * - :math:`carbon_{input,nom}`
     - ``carbon_input_nom``
     - ``0.042``
     - Initial or nominal value of carbon input used to initialize and scale this model.
   * - :math:`carbon_{input,gain}`
     - ``carbon_input_gain``
     - ``0.03``
     - Gain converting the normalized control input into the model-specific carbon input actuation term.
   * - :math:`nitrogen_{input}`
     - ``nitrogen_input``
     - ``0.013``
     - Constant exogenous nitrogen input entering the corresponding material balance.
   * - :math:`smooth_{beta}`
     - ``smooth_beta``
     - ``18.0``
     - Model parameter ``smooth_beta``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`respiration_{nom}`
     - ``respiration_nom``
     - ``0.03``
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
     - Carbon-addition command
   * - :math:`\Delta R_{\mathrm{CO_2}}`
     - ``y`` / ``respiration_deviation``
     - CO2-flux deviation
   * - :math:`C(t)`
     - ``available_carbon``
     - Available carbon
   * - :math:`N(t)`
     - ``available_nitrogen``
     - Available nitrogen
   * - :math:`B(t)`
     - ``microbial_biomass``
     - Microbial biomass
   * - :math:`\rho_{CN}`
     - ``limitation_ratio``
     - C-to-N limitation ratio
   * - :math:`Rco_{2}(t)`
     - ``co2_flux``
     - Soil CO2 flux
   * - :math:`c(t)`
     - ``c``
     - Soil-carbon pool state.
   * - :math:`n(t)`
     - ``n``
     - Nitrogen pool state.
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
   * - :math:`r_C(t)`
     - ``r_C``
     - Potential carbon-limited microbial growth rate.
   * - :math:`r_N(t)`
     - ``r_N``
     - Potential nitrogen-limited microbial growth rate.
   * - :math:`g(t)`
     - ``g``
     - Realized microbial growth rate after carbon/nitrogen co-limitation.
   * - :math:`\operatorname{smin}(a,b;\beta)`
     - ``operatornamesmin(a,b;beta)``
     - Smooth minimum used to combine carbon- and nitrogen-limited growth rates.
   * - :math:`m_B(t)`
     - ``m_B``
     - Microbial maintenance or decay flux.
   * - :math:`F_C(t)`
     - ``F_C``
     - External carbon-input flux generated from the control input.
   * - :math:`y(t)`
     - ``y``
     - Microbial-growth or respiration output defined by the model output equation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `R. L. Sinsabaugh et al., Ecoenzymatic stoichiometry of microbial organic nutrient acquisition. <https://doi.org/10.1038/nature08632>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.carbon_nom,par.nitrogen_nom,par.biomass_nom,0.0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       c,n,b=chi[:3]; uc,un,g=_rates(c,n,b,par)
       respiration=max(uc-g,0.0)+0.35*par.mortality*max(b,0.0)
       ratio=(0.48*uc)/(par.biomass_cn*un+1e-12)
       return {"respiration_deviation":respiration-par.respiration_nom,"available_carbon":c,
               "available_nitrogen":n,"microbial_biomass":b,"limitation_ratio":ratio,
               "co2_flux":respiration}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       c,n,b=chi[:3]; uc,un,g=_rates(c,n,b,par); mort=par.mortality*max(b,0.0)
       cin=par.carbon_input_nom+par.carbon_input_gain*np.tanh(float(u))
       return np.array([cin-uc+0.25*mort,par.nitrogen_input-un+0.15*mort/par.biomass_cn,g-mort,0.0],float)
