# HONU MPC terminology aligned with MRAC

The MPC GUI now reuses the MRAC labels wherever the parameter has the same meaning:

- `t_sim [s]`: total simulation duration.
- `dt_sim [s]`: ODE integration sampling period.
- `u_min`, `u_max`: range used to generate the initial plant-input excitation only.
- `u step width [s]`: duration of one constant excitation level, identical in meaning to module 01.
- `d step width [s]`: duration of one constant reference level, identical in meaning to modules 03/04.
- `tau_1 [s]`, `tau_2 [s]`: reference-model time constants.
- `line width [px]`: graph line width.

`u excitation duration [s]` has no direct MRAC GUI counterpart because MPC combines an initial excitation interval and the subsequent closed-loop simulation in one run. It is not called pre-training: the interval generates plant data, while the first sliding-window HONU fit is evaluated when MPC starts.
