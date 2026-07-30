# Verified P-regulated black-box settings

For the selected problematic models, module 01 identifies the composite plant

    u_new -> [u_phys = r_preg (u_new - y) -> physical ODE plant] -> y.

The saved common identification channels remain `t, u, y`, where `u` is
`u_new`.  The internal physical command is not used as the HONU input.
Module 03 therefore remains unchanged and trains the MRAC law
`u_new = r_0 (d - q)` on the identified composite plant.  Module 04 applies the
same internal P feedback to the physical ODE model.

Verified with batch Ridge plant identification and NGD MRAC for five epochs:

| Model | r_preg | dt_sim [s] | dt_MRAC [s] | t_sim [s] | step u/d [s] | tau_u [s] | Tau_1 [s] | Tau_2 [s] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| chemostat_monod_biomass | -0.25 | 0.2 | 2.0 | 600 | 20 | 10 | 5 | 10 |
| drug_infusion_pk | 0.50 | 0.05 | 0.5 | 300 | 10 | 2.5 | 2 | 3 |
| drug_infusion_pkpd | 0.50 | 0.1 | 1.0 | 500 | 20 | 5 | 5 | 8 |
| glucose_insulin_bergman | -0.05 | 0.2 | 2.0 | 800 | 20 | 10 | 10 | 20 |

The negative gains for chemostat and glucose-insulin reflect their negative
steady-state input-output direction.
