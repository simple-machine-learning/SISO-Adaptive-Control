"""Smoke-test every physical model with the automatic hybrid ODE policy."""
from types import SimpleNamespace
import numpy as np
import shared_plant_model as plant


def main():
    solver = SimpleNamespace(method="auto", rtol=1e-8, atol=1e-10,
                             dt_sim=0.01, dt_ode=None, max_step_factor=0.1)
    failures = []
    for name in plant.available_models():
        try:
            par = plant.default_params(name)
            x0 = np.asarray(plant.initial_state(par), dtype=float)
            x1 = plant.simulate_sample_period_zoh(x0, 0.1, 0.01, par, solver)
            if not np.all(np.isfinite(x1)):
                raise FloatingPointError("non-finite state")
            print(f"PASS {name}: {plant._selected_ode_method(par, solver)}")
        except Exception as exc:
            failures.append((name, type(exc).__name__, str(exc)))
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    if failures:
        raise SystemExit(f"ODE model audit failed for {len(failures)} model(s)")
    print(f"All {len(plant.available_models())} models passed.")


if __name__ == "__main__":
    main()
