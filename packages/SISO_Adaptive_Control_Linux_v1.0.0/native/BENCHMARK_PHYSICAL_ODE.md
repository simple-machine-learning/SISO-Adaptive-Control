# Physical ODE benchmark

Configuration: nonlinear microgrid BESS model, sample period 0.02 s, internal RK4 step 0.002 s, 500 sample intervals. Reference: SciPy `solve_ivp(method="Radau", rtol=1e-8, atol=1e-10)`.

| Mode | Radau | C++ RK4 | Speedup | Maximum state error |
|---|---:|---:|---:|---:|
| ZOH | 1.117 s | 0.00164 s | 681.9x | 6.82e-7 |
| PREG | 1.202 s | 0.00188 s | 637.9x | 1.91e-7 |

The exact speedup depends on CPU, compiler and Python version. The native path targets the currently active nonlinear microgrid plant; unsupported models use the original SciPy solver.
