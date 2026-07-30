# -*- coding: utf-8 -*-
"""Reader for MATLAB v7.3 measurement files used by the MRAC data viewer."""

from pathlib import Path
import numpy as np


def _decode_char_dataset(dataset):
    a = np.asarray(dataset[()]).ravel()
    if a.dtype.kind in "ui":
        return "".join(chr(int(v)) for v in a if int(v) != 0)
    return str(a)


def _read_ref_text(file_handle, group, field, index):
    """Read a MATLAB v7.3 referenced text field, returning an empty string if absent."""
    if field not in group:
        return ""
    try:
        return _decode_char_dataset(file_handle[group[field][index, 0]]).strip()
    except (KeyError, TypeError, ValueError, IndexError):
        return ""


def _physical_name(path, fallback, index):
    """Prefer the Simulink signal path over generic port names such as In1/Out1."""
    path = str(path or "").strip().replace("\\", "/")
    if path:
        leaf = path.rsplit("/", 1)[-1].strip()
        if leaf:
            return leaf
    fallback = str(fallback or "").strip()
    return fallback or f"channel_{index + 1}"


def _infer_unit(path, stored_unit):
    """Use stored units, with conservative fallbacks for the supplied experiment."""
    unit = str(stored_unit or "").strip()
    if unit:
        return unit
    leaf = str(path or "").replace("\\", "/").rsplit("/", 1)[-1].upper()
    if leaf == "OMEGA":
        return "Hz"
    if leaf.startswith("ENC_") or leaf.endswith("_MM"):
        return "mm"
    if leaf in {"FA_N", "FB_N"} or leaf.endswith("_N"):
        return "N"
    if leaf == "TRAJECTORY_TYPE":
        return "-"
    return ""


def load_mat_v73_measurement(filename):
    try:
        import h5py
    except ImportError as exc:
        raise ValueError("h5py is required to read MATLAB v7.3 files.") from exc
    with h5py.File(filename, "r") as f:
        roots = [k for k in f.keys() if k != "#refs#"]
        if not roots:
            raise ValueError("No measurement root group found.")
        root = f[roots[0]]
        x_group = root["X"]
        y_group = root["Y"]
        x_axes = []
        for i in range(x_group["Data"].shape[0]):
            x_data = np.asarray(f[x_group["Data"][i, 0]][()]).squeeze()
            x_name = _read_ref_text(f, x_group, "Name", i)
            x_unit = _read_ref_text(f, x_group, "Unit", i)
            x_axes.append((x_name or f"X{i}", x_unit, x_data))
        channels = []
        for i in range(y_group["Data"].shape[0]):
            values = np.asarray(f[y_group["Data"][i, 0]][()]).squeeze()
            generic_name = _read_ref_text(f, y_group, "Name", i)
            signal_path = _read_ref_text(f, y_group, "Path", i)
            description = _read_ref_text(f, y_group, "Description", i)
            name = _physical_name(signal_path, generic_name, i)
            unit = _infer_unit(signal_path, _read_ref_text(f, y_group, "Unit", i))
            x_index = int(np.asarray(f[y_group["XIndex"][i, 0]][()]).squeeze()) - 1
            if x_index < 0 or x_index >= len(x_axes):
                x_index = 0
            t = np.asarray(x_axes[x_index][2], dtype=float).ravel()
            values = np.asarray(values, dtype=float).ravel()
            if len(t) == len(values) and len(t) > 1:
                channels.append({
                    "name": name,
                    "unit": unit,
                    "path": signal_path,
                    "description": description,
                    "generic_name": generic_name,
                    "t": t,
                    "values": values,
                })
        if not channels:
            raise ValueError("No uniformly sampled numeric channels found.")
        return channels


def _parse_txt_header_and_metadata(filename):
    """Return (column_names, metadata) from leading ``#`` lines in a text table."""
    column_names = None
    metadata = {}
    with open(filename, "r", encoding="utf-8-sig", errors="replace") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if not stripped.startswith("#"):
                break
            content = stripped[1:].strip()
            if not content:
                continue
            # Metadata lines use key=value pairs separated by commas.
            if "=" in content:
                for part in content.split(","):
                    if "=" not in part:
                        continue
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key:
                        metadata[key] = value
                continue
            # The first non-metadata comment is interpreted as the column header.
            if column_names is None:
                names = content.replace(",", " " ).replace(";", " " ).split()
                if names:
                    column_names = names
    return column_names, metadata


