# HONU MPC tau_u / tau_d correction

- Restored `u step width [s]` and `d step width [s]` as independent signal-block durations.
- Added independent `tau_u [s]` and `tau_d [s]` widgets.
- `tau_u` is converted to `n_tau_u = round(tau_u / dt_MPC)` and the HONU plant regressor uses `u[k-n_tau_u-i]`.
- The same delayed-input structure is used during sliding-window identification and recursive MPC prediction.
- `tau_d` is converted to `n_tau_d = round(tau_d / dt_MPC)` and delays `d` before the two reference-model filters.
- Initial excitation and reference step switching still use their own step-width widgets.
