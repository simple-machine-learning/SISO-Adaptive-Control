# -*- coding: utf-8 -*-
"""Fixed training-data normalization for the simulated MRAC branch."""
from __future__ import annotations

from pathlib import Path
import numpy as np

STD_MULTIPLIER = 1.0
MIN_SCALE = 1.0e-12


def fit_and_save(data: np.ndarray, stats_file: str | Path, normalized_file: str | Path | None = None, columns=None, model_name="", metadata=None) -> dict:
    """Fit u/y normalization once from module-01 training data and save it."""
    values = np.asarray(data, dtype=float)
    if values.ndim != 2 or values.shape[1] < 3:
        raise ValueError("Simulated data must contain at least common columns t, u, y.")
    u = values[:, 1]
    y = values[:, 2]
    mu_u = float(np.mean(u))
    mu_y = float(np.mean(y))
    sigma_u = float(np.std(u))
    sigma_y = float(np.std(y))
    scale_u = max(STD_MULTIPLIER * sigma_u, MIN_SCALE)
    scale_y = max(STD_MULTIPLIER * sigma_y, MIN_SCALE)
    metadata = dict(metadata or {})
    np.savez(
        stats_file,
        mu_u=mu_u,
        sigma_u=sigma_u,
        scale_u=scale_u,
        mu_y=mu_y,
        sigma_y=sigma_y,
        scale_y=scale_y,
        std_multiplier=STD_MULTIPLIER,
        model_name=str(model_name),
        **metadata,
    )
    normalized = values.copy()
    normalized[:, 1] = (u - mu_u) / scale_u
    normalized[:, 2] = (y - mu_y) / scale_y
    if normalized_file is not None:
        np.savetxt(
            normalized_file,
            normalized,
            fmt="%.10e",
            delimiter="\t",
            header=(
                "\t".join((["t", "u_z", "y_z"] + list(columns[3:])) if columns else ["t", "u_z", "y_z"]) + "\n"
                f"model_name={model_name}, mu_u={mu_u:.17g}, sigma_u={sigma_u:.17g}, scale_u=std_u={scale_u:.17g}, "
                f"mu_y={mu_y:.17g}, sigma_y={sigma_y:.17g}, scale_y=std_y={scale_y:.17g}"
            ),
        )
    return load_stats(stats_file)


def load_stats(stats_file: str | Path) -> dict:
    path = Path(stats_file)
    if not path.exists():
        raise FileNotFoundError(f"Missing simulated normalization metadata: {path}. Run module 01 first.")
    with np.load(path) as data:
        result = {key: (str(data[key]) if data[key].dtype.kind in "USO" else float(data[key])) for key in data.files}
    # Backward compatibility with early Measured exports.
    if "scale_u" not in result and "sigma_u" in result:
        result["scale_u"] = max(float(result["sigma_u"]), MIN_SCALE)
    if "scale_y" not in result and "sigma_y" in result:
        result["scale_y"] = max(float(result["sigma_y"]), MIN_SCALE)
    result.setdefault("sigma_u", result.get("scale_u", MIN_SCALE))
    result.setdefault("sigma_y", result.get("scale_y", MIN_SCALE))
    result.setdefault("std_multiplier", 1.0)
    result.setdefault("model_name", "measured")
    for key in ("scale_u", "scale_y"):
        if key not in result or not np.isfinite(result[key]) or result[key] <= 0.0:
            raise ValueError(f"Invalid normalization parameter {key}={result.get(key)!r} in {path}")
    return result


def normalize_u(u, stats):
    return (np.asarray(u, dtype=float) - stats["mu_u"]) / stats["scale_u"]


def denormalize_u(u_z, stats):
    return stats["mu_u"] + stats["scale_u"] * np.asarray(u_z, dtype=float)


def normalize_y(y, stats):
    return (np.asarray(y, dtype=float) - stats["mu_y"]) / stats["scale_y"]


def denormalize_y(y_z, stats):
    return stats["mu_y"] + stats["scale_y"] * np.asarray(y_z, dtype=float)


def _parse_dataset_header(uy_file: str | Path) -> dict:
    path = Path(uy_file)
    if not path.exists():
        raise FileNotFoundError(f"Missing simulated training data: {path}. Run module 01 first.")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:2]
    if len(lines) < 2:
        raise ValueError(f"Invalid simulated dataset header in {path}. Run module 01 again.")
    text = lines[1].lstrip("# ").strip()
    result = {}
    for item in text.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def validate_dataset_matches_setup(uy_file: str | Path, stats_file: str | Path) -> dict:
    """Validate only the measured data artifacts, not obsolete ODE setup fields."""
    path = Path(uy_file)
    if not path.exists():
        raise FileNotFoundError(f"Missing measured dataset: {path}")
    values = np.loadtxt(path, comments="#", ndmin=2)
    if values.ndim != 2 or values.shape[1] < 3 or len(values) < 3:
        raise ValueError(f"Measured dataset {path} must contain at least three rows and columns t, u, y")
    if not np.all(np.isfinite(values[:, :3])):
        raise ValueError(f"Measured dataset {path} contains non-finite t, u or y")
    if not np.all(np.diff(values[:, 0]) > 0.0):
        raise ValueError(f"Measured dataset {path} time must be strictly increasing")
    return load_stats(stats_file)

