# C++-compiled ODE backend for all physical models

All 37 modules in `apps/simulated/plant_models` are now compiled as C++ extension modules by Cython when `./build_native_linux.sh` is executed. The model `.py` files remain the authoritative source for equations, dataclass parameters, defaults, and GUI-configured values.

The common compiled RK4 interval integrator is `common._physical_ode_native`. The shared functions `simulate_sample_period_zoh()` and `simulate_sample_period_preg()` use it, so the backend is shared by plant-data generation, physical ODE tests, MRAC, HONU MPC, and MLP MPC.

At runtime the expected message is:

```
ODE backend: C++ compiled RK4 + compiled model (<model_name>)
```

If the extension or a compiled model fails, a warning is written to stderr before switching to SciPy. Set `SISO_ODE_NATIVE_STRICT=1` to prohibit fallback and terminate instead. Set `SISO_ODE_NATIVE=0` to disable the native backend explicitly.

Parameter values are not duplicated in C++. The current Python `PlantParams` object is passed to the compiled model at every interval, so parameters edited by the GUI or `project_setup.py` remain effective.

Validation performed: one ZOH interval and one continuous P-feedback interval for every available model; all 37 models returned finite states. A parameter-propagation check changed the crane trolley mass and confirmed a changed native trajectory.

Implementation note: this is Cython-generated C++ and retains CPython object access for model parameters and calls. It avoids a second manually maintained set of 37 equations, but it is not equivalent to a hand-written, fully typed C++ RHS for each model. Performance gains therefore depend on the model and may be modest.
