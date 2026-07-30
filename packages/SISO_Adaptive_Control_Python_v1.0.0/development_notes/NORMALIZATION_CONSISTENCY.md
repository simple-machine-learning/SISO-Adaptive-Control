# Consistent normalization in modules 01-04

Module 01 computes one immutable z-score transform from the complete simulated training record:

u_z = (u - mean_u) / std_u
y_z = (y - mean_y) / std_y

The same statistics are saved in simulated_normalization.npz.

Every trained HONU plant receives a sidecar file named
`<plant model file>.normalization.npz`. Module 03 refuses to train a controller
when this sidecar differs from the active module-01 statistics.

The desired trajectory d has the physical dimension of y and is therefore
normalized with mean_y and std_y before entering the normalized controller
training loop. HONU plant and controller gradients remain fully in normalized
coordinates; no additional std factors are inserted into GD or NGD updates.

Every trained controller receives a sidecar file named
`<controller file>.normalization.npz`. Module 04 uses this controller sidecar as
the source of truth and refuses a test when it differs from module-01 data.
Before the physical ODE plant, u_z is converted by

u = mean_u + std_u * u_z.

The physical plant output is returned to the controller as

y_z = (y - mean_y) / std_y.

Presentation traces and plots are converted back to physical values. The
regulation deviation is scaled only by std_y; no mean is added to a difference.
