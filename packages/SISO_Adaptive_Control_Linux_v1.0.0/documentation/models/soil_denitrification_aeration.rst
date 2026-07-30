Soil ecology: denitrification controlled by aeration
====================================================

Python model: ``plant_models.soil_denitrification_aeration``

Description
-----------

Aeration-controlled soil denitrification and N2O flux benchmark.

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
     - Aeration command
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

   \mathbf{x}(t)=[N(t),\,C(t),\,O(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   r_d(t)&=k_d\dfrac{N^+(t)}{K_N+N^+(t)+10^{-12}}\dfrac{C(t)^+}{K_C+C(t)^++10^{-12}}\dfrac{K_O}{K_O+O^+(t)+10^{-12}} \\
   O_{\mathrm{eq}}(t)&=\operatorname{clip}\!\left(O_0+k_O\tanh(u(t)),0.02,1\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{N}(t)&=F_N-r_d(t) \\
   \dot{C}(t)&=F_C-r_d(t)-k_C C(t)^+ \\
   \dot{O}(t)&=\dfrac{O_{\mathrm{eq}}(t)-O(t)}{\tau_O}-0.12r_d(t)
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(aeration command)},\\
   y(t)=\Delta F_{\mathrm{N_2O}}(t)=F_{\mathrm{N_2O}}(t)-F_{\mathrm{N_2O},0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/soil_denitrification_aeration.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`nitrate_{nom}`
     - ``nitrate_nom``
     - ``0.9``
     - Initial or nominal value of nitrate used to initialize and scale this model.
   * - :math:`carbon_{nom}`
     - ``carbon_nom``
     - ``0.75``
     - Initial or nominal value of carbon used to initialize and scale this model.
   * - :math:`oxygen_{nom}`
     - ``oxygen_nom``
     - ``0.35``
     - Initial or nominal value of oxygen used to initialize and scale this model.
   * - :math:`den_{rate}`
     - ``den_rate``
     - ``0.14``
     - Rate coefficient governing den conversion or loss in this model.
   * - :math:`k_{nitrate}`
     - ``k_nitrate``
     - ``0.35``
     - Rate, affinity, or half-saturation coefficient k_nitrate in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`k_{carbon}`
     - ``k_carbon``
     - ``0.3``
     - Rate, affinity, or half-saturation coefficient k_carbon in the model constitutive law; its exact placement is shown in the state equations.
   * - :math:`oxygen_{inhibition}`
     - ``oxygen_inhibition``
     - ``0.16``
     - Model parameter ``oxygen_inhibition``; its quantitative role is defined explicitly by the state equation in which it appears.
   * - :math:`nitrate_{input}`
     - ``nitrate_input``
     - ``0.045``
     - Rate coefficient governing nitrate input conversion or loss in this model.
   * - :math:`carbon_{input}`
     - ``carbon_input``
     - ``0.035``
     - Constant exogenous carbon input entering the corresponding material balance.
   * - :math:`carbon_{decay}`
     - ``carbon_decay``
     - ``0.02``
     - First-order loss coefficient for carbon.
   * - :math:`\tau_O`
     - ``oxygen_tau``
     - ``1.2``
     - First-order time constant associated with oxygen dynamics.
   * - :math:`k_O`
     - ``aeration_gain``
     - ``0.38``
     - Gain converting the normalized control input into the model-specific aeration actuation term.
   * - :math:`n2o_{fraction}`
     - ``n2o_fraction``
     - ``0.3``
     - Dimensionless fraction allocating the corresponding process flux to n2o .
   * - :math:`n2o_{nom}`
     - ``n2o_nom``
     - ``0.018``
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
     - Aeration command
   * - :math:`\Delta F_{\mathrm{N_2O}}`
     - ``y`` / ``n2o_deviation``
     - N2O-flux deviation
   * - :math:`NO_{3}(t)`
     - ``nitrate``
     - Nitrate pool
   * - :math:`C(t)`
     - ``available_carbon``
     - Available carbon
   * - :math:`O_{2}(t)`
     - ``oxygen``
     - Soil oxygen availability
   * - :math:`rden(t)`
     - ``denitrification_rate``
     - Denitrification rate
   * - :math:`FN2O(t)`
     - ``n2o_flux``
     - N2O flux
   * - :math:`n(t)`
     - ``n``
     - Nitrogen pool state.
   * - :math:`c(t)`
     - ``c``
     - Available-carbon concentration state.
   * - :math:`o(t)`
     - ``o``
     - Oxygen availability/concentration state.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`N(t)`
     - ``N``
     - Available nitrate or nitrogen state used by the denitrification rate.
   * - :math:`O(t)`
     - ``O``
     - Dissolved oxygen state.
   * - :math:`r_d(t)`
     - ``r_d``
     - Denitrification rate.
   * - :math:`O_{\mathrm{eq}}`
     - ``O_mathrmeq``
     - Aeration-dependent oxygen-equilibrium concentration.
   * - :math:`y(t)`
     - ``y``
     - Denitrification-related output defined by the model output equation.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `C. Li, S. Frolking and T. A. Frolking, A model of nitrous oxide evolution from soil driven by rainfall events. <https://doi.org/10.1029/92JG01691>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.nitrate_nom,par.carbon_nom,par.oxygen_nom,0.0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       n,c,o=chi[:3]; r=_rate(n,c,o,par); flux=par.n2o_fraction*r
       return {"n2o_deviation":flux-par.n2o_nom,"nitrate":n,"available_carbon":c,
               "oxygen":o,"denitrification_rate":r,"n2o_flux":flux}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       n,c,o=chi[:3]; r=_rate(n,c,o,par)
       oeq=np.clip(par.oxygen_nom+par.aeration_gain*np.tanh(float(u)),0.02,1.0)
       return np.array([par.nitrate_input-r,par.carbon_input-r-par.carbon_decay*max(c,0.0),
                        (oeq-o)/par.oxygen_tau-0.12*r,0.0],float)
