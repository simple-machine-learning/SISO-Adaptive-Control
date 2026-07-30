# Full HONU MPC optimizer benchmark

Environment: Linux x86-64, CPython 3.13, NumPy, C++17 `-O3`.
Test: prediction horizon 30, `ny=3`, `nu=3`, delay 1, 10 optimizer iterations maximum.

| Model | Python optimizer | C++ full optimizer | Speedup |
|---|---:|---:|---:|
| LNU | 2.198 ms | 0.104 ms | 21.1x |
| QNU | 15.234 ms | 0.358 ms | 42.6x |

The optimized control sequence and final objective were checked against the Python reference. The observed maximum LNU control-sequence difference was approximately `3.1e-8`; QNU agreed at machine precision in the validation case.

Run locally with:

```bash
python native/test_full_optimizer.py
```
