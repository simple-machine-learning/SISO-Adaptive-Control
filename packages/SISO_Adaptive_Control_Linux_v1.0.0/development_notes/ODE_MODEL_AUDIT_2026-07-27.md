# ODE model audit (2026-07-27)

## Confirmed findings

1. `shared_plant_model.py` used `os` and `sys` without importing them. Fixed.
2. The ImportError handler discarded the real import exception. Fixed to preserve it.
3. `common/numba_ode.py` compiled only helper functions whose names began with `_`. The LuGre models use public helpers `stribeck_function()` and `friction_force()`, so Numba always rejected them. Fixed by compiling all local numerical helpers except the public model API.
4. `solver.method = "Radau"` is currently metadata only on the mandatory native path. The native backend always performs explicit fixed-step RK4.
5. `two_mass_actuator_grounded_m2_lugre2` has no dedicated entry in `MODEL_RECOMMENDED_PRESETS`.
6. A 10 s random-step comparison against SciPy Radau showed:
   - RK4 `dt=0.01 s`: overflow near 0.67 s.
   - RK4 `dt=0.001 s`: finite but grossly inaccurate (final y2 about 0.024 vs Radau about 3.672).
   - RK4 `dt=0.0001 s`: agrees with Radau to about 1.6e-7 in infinity norm.
   - RK4 `dt=0.00005 s`: agrees with Radau to about 2.9e-9.

Therefore a merely finite trajectory is not evidence of an accurate simulation. For LuGre2, 1 ms is stable-looking but wrong under the tested excitation. The visually different trajectory at 0.1 ms is the converged trajectory, not a degradation caused by the smaller step.

## Remaining design issue

The GUI exposes `dt_sim` both as output sampling and native RK4 integration resolution. These should be separated. A robust implementation should keep the requested sample grid while using either model-specific internal substeps or a true stiff solver for LuGre models.
