# ODE solver GUI labels

The MRAC and MPC solver selectors now expose the implementation path directly:

- Auto (C++/Numba/SciPy)
- Native RK4 (C++/Numba)
- Radau (SciPy)
- BDF (SciPy)
- LSODA (SciPy)
- RK45 (SciPy)
- DOP853 (SciPy)

Only the displayed labels and widget widths changed. Stored configuration values remain unchanged (`auto`, `RK4`, `Radau`, `BDF`, `LSODA`, `RK45`, `DOP853`).
