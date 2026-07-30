Software overview
=================

Main launcher
-------------

``launcher.py`` is the common entry point. It presents the two software modes,
explains their purpose, and starts the selected GUI in its own process. On
Windows, use ``RUN_SOFTWARE.bat``.

Simulated systems
-----------------

The simulated mode is a controlled learning and experimentation environment.
It generates input-output data from nonlinear physical ODE models and supports:

* selection of the plant and its physical parameters,
* generation of excitation, disturbance and reference signals,
* LNU or QNU plant identification using batch, GD, NGD or LM learning,
* MRAC controller training and closed-loop tests on the ODE plant,
* HONU-based MPC experiments and diagnostic plots.

The simulated workflow should use bounded identification trajectories. An ODE
plant that is open-loop unstable must first be placed under an independent
stabilizing feedback law before its data are treated as admissible HONU
training data. MRAC or MPC can then be studied as a performance-improvement
layer within that stabilized operating regime.

Measured systems
----------------

The measured mode replaces ODE data generation by an import and preprocessing
stage. It supports:

* import of supported tabular measurement files,
* selection of time, input and output channels,
* definition of the working sampling period and optional downsampling,
* LNU or QNU identification from the resulting sampled record,
* MRAC and MPC workflows using the same HONU concepts as simulated mode.

Imported records must come from a naturally stable or independently
pre-stabilized experiment. The measured-data mode is not intended to identify
an uncontrolled unstable plant from divergent trajectories.

Shared and mode-specific implementation
---------------------------------------

The shared ``common`` directory contains numerical modules that were identical
in both original packages: HONU basis construction, LM identification support,
reference-signal generation and general signal generation. Data acquisition,
configuration and GUI execution remain mode-specific because they differ
materially and are part of the validated behaviour of each application.
