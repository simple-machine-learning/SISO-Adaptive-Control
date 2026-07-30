# MPC u/d excitation mode connection

The MPC selector `excitation u / reference d` now controls all step generators consistently:

- standalone ODE simulation input `u`,
- initial unrestricted MPC identification input `u`,
- MPC reference `d` after the initial identification window.

`Random Steps` uses independent random constant blocks. Simulation `u` is uniform in `[u_min,u_max]`; MPC identification `u` remains unrestricted Gaussian `N(0,1)`; reference `d` is uniform in `[d_min,d_max]`.

`Alternating Steps` alternates simulation `u_max/u_min`, unrestricted MPC identification `+1/-1`, and reference `d_max/d_min`.

The MPC optimizer still has no artificial hard bounds on `u`. `u_min` and `u_max` apply only to standalone ODE simulation.
