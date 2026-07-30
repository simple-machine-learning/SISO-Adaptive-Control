# -*- coding: utf-8 -*-
"""Runtime-editable numerical configuration stored in JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_CONFIG_FILE = BASE_DIR / "runtime_config.json"

DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "resample_dt": 0.1,
    "resample_method": "nearest",
    "controller_reference_type": "steps",
    "controller_training_duration_sec": 30.0,
    "controller_reference_d_min": -0.5,
    "controller_reference_d_max": 0.5,
    "reference_tau_1": 1.0,
    "reference_tau_2": 1.0,
    "reference_tau_d": 0.5,
    "plant_n_y": 5,
    "plant_n_u": 5,
    "tau_u": 0.5,
    "plant_batch_lambda": 1.0e-4,
    "plant_lm_lambda": 1.0e-3,
    "plant_gd_ngd_learning": "NGD",
    "plant_gd_ngd_epochs": 5,
    "plant_gd_ngd_eps": 1.0e-4,
    "mu_w": 0.4,
    "ctrl_learning": "GD",
    "ctrl_epochs": 100,
    "mu_v": 0.01,
    "mu_r_0": 0.001,
    "alpha_v": 0.0,
    "alpha_r_0": 0.0,
    "ctrl_eps": 1.0e-4,
    "ctrl_qnu_learning": "NGD",
    "ctrl_qnu_epochs": 100,
    "mu_v_qnu": 0.02,
    "mu_r_0_qnu": 0.0005,
    "alpha_v_qnu": 0.0,
    "alpha_r_0_qnu": 0.0,
    "ctrl_qnu_eps": 1.0e-3,
    "controller_reference_step_hold_sec": 5.0,
    "controller_reference_ramp_period_sec": 20.0,
    "controller_reference_sine_freq_hz": 0.05,
    "q_min": -50.0,
    "q_max": 50.0,
    "u_min": -50.0,
    "u_max": 50.0,
    "r_0_min": 0.0,
    "r_0_max": 20.0,
    "r_0_init": 1.0,
    "v_norm_max": 100.0,
    "qnu_v_norm_max": 100.0,
    "plant_seed": 1,
    "controller_seed": 1,
}


def load_runtime_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_RUNTIME_CONFIG)
    if RUNTIME_CONFIG_FILE.exists():
        try:
            loaded = json.loads(RUNTIME_CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_runtime_config(values: dict[str, Any]) -> dict[str, Any]:
    cfg = load_runtime_config()
    cfg.update(values)
    tmp = RUNTIME_CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(RUNTIME_CONFIG_FILE)
    return cfg


def get_runtime_value(name: str, default: Any = None) -> Any:
    return load_runtime_config().get(name, default)
