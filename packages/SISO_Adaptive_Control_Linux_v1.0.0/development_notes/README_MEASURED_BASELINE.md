# SISO Measured — Simulated-derived baseline

This package is derived directly from `SISO simulated(9)`.

Differences from Simulated are intentionally restricted to the measurement boundary:

1. Step 1 opens a measured-data file instead of generating an ODE trajectory. Accepted canonical input is `t, u, y` in TXT/CSV/NPY/NPZ form. The selected data are converted to the same `data_uy.txt`, `data_uy_normalized.txt`, and normalization artifact interface used by Simulated.
2. The selected measured dataset is shared by MRAC and MPC; switching tabs does not require loading it again.
3. Step 4 does not call a physical ODE. Validation is the closed-loop test on the trained HONU plant produced by controller training.
4. The Simulated GUI structure, top longitudinal panels, parameter widgets, plotting workspace, and workflow order are retained.

The physical-model selector remains present only to preserve exact Simulated panel geometry and backward-compatible setup fields; it is not used to generate measured data.
