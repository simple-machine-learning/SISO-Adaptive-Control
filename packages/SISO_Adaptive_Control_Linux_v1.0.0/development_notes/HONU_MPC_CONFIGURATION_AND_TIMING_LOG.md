MPC configuration and computation-time logging
==============================================

This update adds:
- a complete effective MPC/ODE configuration dump to the MPC log before each run,
- independent wall-clock measurement in every active MPC step for:
  - sliding-window HONU identification,
  - MPC control-action optimization,
- summary statistics in milliseconds: mean, standard deviation, minimum, maximum,
- combined identification + control statistics,
- comparison with configured dt MPC, including deadline-miss count,
- per-step timing arrays saved in the NPZ result as:
  - identification_time_sec
  - control_time_sec

The first identification timing sample includes the one-off construction of the frozen PCA basis. No control or identification equations were changed.
