MPC sliding-window duration in seconds
======================================

- GUI parameter renamed to `window length [s]`.
- Configuration now stores `window_length_sec`.
- Runner converts duration automatically to MPC samples as
  `ceil(window_length_sec / dt_MPC)`.
- A minimum sample count `max(n_y, n_u) + 3` is enforced.
- Initial excitation and every sliding identification window use the resulting effective sample count.
- Result NPZ stores requested duration, effective duration, and effective sample count.
