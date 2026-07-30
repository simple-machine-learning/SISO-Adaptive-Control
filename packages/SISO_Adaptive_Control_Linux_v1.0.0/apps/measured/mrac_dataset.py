# -*- coding: utf-8 -*-
"""NPZ data interface for uniformly resampled measured HONU MRAC data."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


@dataclass
class MRACDataset:
    t: np.ndarray
    u: np.ndarray
    y: np.ndarray
    dt: float
    columns: tuple[str, ...]
    table: np.ndarray
    metadata: dict


def _scalar(value):
    array = np.asarray(value)
    return array.item() if array.ndim == 0 or array.size == 1 else array


def _validate_uniform_time(t: np.ndarray, dt: float) -> None:
    if t.size < 2:
        raise ValueError("At least two samples are required")
    if not np.all(np.isfinite(t)):
        raise ValueError("Time vector contains non-finite values")
    if not np.all(np.diff(t) > 0.0):
        raise ValueError("Time vector must be strictly increasing")
    expected = np.arange(t.size, dtype=float) * dt
    shifted = t - t[0]
    tolerance = max(1.0e-10, abs(dt) * 1.0e-7)
    if not np.allclose(shifted, expected, rtol=1.0e-7, atol=tolerance):
        max_error = float(np.max(np.abs(shifted - expected)))
        raise ValueError(
            f"Dataset is not uniformly sampled at dt={dt:g} s; maximum grid error is {max_error:g} s"
        )


def save_mrac_dataset(filename, t, u, y, dt, *, columns=None, table=None,
                      source="measurement", metadata=None):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.asarray(t, dtype=float).ravel()
    u = np.asarray(u, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if not (t.size == u.size == y.size):
        raise ValueError("t, u and y must have equal lengths")
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(y)):
        raise ValueError("u and y must contain finite values only")

    # Measurements are normalized once during dataset preparation. Numerical
    # identification/control scripts therefore see ordinary signals in standard z-score coordinates
    # and contain no hidden scaling transformations.
    from measured_normalization import normalize_arrays
    u_raw = u.copy(); y_raw = y.copy()
    u, y, normalization = normalize_arrays(u_raw, y_raw)
    dt = float(dt)
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be positive and finite")
    _validate_uniform_time(t, dt)

    if table is None:
        table = np.column_stack((t, u, y))
    table = np.asarray(table, dtype=float).copy()
    if table.ndim != 2 or table.shape[0] != t.size:
        raise ValueError("table must be a 2-D array with one row per sample")
    if columns is None:
        columns = ("t", "u", "y")
    columns = tuple(str(column) for column in columns)
    if len(columns) != table.shape[1]:
        raise ValueError("Number of column names must equal table column count")
    if "u" in columns:
        table[:, columns.index("u")] = u
    if "y" in columns:
        table[:, columns.index("y")] = y

    meta = dict(metadata or {})
    meta["normalization"] = {"kind": "zscore", **normalization}
    meta["signals_are_normalized"] = True
    meta.update({
        "source": str(source),
        "uniform_sampling": True,
        "dt": dt,
        "samples": int(t.size),
    })
    np.savez_compressed(
        path,
        t=t,
        u=u,
        y=y,
        dt=np.array(dt),
        columns=np.asarray(columns, dtype="U"),
        table=table,
        metadata_json=np.array(json.dumps(meta, ensure_ascii=False)),
    )
    from measured_normalization import write_simulated_uy
    write_simulated_uy(path, t, u, y)
    return path


def load_mrac_dataset(filename) -> MRACDataset:
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(str(path))
    with np.load(path, allow_pickle=False) as data:
        required = {"t", "u", "y", "dt"}
        missing = required.difference(data.files)
        if missing:
            raise ValueError(f"Invalid MRAC NPZ file; missing: {sorted(missing)}")
        t = np.asarray(data["t"], dtype=float).ravel()
        u = np.asarray(data["u"], dtype=float).ravel()
        y = np.asarray(data["y"], dtype=float).ravel()
        dt = float(_scalar(data["dt"]))
        columns = tuple(str(item) for item in data["columns"].tolist()) if "columns" in data.files else ("t", "u", "y")
        table = np.asarray(data["table"], dtype=float) if "table" in data.files else np.column_stack((t, u, y))
        metadata = {}
        if "metadata_json" in data.files:
            metadata = json.loads(str(_scalar(data["metadata_json"])))
    if not (t.size == u.size == y.size == table.shape[0]):
        raise ValueError("Inconsistent sample counts in MRAC dataset")
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(y)):
        raise ValueError("Dataset contains non-finite u or y values")
    _validate_uniform_time(t, dt)
    return MRACDataset(t=t, u=u, y=y, dt=dt, columns=columns, table=table, metadata=metadata)


def load_table(filename):
    data = load_mrac_dataset(filename)
    return list(data.columns), data.table, data
