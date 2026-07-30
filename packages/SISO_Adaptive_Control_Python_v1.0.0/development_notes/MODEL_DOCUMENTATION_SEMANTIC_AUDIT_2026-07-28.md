# Model documentation semantic audit — 2026-07-28

The notation and signal tables of all simulated ODE models were checked against both the displayed model equations and the corresponding `plant_models/*.py` implementation.

A table entry is now treated as valid only if it is one of the following:

- a state or input appearing in the ODE;
- a parameter or auxiliary quantity explicitly defined before the ODE;
- an algebraic signal returned by `algebraic_outputs()`, with its relation to the states documented or visible in the implementation reference.

Important corrections include:

- router queue: `q` is the physical state in `dq/dt = r - s(q) - k_l q`; the controlled output is `Delta q = q - q0`; admitted rate, service rate, and queue-delay proxy are now explicitly defined algebraically;
- accelerator beam model: removed incorrect microbial-biomass wording from the magnet-field state;
- cloud workload model: removed mechanical/carbon template descriptions;
- overhead crane: removed soil-moisture wording from the sway angle and aligned payload/trolley symbols with the equations;
- photobioreactor: removed an incorrect plasma-insulin description from the light state;
- quadrotor altitude: removed temperature and microbial-mass template descriptions;
- several compact symbols such as `vx`, `Bm`, `Vc`, `qp`, `xT`, `Fd`, and `QJ` were replaced by the notation actually used in the equations.

The notation-table introduction now explicitly distinguishes ODE states from reported algebraic signals. No plant dynamics or numerical parameters were changed.
