# HONU MPC GUI alignment with MRAC

- Added `Simulate ODE model` action to the MPC page.
- Simulation-only mode runs the selected physical ODE model without PCA, HONU identification, or MPC optimization.
- Added `Full screen` for an independent copy of the currently selected MPC graph tab.
- Corrected pyqtgraph grid rendering on every MPC axis. Upper linked axes retain the bottom axis for vertical grid lines while suppressing only tick labels.
- Applied visible black axes and stronger horizontal and vertical grids to main and fullscreen MPC plots.
- Kept simulation terminology aligned with MRAC: `dt sim [s]`, `dt MPC [s]`, `t_sim [s]`, `u_min`, `u_max`, and `u step width [s]`.
