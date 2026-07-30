# HONU MPC terminology aligned with MRAC

The MPC page now uses the same labels as the MRAC page wherever the parameters have the same meaning:

- `t_sim [s]`
- `u_min`, `u_max`
- `u step width [s]`
- `d_min`, `d_max`
- `d step width [s]`
- `dt sim [s]`
- `line width [px]`

The separate `excitation duration [s]` setting was removed. The initial open-loop excitation is used only to fill the first sliding window and therefore lasts exactly

`t_exc = window_samples * dt_MPC`.

`window samples` is the number of MPC samples in the sliding identification window. `u step width [s]` has exactly the same meaning as in MRAC: the duration of one constant excitation level. After the initial window is filled, MPC control `u` is unrestricted by `u_min` and `u_max`.
