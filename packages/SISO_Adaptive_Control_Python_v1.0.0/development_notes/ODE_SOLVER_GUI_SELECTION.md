# ODE solver selection in GUI

Added an ODE solver selector to both HONU MPC and HONU MRAC pages.

Choices: Auto (SciPy), RK45 (SciPy), DOP853 (SciPy), Radau (SciPy), BDF (SciPy), LSODA (SciPy).

MPC stores the selected value in `honu_mpc_gui_config.json` as `ode_solver` and every physical-plant simulation path in `HONU_MPC_runner.py` uses it.

MRAC stores the selected value in `project_setup.py` as `ode_solver_method`; `solver_setup.method` refers to that value, so modules 01 and 04 use the GUI selection.
