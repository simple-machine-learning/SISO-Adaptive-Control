# HONU MPC input-range scope

`u_min` and `u_max` are used only for:

1. the standalone `Simulate ODE model` excitation, and
2. the initial MPC excitation used to fill the first sliding window.

After the first window is filled, HONU MPC computes an unrestricted control action. The optimizer receives no bounds and the selected action is not clipped or saturated by `u_min` or `u_max`.
