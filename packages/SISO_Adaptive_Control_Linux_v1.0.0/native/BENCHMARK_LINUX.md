# Native HONU MPC kernel benchmark

Environment used for the included validation: Linux x86-64, GCC 14.2,
CPython 3.13, NumPy 2.3.5. Prediction horizon: 30; $n_y=4$, $n_u=3$,
input delay: 2 samples; 1500 repeated calls with exact Jacobian.

| Model | Python | C++ | Speedup |
|---|---:|---:|---:|
| LNU | 315.58 us/call | 9.62 us/call | 32.81x |
| QNU | 750.66 us/call | 10.95 us/call | 68.55x |

The benchmark checks predictions and Jacobians against the original Python
implementation with absolute and relative tolerances near $10^{-12}$. Results
will vary with CPU, compiler, Python version, model order, and MPC horizon.
