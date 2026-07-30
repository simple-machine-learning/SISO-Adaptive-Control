# QNU-QNU recursive-domain correction

The QNU plant is a recursive quadratic model. Local companion-matrix stability does not guarantee bounded global rollout when predicted y or commanded u leaves the module-01 identification domain.

Changes:

- corrected `plant_input` reference conversion: normalized input is denormalized with u statistics, not y statistics;
- QNU-QNU controller training clips the normalized plant regressor to the module-01 u/y domain;
- the QNU plant prediction is bounded to the identified y domain and its sensitivity is set to zero at an active bound;
- controller command u_z is bounded to the module-01 input domain in both training and physical ODE validation;
- derivatives through active command bounds are zero, consistently with saturation;
- non-finite first-epoch divergence is eliminated.

A reference outside the output range represented in module-01 data remains an extrapolation request. For accurate physical validation, module-01 excitation should cover the required controlled-output range.
