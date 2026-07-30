# Model-specific recommended presets

Selecting a physical model in the GUI automatically loads its verified preset. The **Load recommended preset** button restores it after manual edits.

Each preset includes `dt_sim`, `dt` (`dt_MRAC`), `t_end`, `step_hold_sec`, `tau_u`, `n_y`, `n_u`, batch-Ridge regularization, NGD controller parameters, reference-model time constants, and optional P-regulated black-box settings.

The optional black box is

```text
u_new -> [u_phys = r_preg * (u_new - y) -> physical ODE plant] -> y
```

The plant HONU is identified from `u_new` to `y`. The P-feedback is enabled in the verified presets for chemostat, drug PK, drug PK-PD, and glucose-insulin models. All GUI values remain editable and are written to `project_setup.py`.
