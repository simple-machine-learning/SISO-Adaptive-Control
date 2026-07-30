# MPC initial identification excitation range

The initial MPC identification phase now uses the GUI range `u_min` to `u_max`.

- Random Steps: uniform random block values in `[u_min, u_max]`.
- Alternating Steps: deterministic `u_max, u_min, ...`.
- After the initial identification phase, MPC control input `u` remains unrestricted.
