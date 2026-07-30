# Scope of input limitation

The command input `u` is limited only in module 01 while generating ODE-plant identification data.

Modules 03 and 04 do not clip `u`, `u_z`, the physical command, or the controller output `q`. The P-regulated ODE wrapper is called with its default infinite bounds. Any nonlinear saturation intrinsic to a selected physical plant model remains part of that plant model, not a controller-side command limit.
