# Unified local rho(A_y(k)) labels

MRAC and MPC now use the common visible label `local rho(A_y(k))` for the exact step-dependent output-dynamics spectral radius.

- LNU frozen/batch: the trajectory can be constant.
- LNU sliding/online: it changes with the identified weights.
- QNU frozen: it changes with the current regressor even for fixed weights.
- QNU sliding/online: it changes with both the regressor and the weights.
