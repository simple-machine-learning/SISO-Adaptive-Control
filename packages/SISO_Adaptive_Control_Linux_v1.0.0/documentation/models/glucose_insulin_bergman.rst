Biomedical: glucose-insulin model
=================================

Python model: ``plant_models.glucose_insulin_bergman``

Description
-----------

Reduced Bergman glucose-insulin model with meal disturbance.
state vector :math:`\mathbf{x}` = [G,X,I,U,D,0,0], y2=G-Gb. Educational simulation only.

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
     - Insulin-infusion command
   * - Output
     - :math:`\Delta G(t)`
     - ``y`` / ``glucose_deviation``
     - Glucose deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[G(t),\,X(t),\,I(t),\,U(t),\,D(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   U_{\mathrm{cmd}}(t)&=\max\!\left(0,\,U_0+k_U\dfrac{1+\tanh(u(t))}{2}\right) \\
   D_{\mathrm{target}}(t)&=\begin{cases}0,&t<t_m,\\ A_m\exp(-(t-t_m)/\tau_m),&t\geq t_m.\end{cases}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{G}(t)&=-p_1(G(t)-G_b)-X(t)G(t)+D(t) \\
   \dot{X}(t)&=-p_2X(t)+p_3(I(t)-I_b) \\
   \dot{I}(t)&=-n(I(t)-I_b)+\dfrac{U(t)}{V_I} \\
   \dot{U}(t)&=\dfrac{U_{\mathrm{cmd}}(t)-U(t)}{\tau_p} \\
   \dot{D}(t)&=\dfrac{D_{\mathrm{target}}(t)-D(t)}{0.3}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(insulin-infusion command)},\\
   y(t)=\Delta G(t)=G(t)-G_b.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/glucose_insulin_bergman.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`G_b`
     - ``Gb``
     - ``5.5``
     - Basal blood-glucose concentration.
   * - :math:`I_b`
     - ``Ib``
     - ``10.0``
     - Basal plasma-insulin concentration.
   * - :math:`U_0`
     - ``U0``
     - ``0.0``
     - Nominal exogenous insulin-infusion state.
   * - :math:`k_U`
     - ``U_gain``
     - ``2.2``
     - Gain from normalized control input to insulin-infusion command.
   * - :math:`\tau_p`
     - ``tau_pump``
     - ``0.2``
     - First-order time constant of the infusion/pump actuator.
   * - :math:`p_{1}`
     - ``p1``
     - ``0.025``
     - Glucose effectiveness rate constant.
   * - :math:`p_{2}`
     - ``p2``
     - ``0.03``
     - Decay rate of remote insulin action.
   * - :math:`p_{3}`
     - ``p3``
     - ``0.0012``
     - Gain from plasma insulin above basal level to remote insulin action.
   * - :math:`n`
     - ``n``
     - ``0.1``
     - Plasma-insulin clearance rate.
   * - :math:`V_{I}`
     - ``V_I``
     - ``12.0``
     - Insulin distribution volume.
   * - :math:`meal_{amp}`
     - ``meal_amp``
     - ``0.12``
     - Amplitude of the modeled meal glucose-appearance disturbance.
   * - :math:`meal_{time}`
     - ``meal_time``
     - ``45.0``
     - Time at which the meal disturbance begins.
   * - :math:`meal_{tau}`
     - ``meal_tau``
     - ``14.0``
     - Decay time constant of the meal glucose-appearance disturbance.

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
     - Insulin-infusion command
   * - :math:`G(t)`
     - ``y`` / ``glucose_deviation``
     - Glucose deviation
   * - :math:`G(t)`
     - ``glucose``
     - Plasma glucose
   * - :math:`I(t)`
     - ``insulin``
     - Plasma insulin
   * - :math:`X(t)`
     - ``remote_insulin_effect``
     - Remote insulin effect
   * - :math:`Ri(t)`
     - ``infusion_rate``
     - Insulin infusion rate
   * - :math:`Dm(t)`
     - ``meal_disturbance``
     - Meal disturbance
   * - :math:`G(t)`
     - ``G``
     - Blood-glucose concentration.
   * - :math:`X(t)`
     - ``X``
     - Biomass concentration.
   * - :math:`I(t)`
     - ``I``
     - Plasma-insulin concentration.
   * - :math:`U(t)`
     - ``U``
     - Actual insulin-infusion state after pump dynamics.
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
   * - :math:`U_{\mathrm{cmd}}(t)`
     - ``U_mathrmcmd``
     - Saturated insulin-infusion command generated from the control input.
   * - :math:`D_{\mathrm{target}}(t)`
     - ``D_mathrmtarget``
     - Exogenous glucose appearance profile used as a disturbance.
   * - :math:`y(t)`
     - ``y``
     - Blood-glucose deviation from the basal value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `R. N. Bergman et al., Minimal-model approach to glucose regulation. <https://doi.org/10.2337/diab.38.12.1512>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.Gb,0,par.Ib,par.U0,0,0,0],float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi,par):
       G,X,I,U,D=chi[:5]
       return {"glucose":G,"glucose_deviation":G-par.Gb,"remote_insulin_effect":X,"insulin":I,"infusion_rate":U,"meal_disturbance":D}

ODE right-hand side:

.. code-block:: python

   def rhs(t,chi,u,par):
       G,X,I,U,D=chi[:5]; Ucmd=max(0.0,par.U0+par.U_gain*(0.5+0.5*np.tanh(u)))
       Dtarget=par.meal_amp*np.exp(-(t-par.meal_time)/par.meal_tau) if t>=par.meal_time else 0.0
       return np.array([-par.p1*(G-par.Gb)-X*G+D,-par.p2*X+par.p3*(I-par.Ib),
                        -par.n*(I-par.Ib)+U/par.V_I,(Ucmd-U)/par.tau_pump,(Dtarget-D)/0.3,0,0],float)