def load_normalized_uy(uy_file: str | Path, stats_file: str | Path, target_dt=None):
    """Load measured ``u, y`` and resample them to the requested MRAC period.

    ``target_dt`` is passed explicitly by modules 02 and 03 from the current
    ``dt_MRAC`` GUI value.  The fallback import is retained only for backward
    compatibility with external scripts.
    """
    validate_dataset_matches_setup(uy_file, stats_file)
    values = np.loadtxt(uy_file, comments="#", ndmin=2)
    t = np.asarray(values[:, 0], dtype=float)
    u = np.asarray(values[:, 1], dtype=float)
    y = np.asarray(values[:, 2], dtype=float)
    raw_sample_count = int(t.size)
    raw_dt = float(np.median(np.diff(t)))
    if target_dt is None:
        try:
            from project_setup import dt as configured_dt
            target_dt = float(configured_dt)
        except Exception:
            target_dt = raw_dt
    else:
        target_dt = float(target_dt)
    if not np.isfinite(target_dt) or target_dt <= 0.0:
        raise ValueError(f"Invalid dt_MRAC={target_dt!r}")
    if target_dt < raw_dt * (1.0 - 1e-9):
        raise ValueError(f"dt_MRAC={target_dt:g} s is smaller than active data sampling {raw_dt:g} s")
    if not np.isclose(target_dt, raw_dt, rtol=1e-9, atol=1e-12):
        from measured_resampling import resample_uniform
        _t_resampled, signals, _info = resample_uniform(
            t, np.column_stack((u, y)), target_dt, method="nearest"
        )
        u = signals[:, 0]
        y = signals[:, 1]
    mu_u = float(np.mean(u)); mu_y = float(np.mean(y))
    sigma_u = max(float(np.std(u)), MIN_SCALE); sigma_y = max(float(np.std(y)), MIN_SCALE)
    stats = dict(mu_u=mu_u, sigma_u=sigma_u, scale_u=sigma_u,
                 mu_y=mu_y, sigma_y=sigma_y, scale_y=sigma_y,
                 std_multiplier=1.0, model_name="measured", dt=target_dt)
    Path(stats_file).parent.mkdir(parents=True, exist_ok=True)
    np.savez(stats_file, **stats)
    print(
        f"MRAC measured data: samples={raw_sample_count} -> {len(u)}, "
        f"dt_data={raw_dt:.9g} s, dt_MRAC={target_dt:.9g} s"
    )
    return normalize_u(u, stats), normalize_y(y, stats), stats

def artifact_stats_file(artifact_file: str | Path) -> Path:
    path = Path(artifact_file)
    return path.with_name(path.name + ".normalization.npz")


def save_artifact_stats(artifact_file: str | Path, stats: dict, artifact_kind: str = "") -> Path:
    """Save an exact scalar copy of the normalization and dataset metadata."""
    target = artifact_stats_file(artifact_file)
    payload = {}
    for key, value in stats.items():
        array = np.asarray(value)
        if array.ndim == 0:
            payload[key] = value
    payload["artifact_kind"] = str(artifact_kind)
    np.savez(target, **payload)
    return target


def load_artifact_stats(artifact_file: str | Path) -> dict:
    target = artifact_stats_file(artifact_file)
    if not target.exists():
        raise FileNotFoundError(
            f"Missing normalization sidecar {target}. Retrain the corresponding artifact from module 01 data."
        )
    return load_stats(target)


def assert_same_stats(a: dict, b: dict, context: str = "normalization") -> None:
    mismatches = []
    for key in ("mu_u", "sigma_u", "scale_u", "mu_y", "sigma_y", "scale_y", "std_multiplier", "dt"):
        if key not in a or key not in b or not np.isclose(float(a[key]), float(b[key]), rtol=1e-12, atol=1e-14):
            mismatches.append(f"{key}: {a.get(key)!r} != {b.get(key)!r}")
    if str(a.get("model_name", "")) != str(b.get("model_name", "")):
        mismatches.append(f"model_name: {a.get('model_name')!r} != {b.get('model_name')!r}")
    if mismatches:
        raise RuntimeError(context + " mismatch:\n- " + "\n- ".join(mismatches))


def normalize_error(error, stats):
    """Normalize a difference of two y-dimensional quantities; means cancel."""
    return np.asarray(error, dtype=float) / stats["scale_y"]


def denormalize_error(error_z, stats):
    return stats["scale_y"] * np.asarray(error_z, dtype=float)
