Biomedical: nonlinear drug PK
=============================

Python model: ``plant_models.drug_infusion_pk``

Description
-----------

Two-compartment nonlinear pharmacokinetic model with saturable elimination.
state vector :math:`\mathbf{x}` = [C1,C2,R,0,0,0,0], y2=C1-C10. Educational simulation only.

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
     - :math:`\Delta C_1(t)`
     - ``y`` / ``central_concentration_deviation``
     - Central concentration deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[C_1(t),\,C_2(t),\,R(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   R_{\mathrm{cmd}}(t)&=\max\!\left(0,\,R_0+k_R\tanh(u(t))\right) \\
   v_e(C_1(t))&=\dfrac{V_{\max}C_1(t)}{K_m+C_1(t)}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{C}_1(t)&=\dfrac{R(t)-v_e(C_1(t))-Q(C_1(t)-C_2(t))}{V_1} \\
   \dot{C}_2(t)&=\dfrac{Q(C_1(t)-C_2(t))}{V_2} \\
   \dot{R}(t)&=\dfrac{R_{\mathrm{cmd}}(t)-R(t)}{\tau_p}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(infusion command)},\\
   y(t)=\Delta C_1(t)=C_1(t)-C_{1,0}.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/drug_infusion_pk.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`C_{1}(t)`
     - ``y`` / ``central_concentration_deviation``
     - Central concentration deviation
   * - :math:`C_{1}(t)`
     - ``central_concentration``
     - Central concentration
   * - :math:`C_{2}(t)`
     - ``peripheral_concentration``
     - Peripheral concentration
   * - :math:`Rin(t)`
     - ``infusion_rate``
     - Infusion rate
   * - :math:`Rel(t)`
     - ``elimination``
     - Elimination rate
   * - :math:`C_{1}(t)`
     - ``C1``
     - Central-compartment drug concentration.
   * - :math:`C_{2}(t)`
     - ``C2``
     - Peripheral-compartment drug concentration.
   * - :math:`R(t)`
     - ``R``
     - Actual infusion-rate state after pump dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`R_{\mathrm{cmd}}(t)`
     - ``R_mathrmcmd``
     - Saturated drug-infusion-rate command generated from the control input.
   * - :math:`v_e(C_1)`
     - ``v_e(C_1)``
     - Concentration-dependent elimination rate from the central compartment.
   * - :math:`y(t)`
     - ``y``
     - Central-compartment drug-concentration deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `M. Gibaldi and D. Perrier, Pharmacokinetics, 2nd ed. (compartment-model foundation). <https://www.routledge.com/Pharmacokinetics/Gibaldi-Perrier/p/book/9780824710422>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.C10,par.C20,par.R0,0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       C1,C2,R=chi[:3]; elim=par.Vmax*C1/(par.Km+C1)
       return {"central_concentration":C1,"central_concentration_deviation":C1-par.C10,"peripheral_concentration":C2,"infusion_rate":R,"elimination":elim}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       C1,C2,R=chi[:3]; Rcmd=max(0.0,par.R0+par.R_gain*np.tanh(u)); elim=par.Vmax*C1/(par.Km+C1)
       return np.array([(R-elim-par.Q*(C1-C2))/par.V1, par.Q*(C1-C2)/par.V2,
                        (Rcmd-R)/par.tau_pump,0,0,0,0],float)
