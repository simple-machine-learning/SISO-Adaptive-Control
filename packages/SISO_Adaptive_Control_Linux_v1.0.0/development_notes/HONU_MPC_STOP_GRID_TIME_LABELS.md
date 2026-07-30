# HONU MPC stop, grids, and time-parameter labels

The HONU MPC GUI now includes a Stop button next to Run HONU MPC. Stop first requests process termination and force-kills the runner after 1.5 s if required.

All MPC plot axes explicitly enable both horizontal and vertical grids, including after plot clearing and result reload.

Ambiguous hold labels were removed from the left panel. The time parameters in the top panel are now:

- total duration [s]: full closed-loop simulation duration;
- excitation duration [s]: initial open-loop identification interval;
- exc. step width [s]: duration of each constant random excitation value within the excitation interval;
- d step width [s]: duration of each constant reference level before switching between d min and d max.

The left panel now contains only reference-model dynamics, sliding-window HONU parameters, the MPC objective, and the status log.
