# Unrestricted controller input u

- `u_min` and `u_max` configure only the excitation signal generated in module 01.
- Module 03 computes controller output `u` without clipping or saturation.
- Module 04 passes the denormalized controller output directly to the physical ODE plant.
- The QNU surrogate Jacobian in module 04 is no longer projected in its input-history coordinates.
- The optional inner P-regulated black-box path also applies no clipping to its controller-generated input.
