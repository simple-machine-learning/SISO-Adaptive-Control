# -*- coding: utf-8 -*-
"""Integrated measured-data page for HONU MRAC."""

from __future__ import annotations

from pathlib import Path
import threading
import traceback

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal, QTimer, QObject, QSignalBlocker
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget, QApplication,
)

from measured_data_io import load_mat_v73_measurement, load_generic_mat_measurement, load_txt_measurement
from measured_import import import_selected_arrays
from measured_resampling import resample_uniform
from runtime_config import load_runtime_config, save_runtime_config




class _MeasuredLoadSignals(QObject):
    loaded = Signal(object)
    failed = Signal(str)


def _read_measurement_payload(path: Path) -> dict:
    """Read and validate a measurement without touching Qt widgets."""
    path = Path(path).expanduser()
    suffix = path.suffix.lower()
    if suffix == ".mat":
        # MATLAB v7.3 is HDF5, but MAT files normally reserve a 512-byte
        # user block, so the HDF5 signature is not necessarily at byte zero.
        # Check both legal positions used by MATLAB instead of misclassifying
        # v7.3 files as legacy MAT files.
        hdf5_signature = b"\x89HDF\r\n\x1a\n"
        with path.open("rb") as handle:
            signature_0 = handle.read(8)
            handle.seek(512)
            signature_512 = handle.read(8)
        is_hdf5 = signature_0 == hdf5_signature or signature_512 == hdf5_signature
        channels = load_mat_v73_measurement(path) if is_hdf5 else load_generic_mat_measurement(path)
        if not channels:
            raise ValueError("No numeric measurement channels were found.")
        groups = {}
        for channel in channels:
            channel_t = np.asarray(channel["t"], dtype=float).ravel()
            if channel_t.size < 2:
                continue
            key = (channel_t.size, round(float(channel_t[0]), 12), round(float(channel_t[-1]), 12))
            groups.setdefault(key, []).append(channel)
        if not groups:
            raise ValueError("No numeric channels with a usable time axis were found.")
        common = max(groups.values(), key=lambda group: (len(group), len(group[0]["t"])))
        t = np.asarray(common[0]["t"], dtype=float).ravel()
        signals = {}
        for i, channel in enumerate(common):
            channel_t = np.asarray(channel["t"], dtype=float).ravel()
            values = np.asarray(channel["values"], dtype=float).ravel()
            if len(values) != len(t) or not np.allclose(channel_t, t, rtol=1e-10, atol=1e-12):
                continue
            base = str(channel.get("name") or f"channel_{i}")
            name = base if base not in signals else f"{base}_{i}"
            unit = str(channel.get("unit") or "")
            if unit:
                name = f"{name} [{unit}]"
            signals[name] = values
        if len(t) < 2 or not signals:
            raise ValueError("No channels sharing a valid common time axis were found.")
        return {"path": path, "kind": "mat", "t": t, "signals": signals}
    if suffix in {".txt", ".dat", ".csv"}:
        payload = load_txt_measurement(path)
        columns = dict(payload["columns"])
        if len(columns) < 3:
            raise ValueError("TXT data must contain at least three numeric columns for t, u and y selection.")
        return {"path": path, "kind": "txt", "columns": columns, "metadata": dict(payload.get("metadata", {}))}
    if suffix in {".npy", ".npz"}:
        if suffix == ".npz":
            with np.load(path, allow_pickle=False) as z:
                arrays = {name: np.asarray(z[name], dtype=float).ravel() for name in z.files if np.asarray(z[name]).ndim == 1}
            if not arrays:
                raise ValueError("NPZ contains no one-dimensional numeric arrays.")
        else:
            a = np.asarray(np.load(path, allow_pickle=False), dtype=float)
            if a.ndim != 2 or a.shape[1] < 3:
                raise ValueError("NPY must be a two-dimensional array with at least three columns.")
            arrays = {f"column_{i+1}": a[:, i] for i in range(a.shape[1])}
        lengths = {len(v) for v in arrays.values()}
        if len(lengths) != 1 or next(iter(lengths)) < 2:
            raise ValueError("NumPy channels must have equal lengths and at least two samples.")
        return {"path": path, "kind": "numpy", "columns": arrays, "metadata": {}}
    raise ValueError(f"Unsupported measured-data file type: {suffix or '(none)'}")


class MeasurementViewBox(pg.ViewBox):
    resetRequested = Signal()

    def __init__(self):
        super().__init__()
        self.setMouseMode(pg.ViewBox.RectMode)

    def mouseDoubleClickEvent(self, event):
        self.resetRequested.emit()
        event.accept()


