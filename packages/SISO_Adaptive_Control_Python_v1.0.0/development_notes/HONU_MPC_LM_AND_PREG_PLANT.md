# HONU MPC: LM identification and optional inner P-regulated plant

The MPC page supports two sliding-window HONU identification methods:

- Ridge regression
- Levenberg-Marquardt using the shared `lm_identification.solve_linear_lm` implementation

For LM, the GUI exposes the number of iterations and initial damping lambda. The
solver runs silently inside every window to avoid flooding the MPC log.

The selected physical ODE model can be used either directly or with continuous
inner proportional feedback:

    u_phys(t) = r_Preg * (u_new(k) - y(t))

The outer input `u_new(k)` is held over one MPC sample, while the physical input
is recomputed at every internal ODE evaluation. The HONU plant model and MPC see
only the external input `u_new` and output `y`, so the P regulator plus ODE model
forms one new black-box plant, consistently with the MRAC workflow.
