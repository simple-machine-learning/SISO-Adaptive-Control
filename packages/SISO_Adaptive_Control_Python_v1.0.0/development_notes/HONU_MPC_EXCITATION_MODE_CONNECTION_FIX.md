# HONU MPC excitation-mode connection fix

- The MPC excitation selector now controls both standalone ODE simulation and the initial HONU-MPC identification interval.
- Random Steps: one random constant level per hold block. Standalone simulation uses U(u_min,u_max); unrestricted MPC excitation uses N(0,1).
- Alternating Steps: standalone simulation alternates u_max,u_min; unrestricted MPC excitation alternates +1,-1.
- The selected mode is logged and saved in the NPZ output.
