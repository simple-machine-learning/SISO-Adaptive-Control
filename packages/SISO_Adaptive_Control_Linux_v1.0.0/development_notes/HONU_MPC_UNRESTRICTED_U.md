MPC unrestricted input update
=============================

- u_min and u_max apply only to standalone physical ODE simulation.
- MPC optimization has no input bounds or clipping.
- Initial MPC identification excitation uses unbounded N(0,1) samples held for u step width.
- GUI validation of u_min < u_max is performed only for standalone simulation.
