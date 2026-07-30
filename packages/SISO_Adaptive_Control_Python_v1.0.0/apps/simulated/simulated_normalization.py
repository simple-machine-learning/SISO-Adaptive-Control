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
    for key in ("scale_u", "scale_y"):
        if not np.isfinite(result[key]) or result[key] <= 0.0:
            raise ValueError(f"Invalid normalization parameter {key}={result[key]!r} in {path}")
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
    header = _parse_dataset_header(uy_file)
    stats = load_stats(stats_file)
    from project_setup import plant_model_name, preg_blackbox_enabled, r_preg, dt

    errors = []
    if header.get("model_name") != str(plant_model_name):
        errors.append(f"model data={header.get('model_name')!r}, setup={plant_model_name!r}")
    if _as_bool(header.get("preg_blackbox_enabled", False)) != bool(preg_blackbox_enabled):
        errors.append(
            f"P-reg mode data={header.get('preg_blackbox_enabled')!r}, setup={preg_blackbox_enabled!r}"
        )
    try:
        data_r_preg = float(header.get("r_preg", "nan"))
    except ValueError:
        data_r_preg = float("nan")
    if bool(preg_blackbox_enabled) and (not np.isfinite(data_r_preg) or not np.isclose(data_r_preg, float(r_preg), rtol=1e-10, atol=1e-12)):
        errors.append(f"r_preg data={data_r_preg!r}, setup={float(r_preg)!r}")
    try:
        data_dt = float(str(header.get("dt", "nan")).split()[0])
    except ValueError:
        data_dt = float("nan")
    if not np.isfinite(data_dt) or not np.isclose(data_dt, float(dt), rtol=1e-10, atol=1e-12):
        errors.append(f"dt data={data_dt!r}, setup={float(dt)!r}")
    if str(stats.get("model_name", "")) != str(plant_model_name):
        errors.append(f"normalization model={stats.get('model_name')!r}, setup={plant_model_name!r}")
    for key, expected in (
        ("preg_blackbox_enabled", bool(preg_blackbox_enabled)),
        ("r_preg", float(r_preg)),
        ("dt", float(dt)),
    ):
        if key not in stats:
            errors.append(f"normalization metadata missing {key}")
            continue
        actual = stats[key]
        if key == "preg_blackbox_enabled":
            if bool(actual) != expected:
                errors.append(f"normalization {key}={actual!r}, setup={expected!r}")
        elif key == "r_preg" and not bool(preg_blackbox_enabled):
            pass
        elif not np.isclose(float(actual), expected, rtol=1e-10, atol=1e-12):
            errors.append(f"normalization {key}={actual!r}, setup={expected!r}")
    if errors:
        raise RuntimeError(
            "Training-data/setup mismatch. Run step 1 again before identification.\n- "
            + "\n- ".join(errors)
        )
    return stats


def load_normalized_uy(uy_file: str | Path, stats_file: str | Path):
    stats = validate_dataset_matches_setup(uy_file, stats_file)
    values = np.loadtxt(uy_file, skiprows=2)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.shape[1] < 3:
        raise ValueError(f"Dataset {uy_file} must contain leading columns t, u, y.")
    return normalize_u(values[:, 1], stats), normalize_y(values[:, 2], stats), stats


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
    for key in ("mu_u", "sigma_u", "scale_u", "mu_y", "sigma_y", "scale_y", "std_multiplier"):
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
