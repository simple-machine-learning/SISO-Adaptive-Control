Biomedical: nonlinear drug PK-PD
================================

Python model: ``plant_models.drug_infusion_pkpd``

Description
-----------

Nonlinear PK-PD infusion model with effect compartment and Hill response.
state vector :math:`\mathbf{x}` = [C1,C2,Ce,R,E,0,0], y2=E-E0. Educational simulation only.

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
     - Infusion command
   * - Output
     - :math:`\Delta E(t)`
     - ``y`` / ``effect_deviation``
     - Pharmacodynamic effect deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[C_1(t),\,C_2(t),\,C_e(t),\,R(t),\,E(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   R_{\mathrm{cmd}}(t)&=\max\!\left(0,\,R_0+k_R\tanh(u(t))\right) \\
   v_e(C_1(t))&=\dfrac{V_{\max}C_1(t)}{K_m+C_1(t)} \\
   E_{\mathrm{ss}}(C_e(t))&=E_0+E_{\max}\dfrac{[C_e(t)]^\gamma}{EC_{50}^\gamma+[C_e(t)]^\gamma}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}_1(t)&=\dfrac{R(t)-v_e(C_1(t))-Q(C_1(t)-C_2(t))}{V_1} \\
   \dot{C}_2(t)&=\dfrac{Q(C_1(t)-C_2(t))}{V_2} \\
   \dot{C}_e(t)&=k_{e0}(C_1(t)-C_e(t)) \\
   \dot{R}(t)&=\dfrac{R_{\mathrm{cmd}}(t)-R(t)}{\tau_p} \\
   \dot{E}(t)&=\dfrac{E_{\mathrm{ss}}(C_e(t))-E(t)}{\tau_E}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(infusion command)},\\
   y(t)=\Delta E(t)=E(t)-E_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/drug_infusion_pkpd.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`C_{1,0}`
     - ``C10``
     - ``1.0``
     - Initial concentration in the central compartment.
   * - :math:`C_{20}`
     - ``C20``
     - ``0.65``
     - Initial concentration in the peripheral compartment.
   * - :math:`Ce_{0}`
     - ``Ce0``
     - ``0.85``
     - Initial effect-site concentration.
   * - :math:`R_0`
     - ``R0``
     - ``0.55``
     - Nominal infusion-rate state.
   * - :math:`k_R`
     - ``R_gain``
     - ``0.45``
     - Gain from normalized control input to infusion-rate command.
   * - :math:`\tau_p`
     - ``tau_pump``
     - ``0.18``
     - First-order time constant of the infusion/pump actuator.
   * - :math:`V_1`
     - ``V1``
     - ``4.0``
     - Volume of the central pharmacokinetic compartment.
   * - :math:`V_2`
     - ``V2``
     - ``8.0``
     - Volume of the peripheral pharmacokinetic compartment.
   * - :math:`Q`
     - ``Q``
     - ``0.55``
     - Inter-compartmental clearance between central and peripheral compartments.
   * - :math:`V_{\max}`
     - ``Vmax``
     - ``0.65``
     - Maximum nonlinear elimination rate.
   * - :math:`K_m`
     - ``Km``
     - ``0.75``
     - Concentration at which nonlinear elimination reaches half of Vmax.
   * - :math:`k_{e0}`
     - ``ke0``
     - ``0.3``
     - Effect-site equilibration rate constant.
   * - :math:`E_0`
     - ``E0``
     - ``0.0``
     - Baseline pharmacodynamic effect.
   * - :math:`E_{\max}`
     - ``Emax``
     - ``1.0``
     - Maximum effect increment above baseline.
   * - :math:`EC_{50}`
     - ``EC50``
     - ``0.9``
     - Effect-site concentration producing half of Emax.
   * - :math:`\gamma`
     - ``gamma``
     - ``2.2``
     - Hill exponent controlling steepness of the concentration-effect curve.
   * - :math:`\tau_E`
     - ``tau_E``
     - ``0.12``
     - First-order time constant of the filtered pharmacodynamic effect.

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
     - Infusion command
   * - :math:`E(t)`
     - ``y`` / ``effect_deviation``
     - Pharmacodynamic effect deviation
   * - :math:`C_{1}(t)`
     - ``central_concentration``
     - Central concentration
   * - :math:`C_{2}(t)`
     - ``peripheral_concentration``
     - Peripheral concentration
   * - :math:`Ce(t)`
     - ``effect_concentration``
     - Effect-site concentration
   * - :math:`Rin(t)`
     - ``infusion_rate``
     - Infusion rate
   * - :math:`E(t)`
     - ``effect``
     - Pharmacodynamic effect
   * - :math:`C_{1}(t)`
     - ``C1``
     - Central-compartment drug concentration.
   * - :math:`C_{2}(t)`
     - ``C2``
     - Peripheral-compartment drug concentration.
   * - :math:`Ce(t)`
     - ``Ce``
     - Effect-site drug concentration.
   * - :math:`R(t)`
     - ``R``
     - Actual infusion-rate state after pump dynamics.
   * - :math:`E(t)`
     - ``E``
     - Filtered pharmacodynamic effect returned as the controlled output.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`C_e(t)`
     - ``C_e``
     - Effect-site drug concentration.
   * - :math:`R_{\mathrm{cmd}}(t)`
     - ``R_mathrmcmd``
     - Saturated drug-infusion-rate command generated from the control input.
   * - :math:`v_e(C_1)`
     - ``v_e(C_1)``
     - Concentration-dependent elimination rate from the central compartment.
   * - :math:`E_{\mathrm{ss}}(C_e(t))`
     - ``E_mathrmss(C_e)``
     - Steady-state pharmacodynamic effect associated with the effect-site concentration.
   * - :math:`y(t)`
     - ``y``
     - Pharmacodynamic-effect deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `L. B. Sheiner et al., Simultaneous modeling of pharmacokinetics and pharmacodynamics. <https://doi.org/10.1002/cpt1979253358>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par):
       E=hill(par.Ce0,par); return np.array([par.C10,par.C20,par.Ce0,par.R0,E,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       C1,C2,Ce,R,E=chi[:5]; Ebase=hill(par.Ce0,par)
       return {"central_concentration":C1,"peripheral_concentration":C2,"effect_concentration":Ce,"infusion_rate":R,"effect":E,"effect_deviation":E-Ebase}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       C1,C2,Ce,R,E=chi[:5]; Rcmd=max(0.0,par.R0+par.R_gain*np.tanh(u)); elim=par.Vmax*C1/(par.Km+C1); Ess=hill(Ce,par)
       return np.array([(R-elim-par.Q*(C1-C2))/par.V1,par.Q*(C1-C2)/par.V2,
                        par.ke0*(C1-Ce),(Rcmd-R)/par.tau_pump,(Ess-E)/par.tau_E,0,0],float)