def load_txt_measurement(filename):
    """Load TXT/CSV/DAT data and expose every numeric column for GUI selection."""
    from collections import OrderedDict
    filename = str(filename)
    names, metadata = _parse_txt_header_and_metadata(filename)
    suffix = Path(filename).suffix.lower()
    delimiters = [","] if suffix == ".csv" else [None, ",", ";", "\t"]
    table = None

    # Standard CSV first row, e.g. time,input,output.
    if not names:
        for delimiter in delimiters:
            try:
                structured = np.genfromtxt(filename, delimiter=delimiter, names=True, comments="#", dtype=float,
                                           encoding="utf-8-sig", autostrip=True)
                if structured.dtype.names and structured.size >= 2:
                    names = list(structured.dtype.names)
                    columns = OrderedDict((name, np.asarray(structured[name], dtype=float).ravel()) for name in names)
                    if all(len(v) == len(next(iter(columns.values()))) for v in columns.values()) and all(np.all(np.isfinite(v)) for v in columns.values()):
                        return {"columns": columns, "metadata": metadata}
            except Exception:
                pass

    if not names:
        raise ValueError("The file must contain column names in its first row or in a commented header such as '# t u y'.")
    last_exc = None
    for delimiter in delimiters:
        try:
            candidate = np.loadtxt(filename, comments="#", delimiter=delimiter, dtype=float, ndmin=2, skiprows=0)
            if candidate.shape[1] == len(names):
                table = candidate; break
        except ValueError as exc:
            last_exc = exc
            try:
                candidate = np.loadtxt(filename, comments="#", delimiter=delimiter, dtype=float, ndmin=2, skiprows=1)
                if candidate.shape[1] == len(names):
                    table = candidate; break
            except ValueError as exc2:
                last_exc = exc2
    if table is None:
        raise ValueError(f"Cannot parse numeric table: {last_exc}")
    if table.shape[0] < 2 or not np.all(np.isfinite(table)):
        raise ValueError("The table must contain at least two finite numeric rows.")
    columns = OrderedDict()
    used = set()
    for index, raw_name in enumerate(names):
        base = str(raw_name).strip() or f"column_{index + 1}"
        name = base; suffix_number = 2
        while name in used:
            name = f"{base}_{suffix_number}"; suffix_number += 1
        used.add(name); columns[name] = np.asarray(table[:, index], dtype=float)
    return {"columns": columns, "metadata": metadata}


# Generic readers used when files do not follow the original experiment export.
def load_generic_mat_measurement(filename):
    """Load ordinary pre-v7.3 MAT files, including nested MATLAB structs."""
    try:
        from scipy.io import loadmat
    except ImportError as exc:
        raise ValueError("This MAT file is not MATLAB v7.3 and scipy is not installed.") from exc

    payload = loadmat(filename, squeeze_me=True, struct_as_record=False)
    arrays = {}

    def collect(value, prefix, depth=0):
        if depth > 8:
            return
        if hasattr(value, "_fieldnames"):
            for field in value._fieldnames or ():
                collect(getattr(value, field), f"{prefix}.{field}" if prefix else field, depth + 1)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not str(key).startswith("__"):
                    collect(item, f"{prefix}.{key}" if prefix else str(key), depth + 1)
            return
        a = np.asarray(value)
        if a.dtype == object:
            for index, item in enumerate(a.ravel()):
                collect(item, f"{prefix}[{index}]", depth + 1)
            return
        if not np.issubdtype(a.dtype, np.number):
            return
        if a.ndim == 1 and a.size >= 2:
            arrays[prefix] = np.asarray(a, dtype=float).ravel()
        elif a.ndim == 2 and 1 in a.shape and a.size >= 2:
            arrays[prefix] = np.asarray(a, dtype=float).ravel()
        elif a.ndim == 2 and min(a.shape) >= 2:
            for column in range(a.shape[1]):
                arrays[f"{prefix}_{column + 1}"] = np.asarray(a[:, column], dtype=float).ravel()

    collect(payload, "")
    arrays = {name.lstrip("."): values for name, values in arrays.items() if name}
    if not arrays:
        raise ValueError("No one-dimensional numeric channels were found in the MAT file.")

    lengths = {}
    for name, values in arrays.items():
        lengths.setdefault(len(values), []).append((name, values))
    common = max(lengths.values(), key=lambda group: (len(group), len(group[0][1])))
    names = [name for name, _ in common]
    aliases = {"t", "time", "timestamp", "tout"}
    time_name = next((name for name in names if name.rsplit(".", 1)[-1].strip().lower() in aliases), None)
    if time_name is None:
        # A monotonic channel is a safe selectable time-axis candidate.
        time_name = next((name for name, values in common if np.all(np.isfinite(values)) and np.all(np.diff(values) > 0)), None)
    if time_name is None:
        raise ValueError("The MAT file contains no strictly increasing numeric time channel.")
    t = dict(common)[time_name]
    channels = [{"name": name, "unit": "", "path": name, "description": "", "generic_name": name,
                 "t": t, "values": values} for name, values in common if name != time_name]
    if not channels:
        raise ValueError("The MAT file contains a time axis but no matching measured channels.")
    return channels
