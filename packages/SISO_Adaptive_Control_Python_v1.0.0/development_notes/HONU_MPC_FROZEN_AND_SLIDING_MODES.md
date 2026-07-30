# HONU MPC frozen and sliding modes

The MPC workflow now provides two separate control actions:

- **MPC - Frozen HONU**: simulates a complete identification record over `t_sim`, trains the Plant HONU once by the selected Ridge or L-M batch method, then performs MPC with fixed HONU and PCA parameters.
- **MPC - Sliding Retraining**: retains the existing repeated HONU fitting on the current sliding window.

Both modes use the same explicit HONU bias `x_0 = 1`, PCA configuration, delays `tau_u` and `tau_d`, plant/P-regulator selection, excitation settings, and MPC objective. Their result files and GUI result buttons are separate.
