Accelerator: RF cavity amplitude
================================

Python model: ``plant_models.accelerator_rf_cavity_amplitude``

Description
-----------

Reduced RF-cavity envelope amplitude with amplifier lag and beam loading.

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
     - RF-drive command
   * - Output
     - :math:`\Delta V_c(t)`
     - ``y`` / ``field_deviation``
     - Cavity-field amplitude deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[V(t),\,a(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   a_{\mathrm{cmd}}(t)&=\max\!\left(0,\,a_0+k_a\tanh(u(t))\right)
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{V}(t)&=\dfrac{-V(t)-k_dV^3(t)+k_c a(t)-P_b(t)}{\tau_c} \\
   \dot{a}(t)&=\dfrac{a_{\mathrm{cmd}}(t)-a(t)}{\tau_a}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(RF-drive command)},\\
   y(t)=\Delta V_c(t)=V(t)-V_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/accelerator_rf_cavity_amplitude.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`amplitude_{nom}`
     - ``amplitude_nom``
     - ``1.0``
     - Initial or nominal RF-cavity field amplitude.
   * - :math:`a_0`
     - ``drive_nom``
     - ``1.12``
     - Initial or nominal RF drive state.
   * - :math:`k_a`
     - ``drive_gain``
     - ``0.75``
     - Gain from normalized input to commanded RF drive.
   * - :math:`\tau_a`
     - ``tau_amplifier``
     - ``0.0015``
     - First-order time constant of the RF amplifier.
   * - :math:`\tau_c`
     - ``tau_cavity``
     - ``0.006``
     - RF-cavity filling time constant.
   * - :math:`k_c`
     - ``cavity_gain``
     - ``1.0``
     - Static gain from RF drive to cavity field amplitude.
   * - :math:`P_b(t)`
     - ``beam_loading``
     - ``0.12``
     - Constant beam-induced loading subtracted from cavity drive.
   * - :math:`k_d`
     - ``detuning_nonlinearity``
     - ``0.1``
     - Coefficient of amplitude-dependent cavity detuning/nonlinearity.

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
     - RF-drive command
   * - :math:`\Delta V_c(t)`
     - ``y`` / ``field_deviation``
     - Cavity-field amplitude deviation
   * - :math:`V(t)`
     - ``field_amplitude``
     - Cavity-field amplitude
   * - :math:`a(t)`
     - ``rf_drive``
     - RF amplifier output
   * - :math:`P_b(t)`
     - ``beam_loading``
     - Beam-loading term
   * - :math:`k_dV^3(t)`
     - ``detuning_loss``
     - Nonlinear detuning loss
   * - :math:`V(t)`
     - ``V``
     - RF-cavity field-amplitude state governed by the nonlinear cavity balance.
   * - :math:`a(t)`
     - ``a``
     - Actual RF-amplifier drive state following the commanded drive through first-order amplifier dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`a_{\mathrm{cmd}}(t)`
     - ``a_mathrmcmd``
     - Saturated RF drive-amplitude command generated from the control input.
   * - :math:`y(t)`
     - ``y``
     - RF cavity-amplitude deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `T. Schilcher, Vector Sum Control of Pulsed Accelerating Fields in Lorentz Force Detuned Superconducting Cavities. <https://cds.cern.ch/record/581511>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.amplitude_nom, par.drive_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       V, a = chi[:2]
       return {"field_deviation": V-par.amplitude_nom, "field_amplitude": V,
               "rf_drive": a, "beam_loading": par.beam_loading,
               "detuning_loss": par.detuning_nonlinearity*V**3}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       V, a = chi[:2]
       a_cmd = max(0.0, par.drive_nom+par.drive_gain*np.tanh(float(u)))
       dV = (-V-par.detuning_nonlinearity*V**3+par.cavity_gain*a-par.beam_loading)/par.tau_cavity
       return np.array([dV, (a_cmd-a)/par.tau_amplifier, 0.0], float)
