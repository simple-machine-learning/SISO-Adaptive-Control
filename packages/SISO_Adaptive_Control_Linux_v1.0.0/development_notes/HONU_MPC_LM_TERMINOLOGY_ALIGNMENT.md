# HONU MPC LM terminology alignment

The MPC GUI now uses the same plant-identification terminology as MRAC:

- `epochs` is used instead of LM iterations,
- one shared `lambda` field is used for both methods,
- for Ridge, `lambda` is the ridge regularization coefficient,
- for Levenberg-Marquardt, `lambda` is the initial LM damping coefficient.

The `epochs` field is enabled only for Levenberg-Marquardt. Configuration and logs use `lm_epochs` and `lambda`; the runner keeps backward-compatible fallbacks for older MPC configuration files.
