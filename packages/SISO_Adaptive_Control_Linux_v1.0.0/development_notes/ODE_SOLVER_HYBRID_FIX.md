# Hybrid ODE solver fix

The sampled-data period and ODE integration method are now separated.

- `method="auto"` selects `Radau` for the two LuGre models.
- All other models continue to use the compiled native RK4 backend.
- Explicit `Radau`, `BDF`, `LSODA`, `RK45`, and `DOP853` selections are honored.
- Explicit `native_rk4` keeps the compiled fixed-step backend.
- `dt_ode` is accepted as a distinct internal RK4/adaptive maximum step; `dt_sim` remains a backward-compatible alias.
- There is no silent fallback after a native solver failure.

A one-step finite-state smoke test was run for every discovered plant model. All models passed; LuGre and LuGre2 used Radau, while the remaining models used native RK4.
