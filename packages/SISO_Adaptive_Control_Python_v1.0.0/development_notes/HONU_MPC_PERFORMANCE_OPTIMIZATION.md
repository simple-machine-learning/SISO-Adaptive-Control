# HONU MPC performance optimization

Version 8.80 removes avoidable numerical work without changing the MPC cost function or HONU model structure.

- BFGS now receives the exact gradient of the existing MPC objective.
- HONU prediction sensitivities are propagated recursively through the prediction horizon.
- Sliding and batch identification construct the PCA/HONU design matrix vectorially.
- Prediction retains only the history tail required by n_y, n_u and tau_u.
- The physical ODE solver, tolerances, dt_sim semantics, PCA, learning methods and objective weights are unchanged.
