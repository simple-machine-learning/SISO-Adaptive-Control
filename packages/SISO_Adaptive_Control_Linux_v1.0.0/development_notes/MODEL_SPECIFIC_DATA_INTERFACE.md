# Model-specific simulated-plant data interface

The fixed two-mass columns `F1`, `F2`, `y1`, `y2`, `z_f`, and `F_f` are no longer used as a universal interface.

Every physical model exports its own named physical quantities and units. The first three columns are invariant:

`t, u, y`

Here `u` is the physical plant input and `y` is the model-defined controlled output. Modules 02-04 and the fixed 3-sigma normalization use only these common columns. All following columns are model-specific diagnostics.

Module 01 and module 04 plots are generated dynamically from the selected model metadata.
