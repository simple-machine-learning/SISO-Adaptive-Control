# Fast ODE backend for all models

The shared plant layer now integrates every model with fixed-step RK4 by default. This removes repeated `solve_ivp` construction and adaptive-solver overhead from each sampled interval.

Environment selection:

- `SISO_ODE_BACKEND=rk4`: fast backend (default)
- `SISO_ODE_BACKEND=scipy`: original SciPy `solve_ivp` reference backend

Validation command:

```bash
python native/test_all_physical_models.py
```

Reference test configuration: 20 sample periods, `dt=0.01 s`, `dt_sim=0.001 s`, constant `u=0.1`. All 37 models passed. Median ODE speedup was about 8.8x; observed range was about 6.2x to 12.3x. Errors were measured against SciPy Radau and remained small in this test configuration.
