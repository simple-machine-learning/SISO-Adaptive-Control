Wireless: transmit-power / SNR control
======================================

Python model: ``plant_models.wireless_power_snr``

Description
-----------

Envelope model of wireless transmit-power control and effective SNR.

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
     - Transmit-power command
   * - Output
     - :math:`\Delta \gamma`
     - ``y`` / ``snr_deviation``
     - SNR deviation


Model equations
---------------

State variables
~~~~~~~~~~~~~~~

The physical state vector used by the model is

.. math::

   \mathbf{x}(t)=[p(t),\,\gamma(t)]^\mathsf{T}.

Static and auxiliary relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The auxiliary quantities are

.. math::

   \begin{aligned}
   p_{\mathrm{cmd}}(t)&=\max\!\left(0,\,p_0+k_p\tanh(u(t))\right) \\
   \gamma_{\mathrm{eq}}(t)&=\dfrac{k_hp^+(t)}{N_I}
   \end{aligned}

State equations
~~~~~~~~~~~~~~~

The implemented continuous-time dynamics are

.. math::

   \begin{aligned}
   \dot{p}(t)&=\dfrac{p_{\mathrm{cmd}}(t)-p(t)}{\tau_p} \\
   \dot{\gamma}(t)&=\dfrac{\gamma_{\mathrm{eq}}(t)-\gamma(t)}{\tau_\gamma}
   \end{aligned}

Output equation
~~~~~~~~~~~~~~~

The reported link quantities and controlled output are

.. math::

   \begin{aligned}
   R(t)&=B_w\log_2\!\left(1+\max(\gamma(t),0)\right),\\
   I(t)&=N_I,\\
   y(t)&=\Delta\gamma(t)=\gamma(t)-\gamma_0.
   \end{aligned}

The controlled input and output used by the identification and control algorithms are defined explicitly as

.. math::

   \begin{aligned}
   u(t)\in\mathbb{R}\quad\text{(transmit-power command)},\\
   y(t)=\Delta\gamma(t)=\gamma(t)-\gamma_0.
   \end{aligned}

Parameter implementation
------------------------

The editable default parameters are defined in ``apps/simulated/plant_models/wireless_power_snr.py``. They are fields of ``PlantParams`` near the beginning of that file. The function ``default_params()`` returns the default parameter object used by the GUI and simulation. The parameter table below maps the Python field names to the mathematical symbols used in the equations.

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
   * - :math:`power_{nom}`
     - ``power_nom``
     - ``1.0``
     - Initial or nominal transmitted power state.
   * - :math:`k_p`
     - ``power_gain``
     - ``0.8``
     - Gain from normalized control input to transmitter power command.
   * - :math:`\tau_p`
     - ``tau_power``
     - ``0.12``
     - Transmitter-power actuator time constant.
   * - :math:`k_h`
     - ``channel_gain``
     - ``1.0``
     - Channel gain converting transmitted power into received signal power.
   * - :math:`noise_{interference}`
     - ``noise_interference``
     - ``0.25``
     - Additive noise-plus-interference power in the SNR denominator.
   * - :math:`\tau_\gamma`
     - ``tau_snr``
     - ``0.45``
     - First-order time constant of the filtered SNR output.
   * - :math:`snr_{nom}`
     - ``snr_nom``
     - ``4.0``
     - Initial or nominal SNR state.
   * - :math:`bandwidth`
     - ``bandwidth``
     - ``1.0``
     - Bandwidth scaling used in the reported link-capacity output.

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
     - Transmit-power command
   * - :math:`\Delta \gamma`
     - ``y`` / ``snr_deviation``
     - SNR deviation
   * - :math:`p(t)`
     - ``transmit_power``
     - Transmit power
   * - :math:`\gamma(t)`
     - ``snr``
     - Effective SNR
   * - :math:`R(t)`
     - ``throughput``
     - Shannon-rate proxy
   * - :math:`I(t)`
     - ``interference``
     - Noise and interference
   * - :math:`p(t)`
     - ``p``
     - Actual power or actuator state after first-order dynamics.

Additional symbols
------------------

Symbols used by the model equations that are not already listed in the state or parameter tables.

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - Mathematical notation
     - Python/interface name
     - Meaning
   * - :math:`p_{\mathrm{cmd}}`
     - ``p_mathrmcmd``
     - Saturated transmit-power command generated from the control input.
   * - :math:`\gamma_{\mathrm{eq}}`
     - ``gamma_mathrmeq``
     - Equilibrium signal-to-noise ratio corresponding to the current transmit power and interference.
   * - :math:`y(t)`
     - ``y``
     - Signal-to-noise-ratio deviation from its operating-point value.

Model provenance and references
-------------------------------

This is a reduced-order educational benchmark assembled from standard physical or domain-modeling relations. It is not a parameter-identical reproduction of the cited source. The reference below documents the principal model structure or constitutive relations used.

* `C. E. Shannon, A Mathematical Theory of Communication. <https://doi.org/10.1002/j.1538-7305.1948.tb01338.x>`_

Implementation reference
------------------------

Initial state:

.. code-block:: python

   def initial_state(par): return np.array([par.power_nom, par.snr_nom, 0.0], float)

Algebraic outputs:

.. code-block:: python

   def algebraic_outputs(chi, par):
       p, snr = chi[:2]
       return {"snr_deviation": snr-par.snr_nom, "transmit_power": p,
               "snr": snr, "throughput": par.bandwidth*np.log2(1.0+max(snr,0.0)),
               "interference": par.noise_interference}

ODE right-hand side:

.. code-block:: python

   def rhs(t, chi, u, par):
       p, snr = chi[:2]
       p_cmd = max(0.0, par.power_nom+par.power_gain*np.tanh(float(u)))
       snr_eq = par.channel_gain*max(p,0.0)/par.noise_interference
       return np.array([(p_cmd-p)/par.tau_power, (snr_eq-snr)/par.tau_snr, 0.0], float)
