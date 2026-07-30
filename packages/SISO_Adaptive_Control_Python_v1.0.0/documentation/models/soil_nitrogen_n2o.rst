Soil ecology: nitrogen transformations and N2O
==============================================

Python model: ``plant_models.soil_nitrogen_n2o``

Description
-----------

Reduced nitrification-denitrification and N2O-emission benchmark.

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
     - Soil aeration command
   * - Output
     - :math:`\Delta F_{\mathrm{N_2O}}`
     - ``y`` / ``n2o_deviation``
     - N2O-flux deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[N_{H_4}(t),\,N_{O_3}(t),\,O_2(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   r_{nit}(t)&=k_{nit}\dfrac{N_{H_4}^+(t)}{K_{H_4}+N_{H_4}^+(t)+10^{-12}}\dfrac{O_2(t)^+}{K_{O_2}+O_2(t)^++10^{-12}} \\
   r_{den}(t)&=k_{den}\dfrac{N_{O_3}^+(t)}{K_{O_3}+N_{O_3}^+(t)+10^{-12}}\dfrac{K_i}{K_i+O_2(t)^++10^{-12}} \\
   O_{2,\mathrm{eq}}(t)&=\operatorname{clip}\!\left(O_{2,0}+k_O\tanh(u(t)),0.05,1\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{N}_{H_4}(t)&=F_N-r_{nit}(t)-k_LN_{H_4}^+(t) \\
   \dot{N}_{O_3}(t)&=r_{nit}(t)-r_{den}(t)-k_LN_{O_3}^+(t) \\
   \dot{O}_2(t)&=\dfrac{O_{2,\mathrm{eq}}(t)-O_2(t)}{\tau_O}-0.35r_{nit}(t)-0.18r_{den}(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(soil-aeration command)},\\
   y(t)=\Delta F_{\mathrm{N_2O}}(t)=F_{\mathrm{N_2O}}(t)-F_{\mathrm{N_2O},0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_nitrogen_n2o.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`ammonium_{nom}`
     - ``ammonium_nom``
     - ``0.65``
     - Initial or nominal value of ammonium used to initialize and scale this model.
   * - :math:`nitrate_{nom}`
     - ``nitrate_nom``
     - ``0.8``
     - Initial or nominal value of nitrate used to initialize and scale this model.
   * - :math:`oxygen_{nom}`
     - ``oxygen_nom``
     - ``0.62``
     - Initial or nominal value of oxygen used to initialize and scale this model.
   * - :math:`nit_{rate}`
     - ``nit_rate``
     - ``0.16``
     - Rate coefficient governing nit conversion or loss in this model.
   * - :math:`den_{rate}`
     - ``den_rate``
     - ``0.095``
     - Rate coefficient governing den conversion or loss in this model.
   * - :math:`k_{nh4}`
     - ``k_nh4``
     - ``0.35``
     - Rate, affinity, or half-saturation coefficient k_nh4 in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{no3}`
     - ``k_no3``
     - ``0.4``
     - Rate, affinity, or half-saturation coefficient k_no3 in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{oxygen}`
     - ``k_oxygen``
     - ``0.22``
     - Rate, affinity, or half-saturation coefficient k_oxygen in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`oxygen_{inhibition}`
     - ``oxygen_inhibition``
     - ``0.18``
     - Model parameter ``oxygen_inhibition``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`\tau_O`
     - ``oxygen_tau``
     - ``1.8``
     - First-order time constant associated with oxygen dynamics.
   * - :math:`k_O`
     - ``aeration_gain``
     - ``0.28``
     - Gain converting the normalized control input into the model-specific aeration actuation term.
   * - :math:`nitrogen_{input}`
     - ``nitrogen_input``
     - ``0.055``
     - Constant exogenous nitrogen input entering the corresponding material balance.
   * - :math:`nitrogen_{loss}`
     - ``nitrogen_loss``
     - ``0.025``
     - First-order loss coefficient for nitrogen.
   * - :math:`frac_{n2o,nit}`
     - ``frac_n2o_nit``
     - ``0.035``
     - Dimensionless fraction allocating the corresponding process flux to  n2o nit.
   * - :math:`frac_{n2o,den}`
     - ``frac_n2o_den``
     - ``0.22``
     - Dimensionless fraction allocating the corresponding process flux to  n2o den.
   * - :math:`n2o_{nom}`
     - ``n2o_nom``
     - ``0.02``
     - Initial or nominal value of n2o used to initialize and scale this model.

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
     - Soil aeration command
   * - :math:`\Delta F_{\mathrm{N_2O}}`
     - ``y`` / ``n2o_deviation``
     - N2O-flux deviation
   * - :math:`NH_{4}(t)`
     - ``ammonium``
     - Ammonium pool
   * - :math:`NO_{3}(t)`
     - ``nitrate``
     - Nitrate pool
   * - :math:`O_{2}(t)`
     - ``oxygen``
     - Soil oxygen availability
   * - :math:`rnit(t)`
     - ``nitrification_rate``
     - Nitrification rate
   * - :math:`rden(t)`
     - ``denitrification_rate``
     - Denitrification rate
   * - :math:`FN2O(t)`
     - ``n2o_flux``
     - N2O flux
   * - :math:`nh_{4}(t)`
     - ``nh4``
     - Ammonium concentration state.
   * - :math:`no_{3}(t)`
     - ``no3``
     - Nitrate concentration state.
   * - :math:`o_{2}(t)`
     - ``o2``
     - Dissolved oxygen concentration.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`N_{H_4}(t)`
     - ``N_H_4``
     - Ammonium-nitrogen pool.
   * - :math:`N_{O_3}(t)`
     - ``N_O_3``
     - Nitrate-nitrogen pool.
   * - :math:`r_{nit}(t)`
     - ``r_nit``
     - Nitrification rate.
   * - :math:`r_{den}(t)`
     - ``r_den``
     - Denitrification rate.
   * - :math:`O_{2,\mathrm{eq}}`
     - ``O_2,mathrmeq``
     - Aeration-dependent oxygen-equilibrium concentration.
   * - :math:`y(t)`
     - ``y``
     - Nitrous-oxide emission-rate output.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `C. Li, S. Frolking and T. A. Frolking, A model of nitrous oxide evolution from soil driven by rainfall events. <https://doi.org/10.1029/92JG01691>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.ammonium_nom, par.nitrate_nom, par.oxygen_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       nh4,no3,o2=chi[:3]
       rnit,rden=_rates(nh4,no3,o2,par)
       n2o=par.frac_n2o_nit*rnit+par.frac_n2o_den*rden
       return {"n2o_deviation": n2o-par.n2o_nom, "ammonium": nh4, "nitrate": no3,
               "oxygen": o2, "nitrification_rate": rnit,
               "denitrification_rate": rden, "n2o_flux": n2o}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       nh4,no3,o2=chi[:3]
       rnit,rden=_rates(nh4,no3,o2,par)
       oeq=np.clip(par.oxygen_nom+par.aeration_gain*np.tanh(float(u)),0.05,1.0)
       dnh4=par.nitrogen_input-rnit-par.nitrogen_loss*max(nh4,0.0)
       dno3=rnit-rden-par.nitrogen_loss*max(no3,0.0)
       do2=(oeq-o2)/par.oxygen_tau-0.35*rnit-0.18*rden
       return np.array([dnh4,dno3,do2,0.0],float)
