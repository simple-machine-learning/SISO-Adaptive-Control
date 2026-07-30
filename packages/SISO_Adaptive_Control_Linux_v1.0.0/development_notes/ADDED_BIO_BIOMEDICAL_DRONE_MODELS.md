# Added physical ODE plants

The simulated GUI now offers three bioprocess plants, three biomedical plants,
and two stabilized quadrotor channels. All models implement the existing
`default_params`, `initial_state`, `rhs`, and `algebraic_outputs` API. Their
controlled output is exposed as `y2`, so modules 01-04 remain unchanged.

Biomedical models are educational and research simulations only and are not
intended for clinical decision making or treatment.