class MeasuredDataPage(QWidget):
    """Load, inspect, select, resample and activate measured MRAC data."""

    datasetExported = Signal(object)
    backRequested = Signal()

    def __init__(self, base_dir: Path, project_setup_file: Path, parent=None):
        super().__init__(parent)
        self.base_dir = Path(base_dir)
        self.project_setup_file = Path(project_setup_file)
        self.dataset_role = "training"
        self.file_path: Path | None = None
        self.t: np.ndarray | None = None
        self.signals: dict[str, np.ndarray] = {}
        self.source_kind = ""
        self.txt_columns: dict[str, np.ndarray] = {}
        self.txt_metadata: dict[str, str] = {}
        self._valid_txt_time_column = ""
        self.dt_original = np.nan
        self.plot_widgets: list[pg.PlotWidget] = []
        self.curves: dict[str, pg.PlotDataItem] = {}
        self.sample_curves: dict[str, pg.PlotDataItem] = {}
        self.start_lines: list[pg.InfiniteLine] = []
        self.stop_lines: list[pg.InfiniteLine] = []
        self._syncing_interval = False
        self._base_plot = None
        self._display_timer = QTimer(self)
        self._display_timer.setSingleShot(True)
        self._display_timer.setInterval(35)
        self._display_timer.timeout.connect(self._update_visible_plot_data)
        self._load_signals = _MeasuredLoadSignals(self)
        self._load_signals.loaded.connect(self._on_async_load_finished)
        self._load_signals.failed.connect(self._on_async_load_failed)
        self._load_thread = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.btn_back = QPushButton("Back to MRAC results")
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_open = QPushButton("Open measured-data file")
        self.btn_open.clicked.connect(self.open_data_file)
        # Keep the two primary data-page actions slightly wider than their
        # natural text width while preserving platform-native button height.
        self.btn_back.setMinimumWidth(int(round(self.btn_back.sizeHint().width() * 1.10)))
        self.btn_open.setMinimumWidth(int(round(self.btn_open.sizeHint().width() * 1.10)))
        self._global_line_width = 2.0
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.25, 10.0)
        self.line_width_spin.setDecimals(2)
        self.line_width_spin.setSingleStep(0.25)
        self.line_width_spin.setFixedWidth(76)
        self.line_width_spin.setAlignment(Qt.AlignRight)
        self.line_width_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.line_width_spin.setKeyboardTracking(False)
        self.line_width_spin.setValue(float(self._global_line_width))
        self.line_width_spin.setToolTip("Line width in pixels. Sample-point markers scale together with the curves.")
        self.line_width_spin.valueChanged.connect(self._on_line_width_changed)
        self.line_width_label = QLabel("line width [px]")
        self.file_label = QLabel("No measurement loaded")
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.btn_back)
        top.addWidget(self.btn_open)
        top.addSpacing(8)
        top.addWidget(self.file_label, 1)
        top.addWidget(self.line_width_label)
        top.addWidget(self.line_width_spin)
        root.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls.setMinimumWidth(320)
        controls.setMaximumWidth(430)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 4, 0)
        controls_layout.addWidget(QLabel("Displayed channels"))

        self.channel_list = QListWidget()
        self.channel_list.itemChanged.connect(self.rebuild_plots)
        controls_layout.addWidget(self.channel_list, 1)

        form = QFormLayout()
        self.t_combo = QComboBox()
        self.u_combo = QComboBox()
        self.y_combo = QComboBox()
        self.t_combo.currentTextChanged.connect(self._apply_txt_time_column)
        self.u_combo.currentTextChanged.connect(self._on_role_channel_changed)
        self.y_combo.currentTextChanged.connect(self._on_role_channel_changed)
        self.t_start_spin = QDoubleSpinBox()
        self.t_stop_spin = QDoubleSpinBox()
        self.dt_spin = QDoubleSpinBox()
        self.resample_method_combo = QComboBox()
        self.resample_method_combo.addItem("Nearest original sample (no filter)", "nearest")
        self.resample_method_combo.setEnabled(False)
        for spin in (self.t_start_spin, self.t_stop_spin, self.dt_spin):
            spin.setDecimals(9)
            spin.setRange(-1e12, 1e12)
        self.dt_spin.setMinimum(1e-9)
        self.t_start_spin.valueChanged.connect(self.update_lines_from_spins)
        self.t_stop_spin.valueChanged.connect(self.update_lines_from_spins)
        self.dt_spin.valueChanged.connect(self._update_visible_plot_data)
        form.addRow("t", self.t_combo)
        form.addRow("u", self.u_combo)
        form.addRow("y", self.y_combo)
        form.addRow("t start [s]", self.t_start_spin)
        form.addRow("t stop [s]", self.t_stop_spin)
        form.addRow("dt MRAC / dt MPC [s]", self.dt_spin)
        form.addRow("Resampling", self.resample_method_combo)
        controls_layout.addLayout(form)

        self.sampling_label = QLabel("dt original: -\nfs original: -\nselected samples: -")
        self.sampling_label.setWordWrap(True)
        controls_layout.addWidget(self.sampling_label)

        self.btn_export = QPushButton("Resample measured data (nearest, no filter)")
        self.btn_export.clicked.connect(self.export_dataset)
        controls_layout.addWidget(self.btn_export)
        splitter.addWidget(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(0, 0, 0, 0)
        self.plots_layout.setSpacing(8)
        self.plots_layout.addStretch(1)
        self.scroll.setWidget(self.plots_container)
        splitter.addWidget(self.scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 1200])
        root.addWidget(splitter, 1)

    def open_data_file(self):
        """Open one measured-data file without any visible file-type selector."""
        start_dir = self.base_dir / "data" / "raw"
        try:
            start_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            start_dir = Path.home()

        dialog = QFileDialog(self, "Open measured-data file", str(start_dir))
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setDirectory(str(start_dir))
        # A wildcard name filter makes every directory entry visible. The
        # corresponding controls are hidden because the application chooses
        # the loader only after selection from the filename suffix.
        dialog.setNameFilter("*")
        for object_name in ("fileTypeCombo", "fileTypeLabel"):
            widget = dialog.findChild(QWidget, object_name)
            if widget is not None:
                widget.hide()

        if dialog.exec() != QFileDialog.Accepted:
            return
        selected = dialog.selectedFiles()
        if selected:
            self._start_async_load(Path(selected[0]))

    def open_mat_file(self):
        """Backward-compatible alias used by older GUI code."""
        self.open_data_file()

    def _start_async_load(self, path: Path):
        if self._load_thread is not None and self._load_thread.is_alive():
            return
        path = Path(path).expanduser()
        supported = {".mat", ".txt", ".dat", ".csv", ".npy", ".npz"}
        if path.suffix.lower() not in supported:
            QMessageBox.warning(
                self,
                "Unsupported data file",
                "Select a MAT, TXT, DAT, CSV, NPY or NPZ file.",
            )
            return
        self.btn_open.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.file_label.setText(f"Loading {path.name} ...")

        def worker():
            try:
                payload = _read_measurement_payload(path)
            except Exception as exc:
                self._load_signals.failed.emit(f"{path.name}: {exc}")
            else:
                self._load_signals.loaded.emit(payload)

        self._load_thread = threading.Thread(target=worker, name="measured-data-loader", daemon=True)
        self._load_thread.start()

    def _on_async_load_finished(self, payload):
        self._load_thread = None
        self.btn_open.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.setUpdatesEnabled(False)
        try:
            self._apply_loaded_payload(payload)
        except Exception as exc:
            self._on_async_load_failed(str(exc))
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def _on_async_load_failed(self, message: str):
        self._load_thread = None
        self.btn_open.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.file_label.setText("Data loading failed")
        QMessageBox.critical(self, "Data loading failed", str(message))

    def load_data_path(self, path: Path):
        """Synchronous API retained for tests and scripted use."""
        path = Path(path).expanduser()
        if not path.is_file():
            QMessageBox.critical(self, "Data loading failed", f"Measured-data file does not exist:\n{path}")
            return False
        try:
            return bool(self._apply_loaded_payload(_read_measurement_payload(path)))
        except Exception as exc:
            QMessageBox.critical(self, "Data loading failed", f"{path.name}: {exc}")
            return False

    def _set_time_controls(self, t: np.ndarray, dt: float):
        """Initialize time controls without triggering repeated plot rebuilds."""
        blockers = [
            QSignalBlocker(self.t_start_spin),
            QSignalBlocker(self.t_stop_spin),
            QSignalBlocker(self.dt_spin),
        ]
        try:
            t0 = float(t[0]); t1 = float(t[-1])
            self.t_start_spin.setRange(t0, t1)
            self.t_stop_spin.setRange(t0, t1)
            self.t_start_spin.setValue(t0)
            self.t_stop_spin.setValue(t1)
            self.dt_spin.setValue(float(dt))
        finally:
            del blockers

    def _apply_loaded_payload(self, payload: dict):
        path = Path(payload["path"])
        kind = str(payload["kind"])
        if kind == "mat":
            self.file_path = path
            self.source_kind = "mat"
            self.txt_columns = {}
            self.txt_metadata = {}
            self._valid_txt_time_column = ""
            self.t = np.asarray(payload["t"], dtype=float)
            self.signals = {k: np.asarray(v, dtype=float) for k, v in payload["signals"].items()}
            dt_values = np.diff(self.t)
            dt_values = dt_values[np.isfinite(dt_values) & (dt_values > 0.0)]
            if dt_values.size == 0:
                raise ValueError("The MAT time axis does not define a valid positive sampling interval.")
            self.dt_original = float(np.median(dt_values))
            self.file_label.setText(str(path))
            self.t_combo.blockSignals(True)
            self.t_combo.clear(); self.t_combo.addItem("MAT time axis"); self.t_combo.setEnabled(False)
            self.t_combo.blockSignals(False)
            self._populate_channels()
            self._set_time_controls(self.t, self.dt_original)
            self.rebuild_plots(); self._update_sampling_info()
            return True
        columns = dict(payload["columns"])
        self.file_path = path
        self.source_kind = "txt"
        self.txt_columns = columns
        self.txt_metadata = dict(payload.get("metadata", {}))
        self.file_label.setText(str(path))
        self.t_combo.blockSignals(True); self.t_combo.clear(); self.t_combo.addItems(list(columns))
        t_index = next((i for i, name in enumerate(columns) if name.strip().lower() in {"t", "time", "timestamp", "tout"}), 0)
        self.t_combo.setCurrentIndex(t_index); self.t_combo.setEnabled(True); self.t_combo.blockSignals(False)
        self._apply_txt_time_column(self.t_combo.currentText())
        self.source_kind = kind
        return self.t is not None and bool(self.signals)

    def load_numpy_path(self, path: Path):
        try:
            if path.suffix.lower() == ".npz":
                z = np.load(path, allow_pickle=False)
                arrays = {name: np.asarray(z[name], dtype=float).ravel() for name in z.files if np.asarray(z[name]).ndim == 1}
                if not arrays:
                    raise ValueError("NPZ contains no one-dimensional numeric arrays.")
            else:
                a = np.asarray(np.load(path, allow_pickle=False), dtype=float)
                if a.ndim != 2 or a.shape[1] < 3:
                    raise ValueError("NPY must be a two-dimensional array with at least three columns.")
                arrays = {f"column_{i+1}": a[:, i] for i in range(a.shape[1])}
            lengths = {len(v) for v in arrays.values()}
            if len(lengths) != 1 or next(iter(lengths)) < 2:
                raise ValueError("NumPy channels must have equal lengths and at least two samples.")
        except Exception as exc:
            raise ValueError(f"NumPy loading failed: {exc}") from exc
        self.file_path = Path(path); self.source_kind = "numpy"; self.txt_columns = arrays; self.txt_metadata = {}
        self.file_label.setText(str(self.file_path))
        self.t_combo.blockSignals(True); self.t_combo.clear(); self.t_combo.addItems(list(arrays))
        t_index = next((i for i,n in enumerate(arrays) if n.strip().lower() in {"t","time","timestamp"}), 0)
        self.t_combo.setCurrentIndex(t_index); self.t_combo.setEnabled(True); self.t_combo.blockSignals(False)
        self.source_kind = "txt"
        self._apply_txt_time_column(self.t_combo.currentText())
        self.source_kind = "numpy"
        return True

    def load_mat_path(self, path: Path):
        """Load a MAT file directly; used by both the dialog and the main GUI."""
        try:
            mat_path = Path(path)
            with mat_path.open("rb") as handle:
                is_hdf5 = handle.read(8) == b"\x89HDF\r\n\x1a\n"
            channels = load_mat_v73_measurement(mat_path) if is_hdf5 else load_generic_mat_measurement(mat_path)
            if not channels:
                raise ValueError("No numeric measurement channels were found.")
            groups: dict[tuple[int, float, float], list[dict]] = {}
            for channel in channels:
                channel_t = np.asarray(channel["t"], dtype=float).ravel()
                if channel_t.size < 2:
                    continue
                key = (channel_t.size, round(float(channel_t[0]), 12), round(float(channel_t[-1]), 12))
                groups.setdefault(key, []).append(channel)
            if not groups:
                raise ValueError("No numeric channels with a usable time axis were found.")
            common = max(groups.values(), key=lambda group: (len(group), len(group[0]["t"])))
            t = np.asarray(common[0]["t"], dtype=float).ravel()
            signals: dict[str, np.ndarray] = {}
            for i, channel in enumerate(common):
                channel_t = np.asarray(channel["t"], dtype=float).ravel()
                values = np.asarray(channel["values"], dtype=float).ravel()
                if len(values) != len(t) or not np.allclose(channel_t, t, rtol=1e-10, atol=1e-12):
                    continue
                base = str(channel.get("name") or f"channel_{i}")
                name = base if base not in signals else f"{base}_{i}"
                unit = str(channel.get("unit") or "")
                if unit:
                    name = f"{name} [{unit}]"
                signals[name] = values
            if len(t) < 2 or not signals:
                raise ValueError("No channels sharing a valid common time axis were found.")
        except Exception as exc:
            raise ValueError(f"MAT loading failed: {exc}") from exc

        self.file_path = Path(path)
        self.source_kind = "mat"
        self.txt_columns = {}
        self.txt_metadata = {}
        self._valid_txt_time_column = ""
        self.t = t
        self.signals = signals
        dt_values = np.diff(t)
        dt_values = dt_values[np.isfinite(dt_values) & (dt_values > 0.0)]
        if dt_values.size == 0:
            raise ValueError("The MAT time axis does not define a valid positive sampling interval.")
        self.dt_original = float(np.median(dt_values))
        self.file_label.setText(str(self.file_path))
        self.t_combo.blockSignals(True)
        self.t_combo.clear()
        self.t_combo.addItem("MAT time axis")
        self.t_combo.setEnabled(False)
        self.t_combo.blockSignals(False)
        self._populate_channels()
        self._set_time_controls(t, self.dt_original)
        self.rebuild_plots()
        self._update_sampling_info()
        return True

    def load_txt_path(self, path: Path):
        """Load a generic numeric TXT table and keep t, u and y manually selectable."""
        try:
            payload = load_txt_measurement(Path(path))
            columns = dict(payload["columns"])
            if len(columns) < 3:
                raise ValueError("TXT data must contain at least three numeric columns for t, u and y selection.")
        except Exception as exc:
            raise ValueError(f"Text-table loading failed: {exc}") from exc

        self.file_path = Path(path)
        self.source_kind = "txt"
        self.txt_columns = columns
        self.txt_metadata = dict(payload.get("metadata", {}))
        self.file_label.setText(str(self.file_path))

        self.t_combo.blockSignals(True)
        self.t_combo.clear()
        self.t_combo.addItems(list(columns))
        t_index = next((i for i, name in enumerate(columns) if name.strip().lower() in {"t", "time", "timestamp"}), 0)
        self.t_combo.setCurrentIndex(t_index)
        self.t_combo.setEnabled(True)
        self.t_combo.blockSignals(False)
        self._apply_txt_time_column(self.t_combo.currentText())
        return self.t is not None and bool(self.signals)

    def _apply_txt_time_column(self, name: str):
        if self.source_kind != "txt" or not self.txt_columns or name not in self.txt_columns:
            return
        t = np.asarray(self.txt_columns[name], dtype=float).ravel()
        if t.size < 2 or not np.all(np.isfinite(t)):
            QMessageBox.warning(self, "Invalid time column", "The selected time column must contain at least two finite values.")
            self._restore_valid_txt_time_column()
            return
        dt_values = np.diff(t)
        if not np.all(dt_values > 0.0):
            QMessageBox.warning(self, "Invalid time column", "The selected time column must be strictly increasing.")
            self._restore_valid_txt_time_column()
            return

        previous_u = self.u_combo.currentText()
        previous_y = self.y_combo.currentText()
        self._valid_txt_time_column = name
        self.t = t
        self.signals = {key: np.asarray(value, dtype=float).ravel() for key, value in self.txt_columns.items() if key != name}
        self.dt_original = float(np.median(dt_values))
        self._populate_channels(preferred_u=previous_u, preferred_y=previous_y)

        metadata_dt = self.txt_metadata.get("dt", "")
        parsed_dt = None
        if metadata_dt:
            try:
                parsed_dt = float(str(metadata_dt).split()[0])
            except (TypeError, ValueError):
                parsed_dt = None
        target_dt = parsed_dt if parsed_dt and parsed_dt > 0.0 else float(self.dt_original)
        self._set_time_controls(t, target_dt)
        self.rebuild_plots()
        self._update_sampling_info()

    def _restore_valid_txt_time_column(self):
        if not self._valid_txt_time_column:
            return
        self.t_combo.blockSignals(True)
        self.t_combo.setCurrentText(self._valid_txt_time_column)
        self.t_combo.blockSignals(False)

    def _on_role_channel_changed(self, *_args):
        """Keep manually selected u and y visible in the inspection plots."""
        selected = {self.u_combo.currentText(), self.y_combo.currentText()}
        changed = False
        self.channel_list.blockSignals(True)
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            if item.text() in selected and item.checkState() != Qt.Checked:
                item.setCheckState(Qt.Checked)
                changed = True
        self.channel_list.blockSignals(False)
        if changed:
            self.rebuild_plots()
        else:
            self.update_channel_colors()

    def _populate_channels(self, preferred_u: str = "", preferred_y: str = ""):
        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        self.u_combo.clear()
        self.y_combo.clear()
        for i, name in enumerate(self.signals):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if i < 4 else Qt.Unchecked)
            self.channel_list.addItem(item)
            self.u_combo.addItem(name)
            self.y_combo.addItem(name)
        names = list(self.signals)
        if preferred_u in self.signals:
            u_index = names.index(preferred_u)
        else:
            u_index = next((i for i, name in enumerate(names) if name.strip().lower() == "u"),
                           next((i for i, name in enumerate(names) if "omega" in name.lower()), 0))
        if preferred_y in self.signals:
            y_index = names.index(preferred_y)
        else:
            y_index = next((i for i, name in enumerate(names) if name.strip().lower() == "y"),
                           next((i for i, name in enumerate(names) if "enc_b_from_0" in name.lower()),
                                1 if self.y_combo.count() > 1 else 0))
        if self.u_combo.count():
            self.u_combo.setCurrentIndex(u_index)
        if self.y_combo.count():
            self.y_combo.setCurrentIndex(y_index)
        self.channel_list.blockSignals(False)

    def checked_channels(self):
        return [
            self.channel_list.item(i).text()
            for i in range(self.channel_list.count())
            if self.channel_list.item(i).checkState() == Qt.Checked
        ]

    def _clear_plots(self):
        while self.plots_layout.count():
            item = self.plots_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.plot_widgets.clear()
        self.curves.clear()
        self.sample_curves.clear()
        self.start_lines.clear()
        self.stop_lines.clear()

    def rebuild_plots(self):
        self._clear_plots()
        if self.t is None:
            message = QLabel("Open a MAT or TXT file to display measured channels.")
            message.setAlignment(Qt.AlignCenter)
            self.plots_layout.addWidget(message)
            self.plots_layout.addStretch(1)
            return

        names = self.checked_channels()
        if not names:
            message = QLabel("Select at least one channel.")
            message.setAlignment(Qt.AlignCenter)
            self.plots_layout.addWidget(message)
            self.plots_layout.addStretch(1)
            return

        base_plot = None
        width = float(self._global_line_width)
        for row, name in enumerate(names):
            view_box = MeasurementViewBox()
            plot = pg.PlotWidget(viewBox=view_box)
            plot.setBackground("w")
            plot.setMinimumHeight(220)
            plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            plot.showGrid(x=True, y=True, alpha=0.18)
            plot.setLabel("left", name)
            plot.setLabel("bottom", f"t [s], dt={self.dt_original:.9g} s" if row == len(names) - 1 else "")
            plot.setMenuEnabled(True)
            plot.setMouseEnabled(x=True, y=True)
            if base_plot is None:
                base_plot = plot
                self._base_plot = plot
            else:
                plot.setXLink(base_plot)
            curve = plot.plot([], [], pen=pg.mkPen("g", width=width),
                              autoDownsample=True, clipToView=True, skipFiniteCheck=True,
                              name="original")
            sample_ring = plot.plot([], [], pen=None, symbol="o",
                                    symbolSize=self._sample_symbol_size(width),
                                    symbolPen=pg.mkPen("b", width=self._sample_symbol_pen_width(width)),
                                    symbolBrush=pg.mkBrush("b"),
                                    name="downsampled")
            view_box.resetRequested.connect(self._reset_all_plots)
            self.curves[name] = curve
            self.sample_curves[name] = sample_ring
            self.plot_widgets.append(plot)
            self.plots_layout.addWidget(plot)

        self.plots_layout.addStretch(1)
        self._create_interval_lines()
        if self._base_plot is not None:
            self._base_plot.sigXRangeChanged.connect(self._on_visible_range_changed)
            self._base_plot.setXRange(float(self.t[0]), float(self.t[-1]), padding=0.01)
        self._update_visible_plot_data()
        for plot in self.plot_widgets:
            plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
            plot.autoRange()


    def _on_visible_range_changed(self, plot, view_range):
        self._schedule_visible_update()
        if self.t is None or self._syncing_interval:
            return
        x0, x1 = view_range
        x0 = max(float(self.t[0]), min(float(self.t[-1]), float(x0)))
        x1 = max(float(self.t[0]), min(float(self.t[-1]), float(x1)))
        if x1 > x0:
            self._syncing_interval = True
            self.t_start_spin.setValue(x0)
            self.t_stop_spin.setValue(x1)
            for line in self.start_lines:
                line.setValue(x0)
            for line in self.stop_lines:
                line.setValue(x1)
            self._syncing_interval = False
            self._update_sampling_info()

    def _schedule_visible_update(self, *args):
        self._display_timer.start()

    def _reset_all_plots(self):
        if self.t is None or self._base_plot is None:
            return
        self._base_plot.setXRange(float(self.t[0]), float(self.t[-1]), padding=0.01)
        for plot in self.plot_widgets:
            plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        self._update_visible_plot_data()

    def _update_visible_plot_data(self):
        if self.t is None or not self.curves:
            return
        if self._base_plot is None:
            x_min, x_max = float(self.t[0]), float(self.t[-1])
        else:
            x_min, x_max = self._base_plot.viewRange()[0]
        i0 = max(0, int(np.searchsorted(self.t, x_min, side="left")) - 1)
        i1 = min(len(self.t), int(np.searchsorted(self.t, x_max, side="right")) + 1)
        if i1 <= i0:
            return
        visible_count = i1 - i0
        max_points = 6000
        step = max(1, int(np.ceil(visible_count / max_points)))
        idx = np.arange(i0, i1, step, dtype=int)
        if idx.size == 0 or idx[-1] != i1 - 1:
            idx = np.append(idx, i1 - 1)
        tx = self.t[idx]

        # Display sample markers only in the visible range.  The previous code
        # generated markers for the complete selected interval for every curve,
        # which could allocate millions of points and freeze the Qt event loop.
        marker_t = np.empty(0, dtype=float)
        marker_idx = np.empty(0, dtype=int)
        dt_target = float(self.dt_spin.value())
        if np.isfinite(dt_target) and dt_target > 0.0:
            t0 = max(float(self.t_start_spin.value()), float(self.t[0]), float(x_min))
            t1 = min(float(self.t_stop_spin.value()), float(self.t[-1]), float(x_max))
            if t1 >= t0:
                estimated = int(np.floor((t1 - t0) / dt_target)) + 1
                max_markers = 4000
                display_dt = dt_target * max(1, int(np.ceil(estimated / max_markers)))
                marker_t = np.arange(t0, t1 + 0.5 * display_dt, display_dt)
                if marker_t.size:
                    marker_idx = np.searchsorted(self.t, marker_t, side="left")
                    marker_idx = np.clip(marker_idx, 0, len(self.t) - 1)
                    left = np.maximum(marker_idx - 1, 0)
                    choose_left = np.abs(self.t[left] - marker_t) <= np.abs(self.t[marker_idx] - marker_t)
                    marker_idx[choose_left] = left[choose_left]

        for name, curve in self.curves.items():
            curve.setData(tx, self.signals[name][idx], skipFiniteCheck=True)
            samples = self.sample_curves[name]
            if marker_idx.size:
                samples.setData(self.t[marker_idx], self.signals[name][marker_idx], skipFiniteCheck=True)
            else:
                samples.setData([], [])

    def _create_interval_lines(self):
        a = float(self.t_start_spin.value())
        b = float(self.t_stop_spin.value())
        for i, plot in enumerate(self.plot_widgets):
            start = pg.InfiniteLine(a, angle=90, movable=(i == 0), pen=pg.mkPen("k", width=1.5))
            stop = pg.InfiniteLine(b, angle=90, movable=(i == 0), pen=pg.mkPen("k", width=1.5))
            plot.addItem(start)
            plot.addItem(stop)
            self.start_lines.append(start)
            self.stop_lines.append(stop)
        if self.start_lines:
            self.start_lines[0].sigPositionChanged.connect(self.update_spins_from_lines)
            self.stop_lines[0].sigPositionChanged.connect(self.update_spins_from_lines)


    def _channel_color(self, name: str, fallback_index: int) -> str:
        """Measured-data preview uses uniform styling for all displayed channels."""
        return "k"

    def _sample_symbol_size(self, width: float) -> float:
        return max(4.0, float(width) + 2.0)

    def _sample_symbol_pen_width(self, width: float) -> float:
        return max(0.35, 0.3 * float(width))

    def update_channel_colors(self, *_args):
        width = float(self._global_line_width)
        symbol_size = self._sample_symbol_size(width)
        symbol_pen_width = self._sample_symbol_pen_width(width)
        for _row, (_name, curve) in enumerate(self.curves.items()):
            curve.setPen(pg.mkPen("g", width=width))
        for samples in self.sample_curves.values():
            samples.setSymbolSize(symbol_size)
            samples.setSymbolPen(pg.mkPen("b", width=symbol_pen_width))
            samples.setSymbolBrush(pg.mkBrush("b"))

    def _on_line_width_changed(self, value):
        self.set_global_line_width(value)

    def set_global_line_width(self, width):
        self._global_line_width = float(width)
        self.update_channel_colors()

    def update_spins_from_lines(self):
        if self._syncing_interval or not self.start_lines:
            return
        self._syncing_interval = True
        a = float(self.start_lines[0].value())
        b = float(self.stop_lines[0].value())
        if a > b:
            a, b = b, a
        self.t_start_spin.setValue(a)
        self.t_stop_spin.setValue(b)
        for line in self.start_lines[1:]:
            line.setValue(a)
        for line in self.stop_lines[1:]:
            line.setValue(b)
        self._syncing_interval = False
        self._update_sampling_info()

    def update_lines_from_spins(self):
        if self._syncing_interval:
            return
        self._syncing_interval = True
        a = min(self.t_start_spin.value(), self.t_stop_spin.value())
        b = max(self.t_start_spin.value(), self.t_stop_spin.value())
        for line in self.start_lines:
            line.setValue(a)
        for line in self.stop_lines:
            line.setValue(b)
        self._syncing_interval = False
        self._update_sampling_info()

    def _update_sampling_info(self):
        if self.t is None:
            return
        a = min(self.t_start_spin.value(), self.t_stop_spin.value())
        b = max(self.t_start_spin.value(), self.t_stop_spin.value())
        n = max(0, int(np.searchsorted(self.t, b, side="right") - np.searchsorted(self.t, a, side="left")))
        fs = 1.0 / self.dt_original if self.dt_original > 0 else np.nan
        dt_target = float(self.dt_spin.value())
        duration = max(0.0, b - a)
        n_out = int(np.floor(duration / dt_target)) + 1 if dt_target > 0.0 else 0
        self.sampling_label.setText(
            f"dt original: {self.dt_original:.9g} s\n"
            f"fs original: {fs:.9g} Hz\n"
            f"selected raw samples: {n}\n"
            f"expected uniform samples: {n_out}"
        )

    def _portable_source_file(self) -> str:
        if self.file_path is None:
            return ""
        source = Path(self.file_path).expanduser().resolve()
        try:
            return str(source.relative_to(self.base_dir.resolve()))
        except ValueError:
            return str(source)

    def export_dataset(self):
        if self.t is None:
            QMessageBox.warning(self, "No data", "Load a measurement first."); return
        a = min(self.t_start_spin.value(), self.t_stop_spin.value())
        b = max(self.t_start_spin.value(), self.t_stop_spin.value())
        mask = (self.t >= a) & (self.t <= b)
        t = self.t[mask]
        u_name = self.u_combo.currentText(); y_name = self.y_combo.currentText()
        if not u_name or not y_name or u_name == y_name:
            QMessageBox.warning(self, "Invalid channels", "Select different channels for u and y."); return
        u = self.signals[u_name][mask]; y = self.signals[y_name][mask]
        if len(t) < 3:
            QMessageBox.warning(self, "Selection too short", "Select at least three samples."); return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.btn_export.setEnabled(False)
        try:
            meta = import_selected_arrays(t, u, y, self.file_path, self.base_dir, float(self.dt_spin.value()), metadata={
                "source_format": self.source_kind,
                "channel_t": self.t_combo.currentText() if self.t_combo.isEnabled() else "MAT time axis",
                "channel_u": u_name, "channel_y": y_name,
                "selection_t_start": float(a), "selection_t_stop": float(b),
            })
        except Exception as exc:
            QMessageBox.critical(self, "Dataset preparation failed", str(exc)); return
        finally:
            self.btn_export.setEnabled(True)
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Dataset ready", f"Shared measured dataset activated.\n\nsamples = {meta['samples']}\ndt = {meta['dt']:g} s")
        self.datasetExported.emit(self.base_dir / "data_uy.txt")

    def _activate_dataset(self, out_path: Path, role: str):
        import project_state as ps
        ps.set_dataset_file(role, out_path, activate=True)

