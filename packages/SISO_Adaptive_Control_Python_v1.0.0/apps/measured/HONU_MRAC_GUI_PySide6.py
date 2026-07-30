# -*- coding: utf-8 -*-
"""
PySide6 + pyqtgraph GUI for measured-data HONU MRAC/MPC.

Run:
    python HONU_MRAC_GUI_PySide6.py

Required packages:
    pip install PySide6 pyqtgraph numpy

Design rules:
    - project_setup.py remains the authoritative setup file.
    - The GUI preserves the Simulated layout; measured data replace trained HONU generation.
    - Computational scripts are executed as external processes.
    - Matplotlib windows are suppressed in GUI mode.
    - All displayed figures are rendered by pyqtgraph.
    - Plot layout and labels follow the original script figures.
"""

# =============================================================================
# Imports and setup
# =============================================================================

import ast
import json
import os
import re
import sys
import time
import subprocess
from pathlib import Path

import numpy as np

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QPalette, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QFileDialog,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg

from measured_import import import_measured_file
from measured_data_page import MeasuredDataPage

from simulated_normalization import (
    load_stats, load_artifact_stats, assert_same_stats,
    denormalize_u, denormalize_y, denormalize_error,
)


class CompactYAxis(pg.AxisItem):
    """Y axis with literal lower/zero/upper labels and no SI prefix in title."""

    def __init__(self, orientation="left", *args, **kwargs):
        super().__init__(orientation=orientation, *args, **kwargs)
        self.enableAutoSIPrefix(False)
        self.setStyle(
            autoExpandTextSpace=True,
            tickTextWidth=76,
            tickTextHeight=16,
            showValues=True,
            maxTextLevel=0,
            hideOverlappingLabels=False,
            # Never suppress the numeric tick-label level merely because a
            # plot row is short.  This is essential in the embedded main GUI,
            # where several vertically stacked plots share the available
            # height.
            textFillLimits=[(0, 10.0)],
        )
        self.setWidth(82)
        self._display_tick_values = {}

    @staticmethod
    def _format_value(value):
        value = float(value)
        if not np.isfinite(value):
            return ""
        if np.isclose(value, 0.0, atol=1e-15, rtol=0.0):
            return "0"
        magnitude = abs(value)
        if magnitude < 1e-3 or magnitude >= 1e4:
            text = f"{value:.3e}"
            mantissa, exponent = text.split("e")
            mantissa = mantissa.rstrip("0").rstrip(".")
            exponent = str(int(exponent))
            return f"{mantissa}e{exponent}"
        return f"{value:.4g}"

    def tickValues(self, minVal, maxVal, size):
        lo = float(min(minVal, maxVal))
        hi = float(max(minVal, maxVal))
        if not np.isfinite(lo) or not np.isfinite(hi):
            self._display_tick_values = {}
            return []
        span = hi - lo
        if span <= np.finfo(float).eps * max(1.0, abs(lo), abs(hi)):
            self._display_tick_values = {lo: lo}
            return [(1.0, [lo])]

        # Tick marks are moved inside the view so Qt does not clip their text.
        # Labels still show the true visible lower and upper limits.
        # Reserve a fixed number of screen pixels above and below the endpoint
        # labels. A percentage-only inset fails when many plots make each row
        # short: the endpoint text then extends outside AxisItem.boundingRect()
        # and pyqtgraph silently drops it. Convert the required pixel margin to
        # data coordinates so ymin/ymax remain visible at every plot height.
        axis_pixels = max(float(size), 1.0)
        label_margin_pixels = 11.0
        inset_fraction = max(0.065, label_margin_pixels / axis_pixels)
        inset_fraction = min(inset_fraction, 0.28)
        inset = inset_fraction * span
        lo_pos = lo + inset
        hi_pos = hi - inset
        values = [lo_pos]
        mapping = {lo_pos: lo, hi_pos: hi}

        # Add the zero tick only when its label has enough screen-space from
        # both endpoint labels.  For strongly asymmetric ranges (for example
        # y in [-4.45, 0.34]) zero lies only a few pixels below the upper
        # endpoint.  Drawing both labels then looks like two y axes overlaid.
        # The axis size is available here, so decide in pixels rather than by
        # a fragile data-range percentage.
        if lo < 0.0 < hi:
            zero_pixel = axis_pixels * (0.0 - lo) / span
            lo_pixel = axis_pixels * (lo_pos - lo) / span
            hi_pixel = axis_pixels * (hi_pos - lo) / span
            min_label_separation_pixels = 22.0
            if (zero_pixel - lo_pixel >= min_label_separation_pixels and
                    hi_pixel - zero_pixel >= min_label_separation_pixels):
                values.append(0.0)
                mapping[0.0] = 0.0

        values.append(hi_pos)
        self._display_tick_values = mapping
        return [(span, values)]

    def tickStrings(self, values, scale, spacing):
        # AxisItem may pass values back with tiny floating-point changes and,
        # depending on the pyqtgraph version, with ``scale`` already applied.
        # Exact dictionary lookup therefore made only the zero label survive.
        # Match each returned tick to the nearest stored display position.
        labels = []
        positions = np.asarray(list(self._display_tick_values.keys()), dtype=float)
        span = float(np.ptp(positions)) if positions.size > 1 else 0.0
        tolerance = max(1e-12, 1e-8 * max(1.0, span))

        for raw_position in values:
            position = float(raw_position)
            candidates = [position]
            if np.isfinite(scale) and scale not in (0.0, 1.0):
                candidates.extend((position * float(scale), position / float(scale)))

            shown = None
            if positions.size:
                best_distance = np.inf
                best_key = None
                for candidate in candidates:
                    distances = np.abs(positions - candidate)
                    index = int(np.argmin(distances))
                    distance = float(distances[index])
                    if distance < best_distance:
                        best_distance = distance
                        best_key = float(positions[index])
                if best_key is not None and best_distance <= tolerance:
                    shown = self._display_tick_values[best_key]

            if shown is None:
                shown = position * float(scale) if np.isfinite(scale) else position
            labels.append(self._format_value(shown))
        return labels


def plant_display_name(_name=None):
    return "Measured dataset"

def plant_signal_metadata(_name=None):
    return {}

def plant_signal_symbol(_name, key):
    return str(key)

# =============================================================================
# User-visible configuration
# =============================================================================

APP_TITLE = "HONU MRAC Laboratory"
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
PROJECT_SETUP_FILE = BASE_DIR / "project_setup.py"
PYTHON_EXE = sys.executable

DATA_SOURCES = {
    "Automatic from selected file": "auto",
}

PLANT_APPROXIMATION_MODELS = ["LNU", "QNU"]
CONTROLLER_MODELS = ["LNU", "QNU"]
PLANT_LEARNING_ALGORITHMS = ["batch", "LM", "GD", "NGD"]
CONTROLLER_LEARNING_ALGORITHMS = ["GD", "NGD"]
REFERENCE_TYPES = {
    "Alternating steps": "alternating_steps",
    "Random steps": "random_steps",
    "Plant excitation (legacy)": "plant_input",
}

SCRIPT_MODULES = {
    "01 Load measured data": "measured_import.py",
    "02 Identify plant LNU batch": "02_identify_plant_LNU_batch.py",
    "02 Identify plant LNU GD/NGD": "02_identify_plant_LNU_gd_ngd.py",
    "02 Identify plant LNU LM": "02_identify_plant_LNU_lm.py",
    "02 Identify plant QNU batch": "02_identify_plant_QNU_batch.py",
    "02 Identify plant QNU GD/NGD": "02_identify_plant_QNU_gd_ngd.py",
    "02 Identify plant QNU LM": "02_identify_plant_QNU_lm.py",
    "03 Train LNU plant + LNU controller": "03_train_controller_plant_LNU_controller_LNU.py",
    "03 Train LNU plant + QNU controller": "03_train_controller_plant_LNU_controller_QNU.py",
    "03 Train QNU plant + LNU controller": "03_train_controller_plant_QNU_controller_LNU.py",
    "03 Train QNU plant + QNU controller": "03_train_controller_plant_QNU_controller_QNU.py",
    "04 Test LNU-LNU controller on HONU plant": "",
    "04 Test LNU-QNU controller on HONU plant": "",
    "04 Test QNU-LNU controller on HONU plant": "",
    "04 Test QNU-QNU controller on HONU plant": "",
}

IDENTIFICATION_SCRIPT_BY_METADATA = {
    ("LNU", "batch"): "02_identify_plant_LNU_batch.py",
    ("LNU", "GD"): "02_identify_plant_LNU_gd_ngd.py",
    ("LNU", "NGD"): "02_identify_plant_LNU_gd_ngd.py",
    ("LNU", "LM"): "02_identify_plant_LNU_lm.py",
    ("QNU", "batch"): "02_identify_plant_QNU_batch.py",
    ("QNU", "GD"): "02_identify_plant_QNU_gd_ngd.py",
    ("QNU", "NGD"): "02_identify_plant_QNU_gd_ngd.py",
    ("QNU", "LM"): "02_identify_plant_QNU_lm.py",
}

CONTROL_SCRIPT_BY_METADATA = {
    ("LNU", "LNU"): "03_train_controller_plant_LNU_controller_LNU.py",
    ("LNU", "QNU"): "03_train_controller_plant_LNU_controller_QNU.py",
    ("QNU", "LNU"): "03_train_controller_plant_QNU_controller_LNU.py",
    ("QNU", "QNU"): "03_train_controller_plant_QNU_controller_QNU.py",
}

EVALUATION_SCRIPT_BY_METADATA = {
    ("LNU", "LNU"): "",
    ("LNU", "QNU"): "",
    ("QNU", "LNU"): "",
    ("QNU", "QNU"): "",
}

OUTPUT_FILES = {
    "01 physical plant data: model-specific signals": "data_uy.txt",
    "02 plant LNU batch BIBS": "bibs_plant_LNU_batch.txt",
    "02 plant LNU GD/NGD BIBS": "bibs_plant_LNU_gd_ngd.txt",
    "02 plant LNU LM BIBS": "bibs_plant_LNU_lm.txt",
    "02 plant QNU batch BIBS": "bibs_plant_QNU_batch.txt",
    "02 plant QNU GD/NGD BIBS": "bibs_plant_QNU_gd_ngd.txt",
    "02 plant QNU LM BIBS": "bibs_plant_QNU_lm.txt",
    "03 training trace LNU-LNU": "training_controller_LNU_LNU_gd_ngd.txt",
    "03 training trace LNU-QNU": "training_controller_LNU_QNU_gd_ngd.txt",
    "03 training trace QNU-LNU": "training_controller_QNU_LNU_gd_ngd.txt",
    "03 training trace QNU-QNU": "training_controller_QNU_QNU_gd_ngd.txt",
    "03 training BIBS LNU-LNU": "bibs_controller_LNU_LNU_gd_ngd.txt",
    "03 training BIBS LNU-QNU": "bibs_controller_LNU_QNU_gd_ngd.txt",
    "03 training BIBS QNU-LNU": "bibs_controller_QNU_LNU_gd_ngd.txt",
    "03 training BIBS QNU-QNU": "bibs_controller_QNU_QNU_gd_ngd.txt",
    "04 trained HONU test LNU-LNU": "eval_LNU_LNU_physical.txt",
    "04 trained HONU test LNU-QNU": "eval_LNU_QNU_physical.txt",
    "04 trained HONU test QNU-LNU": "eval_QNU_LNU_physical.txt",
    "04 trained HONU test QNU-QNU": "eval_QNU_QNU_physical.txt",
}

GRID_ALPHA = 0.28

OUTPUT_BY_STEP = {
    "01": "data_uy.txt",
}




class HoverArrowDoubleSpinBox(QDoubleSpinBox):
    """Compact numeric field whose step arrows appear on hover/focus."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QDoubleSpinBox.NoButtons)

    def _update_buttons(self):
        visible = self.underMouse() or self.hasFocus()
        self.setButtonSymbols(
            QDoubleSpinBox.UpDownArrows if visible else QDoubleSpinBox.NoButtons
        )

    def enterEvent(self, event):
        self.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.hasFocus():
            self.setButtonSymbols(QDoubleSpinBox.NoButtons)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setButtonSymbols(
            QDoubleSpinBox.UpDownArrows if self.underMouse() else QDoubleSpinBox.NoButtons
        )
        super().focusOutEvent(event)


class SelectAllDoubleSpinBox(QDoubleSpinBox):
    """Numeric editor with compact defaults and unrestricted manual precision.

    Programmatically loaded/default values are displayed with four decimal
    places.  If the user types more decimal places, that precision is retained
    and remains visible.  The internal QDoubleSpinBox precision is therefore
    not limited to four decimals.
    """

    DEFAULT_DISPLAY_DECIMALS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_decimals = 0

    @staticmethod
    def _typed_decimal_count(text):
        text = str(text).strip().lower()
        mantissa = text.split("e", 1)[0]
        if "." not in mantissa:
            return 0
        return len(mantissa.rsplit(".", 1)[1])

    def valueFromText(self, text):
        self._user_decimals = min(
            self.decimals(),
            max(self._user_decimals, self._typed_decimal_count(text)),
        )
        return super().valueFromText(text)

    def textFromValue(self, value):
        shown_decimals = min(
            self.decimals(),
            max(self.DEFAULT_DISPLAY_DECIMALS, self._user_decimals),
        )
        return f"{value:.{shown_decimals}f}"

    def setValue(self, value):
        # Values loaded by the application use the compact four-decimal view.
        self._user_decimals = 0
        super().setValue(value)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event):
        first_focus = not self.hasFocus()
        super().mousePressEvent(event)
        if first_focus:
            QTimer.singleShot(0, self.selectAll)


class ZoomResetViewBox(pg.ViewBox):
    """ViewBox with left-drag rectangular zoom and double-click reset.

    pyqtgraph normally pans with the left mouse button.  For this GUI the
    desired behaviour is closer to the old scientific viewers: left drag draws
    a zoom rectangle; double click restores the full range of the currently
    visible graph tab.
    """

    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.setMouseMode(pg.ViewBox.RectMode)

    def mouseDoubleClickEvent(self, ev):
        if self.owner is not None:
            self.owner.reset_current_graph_ranges()
            ev.accept()
            return
        super().mouseDoubleClickEvent(ev)

def plant_bibs_file(honu_plant, learning_algorithm):
    suffix = "batch" if learning_algorithm == "batch" else ("lm" if learning_algorithm == "LM" else "gd_ngd")
    return f"bibs_plant_{honu_plant}_{suffix}.txt"

def controller_bibs_file(honu_plant, controller):
    return f"bibs_controller_{honu_plant}_{controller}_gd_ngd.txt"

def controller_training_trace_file(honu_plant, controller):
    return f"training_controller_{honu_plant}_{controller}_gd_ngd.txt"

def eval_file(honu_plant, controller):
    return f"eval_{honu_plant}_{controller}_physical.txt"

def output_label_for_file(file_name):
    for label, name in OUTPUT_FILES.items():
        if name == file_name:
            return label
    return file_name

# =============================================================================
# Utility functions
# =============================================================================


def read_header_columns(path: Path):
    """Return column names from the first useful comment line."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s.startswith("#"):
                    break
                s = s[1:].strip()
                if "=" in s and "," in s:
                    continue
                parts = s.replace("\t", " ").split()
                if len(parts) >= 2:
                    return parts
    except OSError:
        pass
    return []


def load_table(path: Path):
    if not path.exists():
        raise FileNotFoundError(str(path))
    columns = read_header_columns(path)
    data = np.loadtxt(path, comments="#")
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if not columns or len(columns) != data.shape[1]:
        columns = ["t"] + [f"x{i}" for i in range(1, data.shape[1])]
    return columns, data


def column_index(columns, name):
    try:
        return columns.index(name)
    except ValueError:
        return None


def finite_xy(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def read_setup_text():
    if PROJECT_SETUP_FILE.exists():
        text = PROJECT_SETUP_FILE.read_text(encoding="utf-8", errors="ignore")
        # Repair a setup file that may have been corrupted by older GUI builds,
        # where replacement strings wrote escaped quotes into Python code, e.g.
        #     plant_model_name = \"two_mass...\"
        # Such a file raises SyntaxError before any module can generate data_uy.txt.
        return text.replace('\\"', '"').replace("\\'", "'")
    return ""


def read_setup_value(name, default=None):
    """Read a literal assignment from project_setup.py.

    Only simple Python literals are accepted. Expressions and aliases intentionally
    fall back to *default*, which keeps this helper safe and predictable.
    """
    text = read_setup_text()
    pattern = rf"^\s*{re.escape(name)}\s*=\s*(.+?)(?:\s+#.*)?$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return default
    try:
        return ast.literal_eval(match.group(1).strip())
    except (SyntaxError, ValueError):
        return default


def read_setup_string(name, default=""):
    value = read_setup_value(name, default)
    return str(value) if value is not None else default


def read_setup_int(name, default=0):
    value = read_setup_value(name, default)
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return int(default)


def read_setup_float(name, default=0.0):
    value = read_setup_value(name, default)
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def setup_literal(value):
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("Setup values must be finite numbers.")
        result = format(value, ".15g")
        if "e" not in result.lower() and "." not in result:
            result += ".0"
        return result
    return repr(value)


def replace_setup_value(text, name, value):
    pattern = rf"^(\s*{re.escape(name)}\s*=\s*)[^#\r\n]*(\s*(?:#.*)?)$"
    literal = setup_literal(value)

    def repl(match):
        return f"{match.group(1)}{literal}{match.group(2)}"

    new_text, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
    if count == 0:
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        new_text += f"{name} = {literal}\n"
    return new_text


def write_setup_values(values):
    text = read_setup_text()
    if not text:
        raise FileNotFoundError(str(PROJECT_SETUP_FILE))
    for name, value in values.items():
        text = replace_setup_value(text, name, value)
    temp_path = PROJECT_SETUP_FILE.with_suffix(".py.tmp")
    temp_path.write_text(text, encoding="utf-8")
    os.replace(temp_path, PROJECT_SETUP_FILE)


def open_file_with_system(path: Path):
    path = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def line_width_from_setup(default=2):
    text = read_setup_text()
    m = re.search(r"^\s*line_width\s*=\s*([0-9.]+)", text, flags=re.MULTILINE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return default


def font_size_from_setup(default=10):
    text = read_setup_text()
    m = re.search(r"^\s*font_size\s*=\s*([0-9.]+)", text, flags=re.MULTILINE)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            pass
    return default

# =============================================================================
# Independent comparison windows
# =============================================================================

# Application-level registry. Comparison windows are intentionally not owned by
# MainWindow, so reloading plots or starting another simulation cannot destroy
# them. Each window owns a deep copy of the plotted data.
COMPARISON_PLOT_WINDOWS = []


# =============================================================================
# Main window
# =============================================================================


class FullScreenPlotWindow(QMainWindow):
    """Interactive full-screen host for the active graph tab.

    Full-screen selection operates on complete plot axes, not on individual
    curves. Hidden axes are removed from the GraphicsLayout and the remaining
    axes are reflowed to use the available height. Weight plots are controlled
    as complete ``w`` or ``v`` groups.
    """

    _WEIGHT_RE = re.compile(r"([wv])(?:_?\d+|\[\d+\]|\(\d+\))", flags=re.IGNORECASE)

    def __init__(self, plot_widget, plots, initial_ranges, title, restore_callback, metadata_text="", footer_text="", parent=None, line_width_value=None):
        super().__init__(None)
        self.setWindowFlag(Qt.Window, True)
        self.setMinimumSize(640, 420)
        self._plot_widget = plot_widget
        self._plots = list(plots or [])
        self._initial_ranges = list(initial_ranges or [])
        self._restore_callback = restore_callback
        self._axis_checkboxes = []
        self._weight_plot_groups = {"w": [], "v": []}
        self._weight_selector = None
        self._original_plot_visibility = {plot: plot.isVisible() for plot in self._plots}
        self._line_width_reference = float(line_width_value) if line_width_value is not None else None
        self._line_style_records = []
        # Preserve the x-axis grouping that existed in the source graph.  A
        # shared x label is rendered only on the lowest currently visible axis
        # in its group, including after axes are hidden or shown in this window.
        self._x_axis_groups = self._collect_x_axis_groups()
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        root = QWidget(self)
        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.setSpacing(6)

        if metadata_text:
            metadata_label = QLabel(metadata_text, root)
            # Run metadata belongs in the top information panel and must stay
            # on one line. The plots themselves keep only their short graph title.
            metadata_label.setWordWrap(False)
            metadata_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            metadata_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            metadata_label.setStyleSheet(
                "font-size: 80%; font-weight: 600; padding: 3px 6px;"
            )
            metadata_label.setToolTip(metadata_text)
            outer_layout.addWidget(metadata_label, 0)

        content = QWidget(root)
        root_layout = QHBoxLayout(content)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        controls = QFrame(root)
        controls.setMinimumWidth(190)
        controls.setMaximumWidth(280)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(6)

        heading = QLabel("Displayed axes", controls)
        heading.setStyleSheet("font-weight: 600;")
        controls_layout.addWidget(heading)

        btn_reset = QPushButton("Reset zoom", controls)
        btn_reset.clicked.connect(self.reset_current_graph_ranges)
        controls_layout.addWidget(btn_reset)

        if self._line_width_reference is not None:
            line_width_row = QHBoxLayout()
            line_width_label = QLabel("line width [px]", controls)
            self._line_width_spin = QDoubleSpinBox(controls)
            self._line_width_spin.setRange(0.5, 10.0)
            self._line_width_spin.setDecimals(2)
            self._line_width_spin.setSingleStep(0.25)
            self._line_width_spin.setFixedWidth(72)
            self._line_width_spin.setValue(self._line_width_reference)
            self._line_width_spin.setKeyboardTracking(False)
            line_width_row.addWidget(line_width_label)
            line_width_row.addWidget(self._line_width_spin)
            line_width_row.addStretch(1)
            controls_layout.addLayout(line_width_row)
            self._capture_line_styles()
            self._line_width_spin.valueChanged.connect(self._apply_fullscreen_line_width)

        scroll = QScrollArea(controls)
        scroll.setWidgetResizable(True)
        scroll_body = QWidget(scroll)
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(4)

        used_labels = {}
        for axis_index, plot in enumerate(self._plots):
            try:
                items = list(plot.listDataItems())
            except Exception:
                items = []
            names = [str(item.name() or "").strip() for item in items]
            weight_groups = {
                match.group(1).lower()
                for name in names
                for match in [self._WEIGHT_RE.fullmatch(re.sub(r"\s+", "", name))]
                if match is not None
            }
            named_count = sum(bool(name) for name in names)
            if named_count > 0 and len(weight_groups) == 1 and len(weight_groups) == named_count:
                group = next(iter(weight_groups))
                self._weight_plot_groups[group].append(plot)
                continue

            label = self._plot_axis_label(plot, axis_index)
            count = used_labels.get(label, 0) + 1
            used_labels[label] = count
            if count > 1:
                label = f"{label} ({count})"
            checkbox = QCheckBox(label, scroll_body)
            checkbox.setChecked(plot.isVisible())
            checkbox.toggled.connect(lambda checked, p=plot: self._set_plot_visible(p, checked))
            scroll_layout.addWidget(checkbox)
            self._axis_checkboxes.append((checkbox, plot))

        available_weight_groups = [key for key in ("w", "v") if self._weight_plot_groups[key]]
        if available_weight_groups:
            weight_label = QLabel("Weight axes", scroll_body)
            weight_label.setStyleSheet("font-weight: 600; margin-top: 6px;")
            scroll_layout.addWidget(weight_label)
            self._weight_selector = QComboBox(scroll_body)
            self._weight_selector.addItem("none", "none")
            for key in available_weight_groups:
                self._weight_selector.addItem(key, key)
            initially_visible = "none"
            for key in available_weight_groups:
                if any(plot.isVisible() for plot in self._weight_plot_groups[key]):
                    initially_visible = key
                    break
            index = self._weight_selector.findData(initially_visible)
            self._weight_selector.setCurrentIndex(max(0, index))
            self._weight_selector.currentIndexChanged.connect(self._apply_weight_selection)
            scroll_layout.addWidget(self._weight_selector)

        if not self._axis_checkboxes and not available_weight_groups:
            empty = QLabel("No selectable axes", scroll_body)
            empty.setWordWrap(True)
            scroll_layout.addWidget(empty)
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_body)
        controls_layout.addWidget(scroll, 1)

        window_row = QHBoxLayout()
        btn_restore = QPushButton("Restore", controls)
        btn_maximize = QPushButton("Maximize", controls)
        btn_close = QPushButton("Close", controls)
        btn_restore.clicked.connect(self.showNormal)
        btn_maximize.clicked.connect(self.showMaximized)
        btn_close.clicked.connect(self.close)
        window_row.addWidget(btn_restore)
        window_row.addWidget(btn_maximize)
        window_row.addWidget(btn_close)
        controls_layout.addLayout(window_row)

        hint = QLabel(
            "Independent comparison window\n"
            "Drag the title bar to move; resize by the frame.\n"
            "Left drag: zoom rectangle; double click: reset.",
            controls,
        )
        hint.setWordWrap(True)
        controls_layout.addWidget(hint)

        plot_widget.setParent(root)
        plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_widget.show()
        root_layout.addWidget(controls, 0)
        root_layout.addWidget(plot_widget, 1)
        outer_layout.addWidget(content, 1)

        if footer_text:
            footer_label = QLabel(footer_text, root)
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            footer_label.setStyleSheet("font-weight: 600; padding: 4px 6px;")
            outer_layout.addWidget(footer_label, 0)

        self.setCentralWidget(root)

        for plot in self._plots:
            try:
                view_box = plot.getViewBox()
                view_box.owner = self
                view_box.setMouseMode(pg.ViewBox.RectMode)
                plot.setMouseEnabled(x=True, y=True)
            except Exception:
                pass
        self._apply_weight_selection()
        self._reflow_plots()

    def _capture_line_styles(self):
        """Store full-screen curve and marker dimensions for proportional live scaling."""
        self._line_style_records = []
        reference = max(float(self._line_width_reference or 1.0), 1.0e-12)
        for plot in self._plots:
            for item in plot.listDataItems():
                opts = item.opts
                pen = opts.get("pen")
                pen_width = float(pen.widthF()) if pen is not None else 0.0
                symbol_pen = opts.get("symbolPen")
                symbol_pen_width = float(symbol_pen.widthF()) if symbol_pen is not None else 0.0
                symbol_size = float(opts.get("symbolSize") or 0.0)
                self._line_style_records.append({
                    "item": item,
                    "pen_ratio": pen_width / reference if pen_width > 0.0 else 0.0,
                    "symbol_pen_ratio": symbol_pen_width / reference if symbol_pen_width > 0.0 else 0.0,
                    "symbol_size_ratio": symbol_size / reference if symbol_size > 0.0 else 0.0,
                })

    def _apply_fullscreen_line_width(self, value):
        """Update full-screen curve/marker sizes without touching any view range."""
        width = float(value)
        for record in self._line_style_records:
            item = record["item"]
            opts = item.opts
            if record["pen_ratio"] > 0.0 and opts.get("pen") is not None:
                pen = pg.mkPen(opts.get("pen"))
                pen.setWidthF(max(0.1, width * record["pen_ratio"]))
                item.setPen(pen)
            if record["symbol_pen_ratio"] > 0.0 and opts.get("symbolPen") is not None:
                symbol_pen = pg.mkPen(opts.get("symbolPen"))
                symbol_pen.setWidthF(max(0.1, width * record["symbol_pen_ratio"]))
                item.setSymbolPen(symbol_pen)
            if record["symbol_size_ratio"] > 0.0:
                item.setSymbolSize(max(1.0, width * record["symbol_size_ratio"]))
        try:
            self._plot_widget.scene().update()
        except Exception:
            pass

    @staticmethod
    def _plot_axis_label(plot, axis_index):
        try:
            text = str(plot.getAxis("left").labelText or "").strip()
            if text:
                return text
        except Exception:
            pass
        try:
            names = [str(item.name() or "").strip() for item in plot.listDataItems()]
            names = [name for name in names if name]
            if names:
                return ", ".join(names)
        except Exception:
            pass
        return f"axis {axis_index + 1}"

    @staticmethod
    def _bottom_axis_label(plot):
        try:
            return str(plot.getAxis("bottom").labelText or "").strip()
        except Exception:
            return ""

    def _collect_x_axis_groups(self):
        """Infer contiguous groups that share one x-axis annotation.

        In the source layouts, an x label marks the lowest axis of a linked
        group.  Most tabs contain one group; a few diagnostic tabs contain a
        time group followed by an independent epoch/sample group.  Keeping
        these groups separate prevents a time label from being copied onto an
        epoch axis while still guaranteeing one label per shared x domain.
        """
        if not self._plots:
            return []
        labels = [self._bottom_axis_label(plot) for plot in self._plots]
        labelled = [(index, label) for index, label in enumerate(labels) if label]
        if not labelled:
            return []

        # Older full-screen snapshots could contain the same label on every
        # axis.  Treat that as one shared group and collapse it immediately.
        normalized = {re.sub(r"\s+", " ", label).strip().lower() for _i, label in labelled}
        if len(normalized) == 1:
            return [{"plots": list(self._plots), "label": labelled[-1][1]}]

        groups = []
        start = 0
        for index, label in labelled:
            group_plots = list(self._plots[start:index + 1])
            if group_plots:
                groups.append({"plots": group_plots, "label": label})
            start = index + 1
        if start < len(self._plots):
            # Unlabelled trailing axes belong to the last known x domain.
            groups[-1]["plots"].extend(self._plots[start:])
        return groups

    def _update_bottom_axis_labels(self):
        """Place each shared x label on its lowest visible axis only."""
        for group in self._x_axis_groups:
            group_plots = list(group.get("plots", []))
            label = str(group.get("label", ""))
            visible_plots = [plot for plot in group_plots if plot.isVisible()]
            target = visible_plots[-1] if visible_plots else None
            for plot in group_plots:
                try:
                    plot.getAxis("bottom").setLabel(text=label if plot is target else "")
                except Exception:
                    pass

    def _set_plot_visible(self, plot, visible):
        plot.setVisible(bool(visible))
        self._reflow_plots()

    def _set_all_axes_visible(self, visible):
        """Show or hide complete non-weight axes."""
        for checkbox, _plot in self._axis_checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(visible))
            checkbox.blockSignals(False)
        for _checkbox, plot in self._axis_checkboxes:
            plot.setVisible(bool(visible))
        self._reflow_plots()

    def _apply_weight_selection(self, *_args):
        """Show complete w axes, complete v axes, or no weight axes."""
        selected = "none"
        if self._weight_selector is not None:
            selected = str(self._weight_selector.currentData() or "none").lower()
        for group_name, plots in self._weight_plot_groups.items():
            visible = selected == group_name
            for plot in plots:
                plot.setVisible(visible)
        self._reflow_plots()

    def _reflow_plots(self):
        """Remove hidden axes from the layout and compact visible axes."""
        layout = getattr(self._plot_widget, "ci", None)
        if layout is None:
            return
        for plot in self._plots:
            try:
                layout.removeItem(plot)
            except Exception:
                pass
        # Row 0 is reserved for the common graph title. Reflow only the
        # selectable plot axes below it, both in the main and full-screen view.
        try:
            layout.setRowFixedHeight(0, 36)
            layout.setRowSpacing(0, 4)
        except Exception:
            pass
        row = 1
        for plot in self._plots:
            if not plot.isVisible():
                continue
            try:
                layout.addItem(plot, row=row, col=0)
                plot.show()
                row += 1
            except Exception:
                pass
        self._update_bottom_axis_labels()
        try:
            self._plot_widget.updateGeometry()
            self._plot_widget.update()
            self._plot_widget.scene().update()
        except Exception:
            pass

    def reset_current_graph_ranges(self):
        if len(self._initial_ranges) != len(self._plots):
            for plot in self._plots:
                if not plot.isVisible():
                    continue
                try:
                    plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
                    plot.autoRange()
                    plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
                except Exception:
                    pass
            return
        for plot, ranges in zip(self._plots, self._initial_ranges):
            if ranges is None or not plot.isVisible():
                continue
            try:
                plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
                plot.setRange(xRange=ranges[0], yRange=ranges[1], padding=0.02)
                plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        self._plot_widget.show()
        self._plot_widget.updateGeometry()
        self._plot_widget.update()
        try:
            self._plot_widget.scene().update()
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Restore the original axis visibility and ordering before returning the
        # GraphicsLayoutWidget to the main tab.
        for plot in self._plots:
            plot.setVisible(self._original_plot_visibility.get(plot, True))
            try:
                plot.getViewBox().owner = None
            except Exception:
                pass
        self._reflow_plots()
        if self._plot_widget is not None:
            self._plot_widget.setParent(None)
            if self._restore_callback is not None:
                self._restore_callback(self._plot_widget)
        self._restore_callback = None
        self._plot_widget = None
        super().closeEvent(event)


class HONUMPCPage(QWidget):
    """Model-independent sliding-window HONU MPC page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.stop_requested = False
        self.config_file = BASE_DIR / "honu_mpc_gui_config.json"
        self.simulation_output_file = BASE_DIR / "honu_mpc_ode_simulation_result.npz"
        self.identification_output_file = BASE_DIR / "honu_mpc_identified_plant.npz"
        self.mpc_frozen_output_file = BASE_DIR / "honu_mpc_frozen_result.npz"
        self.mpc_sliding_output_file = BASE_DIR / "honu_mpc_sliding_result.npz"
        self.mpc_output_file = self.mpc_sliding_output_file
        self.output_file = self.mpc_sliding_output_file
        self.current_result_mode = "mpc_sliding"
        self._loaded_result_metadata = {}
        self.tab_plots = {}
        self.tab_titles = {}
        self._initial_plot_ranges = {}
        self._build_ui()

    @staticmethod
    def _dspin(lo, hi, value, step=0.1, decimals=6, width=78):
        w = SelectAllDoubleSpinBox(); w.setRange(lo, hi); w.setDecimals(decimals)
        w.setSingleStep(step); w.setValue(value); w.setKeyboardTracking(False)
        w.setFixedWidth(width)
        return w

    @staticmethod
    def _ispin(lo, hi, value, width=78):
        w = QSpinBox(); w.setRange(lo, hi); w.setValue(value); w.setFixedWidth(width); return w

    @staticmethod
    def _npz_scalar(data, key, default=None):
        if key not in data:
            return default
        try:
            values = np.asarray(data[key]).reshape(-1)
            if values.size == 0:
                return default
            value = values[0]
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value.item() if hasattr(value, "item") else value
        except Exception:
            return default

    @staticmethod
    def _series_dt(values):
        try:
            values = np.asarray(values, dtype=float).reshape(-1)
            if values.size < 2:
                return None
            diffs = np.diff(values)
            diffs = diffs[np.isfinite(diffs) & (diffs > 0.0)]
            if diffs.size:
                return float(np.median(diffs))
        except Exception:
            pass
        return None

    def _result_metadata_from_npz(self, data):
        """Extract the configuration that belongs to one saved MPC result."""
        metadata = {}
        for json_key in ("run_config_json", "identification_config_json"):
            raw = self._npz_scalar(data, json_key, None)
            if raw is None:
                continue
            try:
                payload = json.loads(str(raw))
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        metadata.setdefault(key, value)
            except Exception:
                pass

        direct_mapping = {
            "config_plant_model": "plant_model",
            "config_honu": "honu",
            "config_n_y": "n_y",
            "config_n_u": "n_u",
            "config_dt_control": "dt_control",
            "config_horizon": "horizon",
            "config_tau_u": "tau_u",
            "config_tau_d": "tau_d",
            "config_duration_sec": "duration_sec",
            "config_reference_duration_sec": "reference_duration_sec",
        }
        for source_key, target_key in direct_mapping.items():
            value = self._npz_scalar(data, source_key, None)
            if value is not None:
                metadata[target_key] = value

        for key in ("run_mode", "preg_blackbox_enabled", "r_preg", "plant_learning"):
            value = self._npz_scalar(data, key, None)
            if value is not None:
                metadata[key] = value

        if metadata.get("dt_control") is None:
            if "t_mpc" in data:
                metadata["dt_control"] = self._series_dt(data["t_mpc"])
            if metadata.get("dt_control") is None and "t" in data:
                metadata["dt_control"] = self._series_dt(data["t"])
        return metadata

    @staticmethod
    def _top_label_text(text):
        return text

    def _labeled(self, text, widget, width=None):
        box = QWidget(); lay = QVBoxLayout(box); lay.setContentsMargins(0,0,0,0); lay.setSpacing(1)
        lab = QLabel(self._top_label_text(text)); lab.setObjectName("topLabel"); lab.setToolTip(text)
        lab.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        if width is not None: widget.setFixedWidth(width)
        lay.addWidget(lab); lay.addWidget(widget); return box

    def _compact_group(self, title, rows, columns=2):
        g = QGroupBox(title)
        outer = QGridLayout(g)
        outer.setContentsMargins(7, 6, 7, 6)
        outer.setHorizontalSpacing(8)
        outer.setVerticalSpacing(5)
        for col in range(columns):
            outer.setColumnStretch(col, 1)
        for idx, (name, widget) in enumerate(rows):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            lab = QLabel(name)
            lab.setToolTip(name)
            lab.setWordWrap(False)
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            row.addWidget(widget, 0, Qt.AlignLeft)
            row.addStretch(1)
            cell_layout.addWidget(lab)
            cell_layout.addLayout(row)
            outer.addWidget(cell, idx // columns, idx % columns, alignment=Qt.AlignTop)
        return g

    def _build_ui(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(8)
        # MRAC-like page structure: left action/status panel and a
        # right work area with top selectors, parameter grid, and plots.
        self.physical_model_combo = QComboBox(); self.physical_model_combo.setMinimumContentsLength(42)
        self.physical_model_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.physical_model_combo.addItem("No active dataset", "")
        self.physical_model_combo.setEnabled(False)
        self.honu_combo = QComboBox(); self.honu_combo.addItems(["LNU", "QNU", "MLP"]); self.honu_combo.setFixedWidth(82)
        self.preg_enabled_check = QCheckBox("Use P regulator")
        self.plant_learning_combo = QComboBox(); self.plant_learning_combo.addItem("Ridge", "ridge"); self.plant_learning_combo.addItem("L-M", "lm"); self.plant_learning_combo.setFixedWidth(78)
        self.mpc_excitation_combo = QComboBox(); self.mpc_excitation_combo.addItem("Random Steps", "random_steps"); self.mpc_excitation_combo.addItem("Alternating Steps", "alternating_steps"); self.mpc_excitation_combo.setFixedWidth(128)
        self.mpc_excitation_combo.setToolTip("Selects the step sequence for the MPC reference d and optional controller excitation.")
        self.dt_mpc_spin = self._dspin(1e-4, 1e4, 1.0, 0.1, width=72)
        self.dt_control = self.dt_mpc_spin
        self.horizon = self._ispin(1, 500, 12, 64)
        self.window_length_spin = self._dspin(1e-4, 1e7, 150.0, 1.0, 6, width=78)
        self.n_y = self._ispin(1, 20, 3, 56); self.n_u = self._ispin(1, 20, 3, 56)
        self.duration=self._dspin(1,1e6,500,10,width=74)
        self.d_duration=self._dspin(1e-4,1e7,500,10,6,width=72)
        self.d_min=self._dspin(-1e12,1e12,0.0,0.05,9,width=72)
        self.d_max=self._dspin(-1e12,1e12,0.5,0.05,9,width=72)
        self.u_min=self._dspin(-1e12,1e12,-0.7,0.1,9,width=76)
        self.u_max=self._dspin(-1e12,1e12,0.7,0.1,9,width=76)
        self.u_min.setToolTip("Minimum optional excitation u used by the controller workflow. MPC control u is unrestricted afterward.")
        self.u_max.setToolTip("Maximum optional excitation u used by the controller workflow. MPC control u is unrestricted afterward.")
        self.line_width_spin=self._dspin(0.5,10.0,2.0,0.25,2,width=58)
        self.line_width_spin.valueChanged.connect(self._on_mpc_line_width_changed)
        self.dt_mpc_spin.valueChanged.connect(self.refresh_measured_dataset_preview)
        self.excitation_hold=self._dspin(1e-4,1e6,5,1,width=72)
        self.ref_hold=self._dspin(1e-4,1e6,60,5,width=72)
        self.tau_u_delay=self._dspin(0.0,1e6,0.0,0.1,6,width=72)
        self.tau_d_delay=self._dspin(0.0,1e6,0.0,0.1,6,width=72)
        self.excitation_hold.setToolTip("Duration of one constant excitation block u [s].")
        self.ref_hold.setToolTip("Duration of one constant reference block d [s].")
        self.tau_u_delay.setToolTip("Pure input delay tau_u used in the HONU plant regressor: u[k-n_tau_u-i], n_tau_u=round(tau_u/dt_MPC).")
        self.tau_d_delay.setToolTip("Pure reference delay tau_d before the reference model: d[k-n_tau_d], n_tau_d=round(tau_d/dt_MPC).")
        self.window_length_spin.setToolTip("Sliding-window duration [s]. The effective sample count is computed automatically as ceil(window length / dt MPC), with a minimum imposed by n_y and n_u. The initial excitation lasts for this window duration.")
        self.duration.setToolTip("Duration [s] used by trained HONU simulation and batch HONU identification.")
        self.d_duration.setToolTip("Duration [s] of reference d and the closed-loop MPC runs 3.1 and 3.2.")

        self.simulate_btn = QPushButton("Load measured data"); self.simulate_btn.clicked.connect(self.run_simulation_only)
        self.identify_btn = QPushButton("Identify HONU Plant"); self.identify_btn.clicked.connect(self.run_identify_honu)
        self.simulate_btn.setToolTip("Open the shared measured-data workspace.")
        self.run_frozen_btn = QPushButton("MPC - Frozen HONU"); self.run_frozen_btn.clicked.connect(self.run_mpc_frozen)
        self.run_btn = QPushButton("MPC - Sliding Retraining"); self.run_btn.clicked.connect(self.run_mpc_sliding)
        self.stop_btn = QPushButton("Stop"); self.stop_btn.setEnabled(False); self.stop_btn.clicked.connect(self.stop_mpc)
        self.full_screen_btn = QPushButton("Full screen"); self.full_screen_btn.setFixedWidth(92); self.full_screen_btn.clicked.connect(self.open_current_graph_full_screen)
        self.full_screen_btn.setToolTip("Open an independent movable and resizable copy of the current MPC graph tab.")

        self.activity = QProgressBar(); self.activity.setRange(0,1); self.activity.setValue(0)
        self.activity.setTextVisible(False); self.activity.setFixedHeight(18)
        self.activity.setToolTip("HONU identification and MPC computation activity")

        self.tau1=self._dspin(1e-6,1e6,4,0.5, width=74); self.tau2=self._dspin(1e-6,1e6,6,0.5, width=74)
        self.r_preg=self._dspin(-1e6,1e6,1.0,0.05,8,width=74)
        self.ridge=self._dspin(0,1e9,0.1,0.01,10, width=74)
        self.lm_epochs=self._ispin(1,10000,20,width=74)
        self.mlp_hidden_layers = QLineEdit("16,8"); self.mlp_hidden_layers.setFixedWidth(90)
        self.mlp_hidden_layers.setToolTip("Hidden-layer widths for MLP, comma-separated. Examples: 8, 6,4, 36,8 or 16,8,4. Output width is automatic.")
        self.mu_bibs=self._dspin(0,1.999999,0.5,0.05,8, width=74); self.eps_bibs=self._dspin(1e-15,1e6,1e-8,1e-8,12, width=74)
        self.pca_mode=QComboBox(); self.pca_mode.addItems(["Rank", "Variability"]); self.pca_mode.setCurrentText("Variability")
        self.pca_mode.setToolTip("Rank uses all numerically independent PCA components. Variability uses the minimum number meeting the selected retained variability.")
        self.pca_variability=self._dspin(0.01,100.0,99.9,0.1,4, width=74)
        self.pca_variability.setSuffix(" %")
        self.pca_variability.setToolTip("Percentage of cumulative variability retained in Variability mode.")
        self.pca_mode.currentTextChanged.connect(lambda mode: self.pca_variability.setEnabled(mode == "Variability"))
        self.preg_enabled_check.toggled.connect(self._on_mpc_plant_mode_changed)
        self.plant_learning_combo.currentIndexChanged.connect(self._on_mpc_learning_changed)
        self.honu_combo.currentTextChanged.connect(self._on_mpc_model_changed)
        self.r_preg.setToolTip("Internal P-controller gain. MPC/ODE input is the external command u_new; physical input is r_Preg*(u_new-y).")
        self.lm_epochs.setToolTip("Levenberg-Marquardt epochs for each sliding-window HONU fit.")
        self.ridge.setToolTip("Shared lambda: Ridge regularization for Ridge learning, or initial damping for Levenberg-Marquardt.")
        self.mu_bibs.setToolTip("Normalized online correction gain used after the sliding-window ridge estimate. Larger values adapt faster; valid interval is below 2.")
        self.eps_bibs.setToolTip("Small positive denominator regularization in the normalized correction; prevents division by a nearly zero regressor norm.")
        self.q_track=self._dspin(0,1e12,50,5, width=74); self.r_du=self._dspin(0,1e12,8,1, width=74); self.r_ddu=self._dspin(0,1e12,20,1, width=74); self.r_u=self._dspin(0,1e12,0.01,0.01,10, width=74)
        self.opt_iter=self._ispin(1,10000,30, width=74); self.seed=self._ispin(0,2147483647,12, width=74)
        self.pca_mode.setFixedWidth(86)

        left = QScrollArea(); left.setWidgetResizable(True); left.setFixedWidth(360)
        panel = QWidget(); pl = QVBoxLayout(panel); pl.setContentsMargins(6,6,6,6); pl.setSpacing(8)

        title = QLabel("HONU MPC")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: 600; color: #183b73;")
        pl.addWidget(title)

        actions_group = QGroupBox("MPC workflow")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(7, 6, 7, 6)
        actions_layout.setSpacing(5)
        self.simulate_btn.setText("1. Load measured data")
        self.identify_btn.setText("2. Identify HONU Plant")
        self.run_frozen_btn.setText("3.1 MPC - Frozen HONU")
        self.run_btn.setText("3.2 MPC - Sliding Retraining")
        self.simulate_btn.setMinimumWidth(0); self.simulate_btn.setMaximumWidth(16777215)
        self.simulate_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        actions_layout.addWidget(self.simulate_btn)
        self.identify_btn.setMinimumWidth(0); self.identify_btn.setMaximumWidth(16777215)
        self.identify_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        actions_layout.addWidget(self.identify_btn)
        mpc_actions = QHBoxLayout(); mpc_actions.setSpacing(5)
        for button in (self.run_frozen_btn, self.run_btn):
            button.setMinimumWidth(0); button.setMaximumWidth(16777215)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            mpc_actions.addWidget(button)
        actions_layout.addLayout(mpc_actions)
        pl.addWidget(actions_group)

        self.stop_btn.setText("Stop current calculation")
        self.stop_btn.setMinimumWidth(0); self.stop_btn.setMaximumWidth(16777215)
        self.stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pl.addWidget(self.stop_btn)

        results_group = QGroupBox("Results")
        results_layout = QGridLayout(results_group)
        results_layout.setContentsMargins(7, 8, 7, 7)
        results_layout.setHorizontalSpacing(5)
        results_layout.setVerticalSpacing(5)
        self.btn_result_simulation = QPushButton("1. Measured dataset")
        self.btn_result_identify = QPushButton("2. Identified HONU Plant")
        self.btn_result_frozen = QPushButton("3.1 MPC - Frozen HONU")
        self.btn_result_mpc = QPushButton("3.2 MPC - Sliding Retraining")
        self.btn_result_weights = QPushButton("HONU weights")
        self.btn_result_rho = QPushButton("Spectral radii")
        self.btn_result_simulation.clicked.connect(self.show_simulation_result)
        self.btn_result_identify.clicked.connect(self.show_identification_result)
        self.btn_result_frozen.clicked.connect(self.show_frozen_mpc_result)
        self.btn_result_mpc.clicked.connect(self.show_mpc_result)
        self.btn_result_weights.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.btn_result_rho.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        results_layout.addWidget(self.btn_result_simulation, 0, 0, 1, 2)
        results_layout.addWidget(self.btn_result_identify, 1, 0, 1, 2)
        results_layout.addWidget(self.btn_result_frozen, 2, 0)
        results_layout.addWidget(self.btn_result_mpc, 2, 1)
        results_layout.addWidget(self.btn_result_weights, 3, 0)
        results_layout.addWidget(self.btn_result_rho, 3, 1)
        pl.addWidget(results_group)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(7, 8, 7, 7)
        status_layout.setSpacing(4)
        self.mpc_status_label = QLabel("● Ready")
        self.mpc_status_label.setObjectName("statusIdle")
        self.activity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.activity.setMaximumWidth(16777215)
        status_layout.addWidget(self.mpc_status_label)
        status_layout.addWidget(self.activity)
        pl.addWidget(status_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(7, 8, 7, 7)
        self.status=QTextEdit(); self.status.setReadOnly(True); self.status.setMinimumHeight(220)
        self.status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout.addWidget(self.status, 1)
        pl.addWidget(log_group, 1)
        left.setWidget(panel)
        root.addWidget(left)

        top = QFrame(); top.setObjectName("topPanel"); top.setFrameShape(QFrame.StyledPanel)
        top_outer = QHBoxLayout(top)
        top_outer.setContentsMargins(8, 6, 8, 6)
        top_outer.setSpacing(10)
        top_outer.addWidget(self._labeled("active dataset", self.physical_model_combo, 420))
        top_outer.addWidget(self._labeled("dt_MPC [sec]", self.dt_control))
        top_outer.addWidget(self._labeled("HONU plant", self.honu_combo))
        top_outer.addWidget(self._labeled("learning", self.plant_learning_combo))
        top_outer.addWidget(self._labeled("excitation u / reference d", self.mpc_excitation_combo))
        top_outer.addStretch(1)
        top_outer.addWidget(self._labeled("line width [px]", self.line_width_spin))
        top_outer.addWidget(self.full_screen_btn, 0, Qt.AlignBottom)

        params_group = QGroupBox("MPC parameters")
        params_grid = QGridLayout(params_group)
        params_grid.setContentsMargins(10, 8, 10, 8)
        params_grid.setHorizontalSpacing(10)
        params_grid.setVerticalSpacing(6)

        def add_param_row(row_idx, row_title, items):
            title_label = QLabel(row_title)
            title_label.setMinimumWidth(92)
            params_grid.addWidget(title_label, row_idx, 0, alignment=Qt.AlignTop | Qt.AlignLeft)
            for col_idx, item in enumerate(items, start=1):
                if item is None:
                    continue
                label, widget = item
                params_grid.addWidget(self._labeled(label, widget), row_idx, col_idx, alignment=Qt.AlignTop | Qt.AlignLeft)
            params_grid.setColumnStretch(len(items) + 1, 1)

        add_param_row(0, "Reference d", [
            ("d duration [s]", self.d_duration),
            ("d step width [s]", self.ref_hold),
            ("tau_d [s]", self.tau_d_delay),
            ("Tau 1 [s]", self.tau1),
            ("Tau 2 [s]", self.tau2),
            ("d_min", self.d_min),
            ("d_max", self.d_max),
        ])
        add_param_row(1, "Plant HONU", [
            ("n_y", self.n_y),
            ("n_u", self.n_u),
            ("window length [s]", self.window_length_spin),
            ("lambda", self.ridge),
            ("epochs", self.lm_epochs),
            ("MLP hidden", self.mlp_hidden_layers),
            ("PCA mode", self.pca_mode),
            ("retained variability", self.pca_variability),
        ])
        add_param_row(2, "Online\ncorrection", [
            ("normalized gain", self.mu_bibs),
            ("denominator eps", self.eps_bibs),
        ])
        add_param_row(3, "MPC\nobjective", [
            ("MPC horizon", self.horizon),
            ("Q tracking", self.q_track),
            ("R delta u", self.r_du),
            ("R delta2 u", self.r_ddu),
            ("R u", self.r_u),
            ("optimizer iter.", self.opt_iter),
            ("random seed", self.seed),
        ])

        work_area = QWidget()
        work_layout = QVBoxLayout(work_area)
        work_layout.setContentsMargins(0,0,0,0)
        work_layout.setSpacing(8)
        work_layout.addWidget(top)
        work_layout.addWidget(params_group)
        self.tabs=QTabWidget(); self.tabs.setDocumentMode(True)

        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        work_layout.addWidget(self.tabs,1)
        root.addWidget(work_area,1)

        self.response_plot=self._new_plot_tab("Closed loop",3)
        self.weights_plot=self._new_plot_tab("HONU weights w",2)
        self.rho_plot=self._new_plot_tab("Spectral radii",2)
        self._on_mpc_plant_mode_changed()
        self._on_mpc_model_changed()

    def _on_mpc_physical_model_changed(self, *_args):
        return

    def _new_plot_tab(self,title,rows):
        w=pg.GraphicsLayoutWidget(); w.setBackground("w"); plots=[]
        title_item = w.addLabel("", row=0, col=0, justify="center")
        title_item.setText("", color="#183b73", size="12pt", bold=True)
        self.tab_titles[w] = title_item
        for r in range(rows):
            view_box = ZoomResetViewBox(owner=self)
            p=w.addPlot(row=r+1,col=0,viewBox=view_box,axisItems={"left":CompactYAxis("left")})
            p.setMouseEnabled(x=True, y=True)
            view_box.setMouseMode(pg.ViewBox.RectMode)
            p.showGrid(x=True,y=True,alpha=0.55)
            p.getAxis("left").setGrid(180)
            p.getAxis("bottom").setGrid(180)
            p.getAxis("left").setPen(pg.mkPen("k")); p.getAxis("bottom").setPen(pg.mkPen("k"))
            p.getAxis("left").setTextPen(pg.mkPen("k")); p.getAxis("bottom").setTextPen(pg.mkPen("k"))
            if r<rows-1:
                p.getAxis("bottom").setStyle(showValues=False)
                p.getAxis("bottom").setLabel("")
            plots.append(p)
        for p in plots[1:]: p.setXLink(plots[0])
        self.tabs.addTab(w,title); self.tab_plots[w]=plots; return plots

    def reset_current_graph_ranges(self):
        """Restore the original range of the currently selected MPC graph tab."""
        widget = self.tabs.currentWidget()
        plots = self.tab_plots.get(widget, [])
        ranges = self._initial_plot_ranges.get(widget, [])
        if len(ranges) != len(plots):
            for plot in plots:
                try:
                    plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
                    plot.autoRange()
                    plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
                except Exception:
                    pass
            return
        for plot, initial_range in zip(plots, ranges):
            if initial_range is None:
                continue
            try:
                plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
                plot.setRange(xRange=initial_range[0], yRange=initial_range[1], padding=0.0)
                plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            except Exception:
                pass

    def _clone_current_graph_for_full_screen(self, source_widget, title):
        clone=pg.GraphicsLayoutWidget(); clone.setBackground("w")
        source_title_item = self.tab_titles.get(source_widget)
        source_title = source_title_item.text if source_title_item is not None else title
        clone.addLabel(source_title or title, row=0, col=0, justify="center", color="#183b73", size="12pt", bold=True)
        source_plots=list(self.tab_plots.get(source_widget, [])); clone_plots=[]; ranges=[]
        for i,src in enumerate(source_plots):
            view_box = ZoomResetViewBox(owner=None)
            dst=clone.addPlot(row=i+1,col=0,viewBox=view_box,axisItems={"left":CompactYAxis("left")})
            dst.setMouseEnabled(x=True, y=True)
            view_box.setMouseMode(pg.ViewBox.RectMode)
            dst.showGrid(x=True,y=True,alpha=0.55)
            dst.getAxis("left").setGrid(180); dst.getAxis("bottom").setGrid(180)
            dst.getAxis("left").setPen(pg.mkPen("k")); dst.getAxis("bottom").setPen(pg.mkPen("k"))
            dst.getAxis("left").setTextPen(pg.mkPen("k")); dst.getAxis("bottom").setTextPen(pg.mkPen("k"))
            try:
                dst.setLabel("left",src.getAxis("left").labelText or "")
                dst.setLabel("bottom",src.getAxis("bottom").labelText or "")
            except Exception:
                pass
            if i>0: dst.setXLink(clone_plots[0])
            for item in src.listDataItems():
                x,y=item.getData()
                if x is None or y is None: continue
                opts=item.opts
                copied=dst.plot(
                    np.array(x,copy=True), np.array(y,copy=True),
                    pen=pg.mkPen(opts.get("pen")) if opts.get("pen") is not None else None,
                    symbol=opts.get("symbol"),
                    symbolSize=opts.get("symbolSize"),
                    symbolPen=pg.mkPen(opts.get("symbolPen")) if opts.get("symbolPen") is not None else None,
                    symbolBrush=pg.mkBrush(opts.get("symbolBrush")) if opts.get("symbolBrush") is not None else None,
                    name=item.name(),
                )
                copied.setVisible(item.isVisible())
            try:
                vr=src.getViewBox().viewRange(); rr=[list(vr[0]),list(vr[1])]
                dst.setRange(xRange=rr[0],yRange=rr[1],padding=0.0); ranges.append(rr)
            except Exception: ranges.append(None)
            # Preserve hidden axes from the source tab.  Otherwise an empty
            # lower axis can become visible only in full screen and steal the
            # shared x label from the actual lowest displayed signal.
            dst.setVisible(src.isVisible())
            clone_plots.append(dst)
        return clone,clone_plots,ranges

    def open_current_graph_full_screen(self):
        if self.tabs.count()==0:
            QMessageBox.information(self,"Full screen","No MPC graph is available."); return
        source=self.tabs.currentWidget(); title=self.tabs.tabText(self.tabs.currentIndex()) or "HONU MPC graph"
        clone,plots,ranges=self._clone_current_graph_for_full_screen(source,title)
        result_meta = dict(self._loaded_result_metadata)
        plant_model = str(result_meta.get("plant_model", "")).strip()
        plant_title = plant_display_name(plant_model) if plant_model else "saved physical plant"
        meta_parts = [plant_title]
        honu_name = str(result_meta.get("honu", "")).strip()
        if honu_name:
            meta_parts.append(honu_name)
        for key, label in (("dt_control", "dt MPC"),):
            try:
                value = float(result_meta[key])
            except (KeyError, TypeError, ValueError):
                continue
            if np.isfinite(value):
                meta_parts.append(f"{label}={value:g} s")
        if not result_meta:
            meta_parts.append("exact run metadata unavailable")
        meta=" | ".join(meta_parts)
        win=FullScreenPlotWindow(
            clone, plots, ranges, f"HONU MPC | {title}",
            restore_callback=None, metadata_text=meta, parent=None,
            line_width_value=float(self.line_width_spin.value()),
        )
        COMPARISON_PLOT_WINDOWS.append(win)
        win.destroyed.connect(lambda *_: COMPARISON_PLOT_WINDOWS.remove(win) if win in COMPARISON_PLOT_WINDOWS else None)
        win.resize(1300,800); win.show(); win.raise_(); win.activateWindow()


    def _on_mpc_plant_mode_changed(self, *_args):
        self.r_preg.setEnabled(bool(self.preg_enabled_check.isChecked()))

    def _on_mpc_model_changed(self, *_args):
        model = str(self.honu_combo.currentText()).upper()
        previous = self.plant_learning_combo.currentData()
        self.plant_learning_combo.blockSignals(True)
        self.plant_learning_combo.clear()
        if model == "MLP":
            self.plant_learning_combo.addItem("Adam", "adam")
            self.plant_learning_combo.addItem("L-BFGS", "lbfgs")
            self.plant_learning_combo.addItem("Adam + L-BFGS", "adam_lbfgs")
            index = self.plant_learning_combo.findData(previous)
            self.plant_learning_combo.setCurrentIndex(index if index >= 0 else 2)
        else:
            self.plant_learning_combo.addItem("Ridge", "ridge")
            self.plant_learning_combo.addItem("L-M", "lm")
            index = self.plant_learning_combo.findData(previous)
            self.plant_learning_combo.setCurrentIndex(index if index >= 0 else 0)
        self.plant_learning_combo.blockSignals(False)
        self.mlp_hidden_layers.setEnabled(model == "MLP")
        self.mu_bibs.setEnabled(model != "MLP")
        self.eps_bibs.setEnabled(model != "MLP")
        self._on_mpc_learning_changed()

    def _on_mpc_learning_changed(self, *_args):
        is_mlp = str(self.honu_combo.currentText()).upper() == "MLP"
        use_lm = self.plant_learning_combo.currentData() == "lm"
        self.ridge.setEnabled(True)
        self.lm_epochs.setEnabled(is_mlp or use_lm)
        self.lm_epochs.setToolTip("MLP optimizer epochs/iterations." if is_mlp else "Levenberg-Marquardt epochs for each sliding-window HONU fit.")
        self.ridge.setToolTip("MLP L2 regularization." if is_mlp else "Shared lambda: Ridge regularization for Ridge learning, or initial damping for Levenberg-Marquardt.")

    def _current_mpc_excitation_mode(self):
        # Resolve directly from the currently visible selector index at run time.
        # This avoids stale/default item data being reused after GUI changes.
        return "alternating_steps" if self.mpc_excitation_combo.currentIndex() == 1 else "random_steps"

    def _config(self):
        excitation_mode = self._current_mpc_excitation_mode()
        return {"data_source":self.physical_model_combo.currentData() or "measured","plant_model":"measured_honu","honu":self.honu_combo.currentText(),
                "preg_blackbox_enabled":bool(self.preg_enabled_check.isChecked()),"r_preg":self.r_preg.value(),
                "plant_learning":self.plant_learning_combo.currentData(),"mlp_optimizer":self.plant_learning_combo.currentData(),
                "mlp_hidden_layers":self.mlp_hidden_layers.text().strip(),
                "mlp_epochs":self.lm_epochs.value(),
                "mlp_learning_rate":1.0e-3,"prediction_target":"delta",
                "lm_epochs":self.lm_epochs.value(),"lambda":self.ridge.value(),
                "dt_control":self.dt_control.value(),"horizon":self.horizon.value(),
                "window_length_sec":self.window_length_spin.value(),"n_y":self.n_y.value(),"n_u":self.n_u.value(),
                "duration_sec":self.duration.value(),
                "reference_duration_sec":self.d_duration.value(),
                "u_min":self.u_min.value(),"u_max":self.u_max.value(),
                "tau_u":self.tau_u_delay.value(),
                "excitation_hold_sec":self.excitation_hold.value(),
                "excitation_mode":excitation_mode,
                "u_excitation_mode":excitation_mode,
                "d_reference_mode":excitation_mode,
                "d_min":self.d_min.value(),"d_max":self.d_max.value(),
                "tau_d":self.tau_d_delay.value(),"hold_sec":self.ref_hold.value(),"tau1":self.tau1.value(),"tau2":self.tau2.value(),"ridge":self.ridge.value(),
                "mu_bibs":self.mu_bibs.value(),"eps_bibs":self.eps_bibs.value(),"q_track":self.q_track.value(),
                "r_du":self.r_du.value(),"r_ddu":self.r_ddu.value(),"r_u":self.r_u.value(),"opt_iter":self.opt_iter.value(),"seed":self.seed.value(),
                "pca_selection_mode":self.pca_mode.currentText().lower(),
                "pca_retained_variability":self.pca_variability.value()/100.0}

    def _append_mpc_configuration(self, cfg, run_mode):
        """Write a concise effective configuration to the MPC log."""
        mode_label = 'simulate' if run_mode == 'simulate' else ('identify' if run_mode == 'identify' else ('mpc_frozen' if run_mode == 'mpc_frozen' else 'mpc_sliding'))
        self.status.append(f"mode={mode_label}")
        self.status.append(
            f"data_source={cfg['data_source']}; "
            f"r_Preg={cfg['r_preg']:.9g}; HONU={cfg['honu']}; n_y={cfg['n_y']}; n_u={cfg['n_u']}"
        )
        self.status.append(
            f"duration={cfg['duration_sec']:.9g} s; d_duration={cfg['reference_duration_sec']:.9g} s; "
            f"dt_MPC={cfg['dt_control']:.9g} s; "
            f"line_width={self.line_width_spin.value():.9g} px"
        )
        if run_mode == "simulate":
            self.status.append(
                f"u_excitation={cfg['excitation_mode']}; u_min={cfg['u_min']:.9g}; u_max={cfg['u_max']:.9g}; "
                f"u_step_width={cfg['excitation_hold_sec']:.9g} s"
            )
        else:
            self.status.append(
                f"step_mode={cfg['excitation_mode']}; u_step_width={cfg['excitation_hold_sec']:.9g} s; "
                f"d_step_width={cfg['hold_sec']:.9g} s"
            )
        self.status.append(
            f"tau1={cfg['tau1']:.9g} s; tau2={cfg['tau2']:.9g} s; "
            f"d_min={cfg['d_min']:.9g}; d_max={cfg['d_max']:.9g}; "
            f"tau_u={cfg['tau_u']:.9g} s; tau_d={cfg['tau_d']:.9g} s"
        )
        is_mlp = str(cfg['honu']).upper() == "MLP"
        if is_mlp:
            optimizer_name = {
                "adam": "Adam",
                "lbfgs": "L-BFGS",
                "adam_lbfgs": "Adam + L-BFGS",
            }.get(str(cfg.get('mlp_optimizer', cfg['plant_learning'])).lower(), str(cfg['plant_learning']))
            learning_details = (
                f"optimizer={optimizer_name}; epochs/iterations={cfg['lm_epochs']}; "
                f"L2={cfg['lambda']:.9g}"
            )
        else:
            learning_details = f"learning={cfg['plant_learning']}"
            if cfg['plant_learning'] == "ridge":
                learning_details += f"; ridge_lambda={cfg['lambda']:.9g}"
            elif cfg['plant_learning'] == "lm":
                learning_details += f"; lambda_0={cfg['lambda']:.9g}; epochs={cfg['lm_epochs']}"
        training_scope = (f"batch_training_length={cfg['duration_sec']:.9g} s" if run_mode in {"identify", "mpc_frozen"} else f"window_length={cfg['window_length_sec']:.9g} s")
        self.status.append(
            f"{training_scope}; {learning_details}; PCA_mode={cfg['pca_selection_mode']}; "
            f"PCA_variability={100.0*cfg['pca_retained_variability']:.9g} %"
        )
        if not is_mlp:
            self.status.append(
                f"mu_bibs={cfg['mu_bibs']:.9g}; eps_bibs={cfg['eps_bibs']:.9g}"
            )
        self.status.append(
            f"Np={cfg['horizon']}; Q={cfg['q_track']:.9g}; R_du={cfg['r_du']:.9g}; "
            f"R_ddu={cfg['r_ddu']:.9g}; R_u={cfg['r_u']:.9g}; "
            f"opt_iter={cfg['opt_iter']}; seed={cfg['seed']}"
        )

    def run_mpc(self):
        self.run_mpc_sliding()

    def run_identify_honu(self):
        self._start_process("identify")

    def run_mpc_frozen(self):
        """Run MPC 3.1 with the already identified HONU model.

        Frozen MPC intentionally does not compare the current identification
        widgets with the configuration used during HONU training.  The model
        file is self-contained; only a readable trained HONU and a valid
        reference-d configuration are required.
        """
        if not self.identification_output_file.exists():
            QMessageBox.warning(
                self,
                "HONU MPC",
                "Run 2. Identify HONU Plant before 3.1 MPC - Frozen HONU.",
            )
            return
        try:
            with np.load(self.identification_output_file, allow_pickle=False) as z:
                required = {"theta", "model", "ny", "nu", "delay_u"}
                missing = sorted(required.difference(z.files))
                if missing:
                    raise ValueError("missing model fields: " + ", ".join(missing))
                theta = np.asarray(z["theta"], dtype=float).reshape(-1)
                if theta.size == 0 or not np.all(np.isfinite(theta)):
                    raise ValueError("HONU coefficients are empty or non-finite")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Invalid identified HONU",
                "The trained HONU model cannot be loaded. Run 2. Identify HONU Plant again."
                f"\n\n{exc}",
            )
            return
        self._start_process("mpc_frozen")

    def run_mpc_sliding(self):
        self._start_process("mpc_sliding")

    def run_simulation_only(self):
        self.refresh_measured_dataset_preview(show_errors=True)

    def refresh_measured_dataset_preview(self, *_args, show_errors=False):
        """Render the active measured curves and dt_MPC sample points immediately."""
        path = BASE_DIR / "data_uy.txt"
        if not path.exists():
            if show_errors:
                QMessageBox.warning(self, "Measured data", "Load and activate measured data first.")
            return
        try:
            data = np.loadtxt(path, comments="#", ndmin=2)
            if data.shape[1] < 3 or len(data) < 3:
                raise ValueError("data_uy.txt must contain t, u, y")
            t, u, y = data[:, 0], data[:, 1], data[:, 2]
            raw_dt = float(np.median(np.diff(t)))
            dt_mpc = float(self.dt_mpc_spin.value())
            if dt_mpc < raw_dt * (1.0 - 1e-9):
                raise ValueError(f"dt_MPC={dt_mpc:g} s is smaller than active data sampling {raw_dt:g} s")
            if np.isclose(dt_mpc, raw_dt, rtol=1e-9, atol=1e-12):
                tq, uq, yq = t.copy(), u.copy(), y.copy()
            else:
                tq = np.arange(t[0], t[-1] + 0.5 * dt_mpc, dt_mpc)
                idx = np.searchsorted(t, tq, side="left")
                idx = np.clip(idx, 0, len(t)-1)
                left = np.clip(idx-1, 0, len(t)-1)
                idx = np.where(np.abs(tq-t[left]) <= np.abs(t[idx]-tq), left, idx)
                uq, yq = u[idx], y[idx]
            np.savez(self.simulation_output_file, t=t, u=u, y=y, t_mpc=tq, u_mpc=uq, y_mpc=yq,
                     config_dt_control=np.asarray([dt_mpc]), run_mode=np.asarray(["simulate"]))
            self.output_file = self.simulation_output_file
            self.current_result_mode = "simulate"
            self.load_result(update_log=False, preserve_view=False)
            self.tabs.setCurrentIndex(0)
        except Exception as exc:
            if show_errors:
                QMessageBox.warning(self, "Measured data", str(exc))
            else:
                self.status.append(f"Measured-data preview warning: {exc}")

    def _start_process(self, run_mode):
        if self.process is not None and self.process.state()!=QProcess.NotRunning: return
        if self.d_duration.value() <= self.ref_hold.value():
            QMessageBox.warning(self,"HONU MPC","d duration must be larger than d step width."); return
        if self.u_min.value() >= self.u_max.value():
            QMessageBox.warning(self,"HONU MPC","u_min must be smaller than u_max."); return
        if self.plant_learning_combo.currentData() == "lm" and self.ridge.value() <= 0.0:
            QMessageBox.warning(self,"HONU MPC","Levenberg-Marquardt requires positive lambda."); return
        cfg=self._config(); cfg["run_mode"]=run_mode; cfg["data_file"]=str(BASE_DIR / "data_uy.txt")
        cfg["identified_model_file"] = str(self.identification_output_file)
        if run_mode == "simulate":
            self.output_file = self.simulation_output_file
        elif run_mode == "identify":
            self.output_file = self.identification_output_file
        elif run_mode == "mpc_frozen":
            self.output_file = self.mpc_frozen_output_file
        else:
            self.output_file = self.mpc_sliding_output_file
        self.current_result_mode = run_mode
        self.config_file.write_text(json.dumps(cfg,indent=2),encoding="utf-8")
        self.status.clear()
        self._append_mpc_configuration(cfg, run_mode)
        self.status.append("")
        self.status.append("running...")
        self.stop_requested = False
        self.run_btn.setEnabled(False); self.run_frozen_btn.setEnabled(False); self.identify_btn.setEnabled(False); self.simulate_btn.setEnabled(False); self.stop_btn.setEnabled(True); self.activity.setRange(0,0); self.process=QProcess(self)
        env=QProcessEnvironment.systemEnvironment(); env.insert("MPLBACKEND","Agg"); self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(BASE_DIR)); self.process.setProgram(PYTHON_EXE)
        self.process.setArguments([str(BASE_DIR/"HONU_MPC_runner.py"),str(self.config_file),str(self.output_file)])
        self.process.readyReadStandardOutput.connect(self._read_out); self.process.readyReadStandardError.connect(self._read_err)
        self.process.finished.connect(self._finished); self.process.start()


    def stop_mpc(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        self.stop_requested = True
        self.status.append("Stopping HONU MPC...")
        self.stop_btn.setEnabled(False)
        self.process.terminate()
        QTimer.singleShot(1500, self._kill_mpc_if_running)

    def _kill_mpc_if_running(self):
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            self.process.kill()

    def _read_out(self):
        process = self.sender()
        if not isinstance(process, QProcess):
            process = self.process
        if process is None:
            return
        text = bytes(process.readAllStandardOutput()).decode(errors="replace").rstrip()
        if text:
            self.status.append(text)

    def _read_err(self):
        process = self.sender()
        if not isinstance(process, QProcess):
            process = self.process
        if process is None:
            return
        text = bytes(process.readAllStandardError()).decode(errors="replace").rstrip()
        if text:
            self.status.append(text)

    def _finished(self, code, status):
        process = self.sender()
        if isinstance(process, QProcess):
            stdout = bytes(process.readAllStandardOutput()).decode(errors="replace").rstrip()
            stderr = bytes(process.readAllStandardError()).decode(errors="replace").rstrip()
            if stdout:
                self.status.append(stdout)
            if stderr:
                self.status.append(stderr)
        self.process = None
        if isinstance(process, QProcess):
            process.deleteLater()
        self.run_btn.setEnabled(True); self.run_frozen_btn.setEnabled(True); self.identify_btn.setEnabled(True); self.simulate_btn.setEnabled(True); self.stop_btn.setEnabled(False); self.activity.setRange(0,1)
        if self.stop_requested:
            self.activity.setValue(0); self.status.append("HONU MPC stopped by user."); return
        self.activity.setValue(1 if code==0 else 0)
        if code!=0 or not self.output_file.exists(): self.status.append(f"MPC failed, exit code {code}"); return
        self.status.append("Preparing result plots...")
        QTimer.singleShot(0, self._load_finished_mpc_result)

    def _load_finished_mpc_result(self):
        """Load and draw a completed MPC result without blocking QProcess cleanup."""
        QApplication.processEvents()
        try:
            self.load_result()
            self.status.append("MPC result loaded.")
        except Exception as exc:
            self.status.append(f"Plot error: {exc}")
        QApplication.processEvents()

    def show_simulation_result(self):
        if not self.simulation_output_file.exists():
            self.status.append("No measured dataset result is available.")
            return
        self.output_file = self.simulation_output_file
        self.current_result_mode = "simulate"
        self.load_result(update_log=False, preserve_view=False)
        self.tabs.setCurrentIndex(0)

    def show_identification_result(self):
        if not self.identification_output_file.exists():
            self.status.append("No identified HONU Plant result is available.")
            return
        self.output_file = self.identification_output_file
        self.current_result_mode = "identify"
        self.load_result()
        self.tabs.setCurrentIndex(0)

    def show_frozen_mpc_result(self):
        if not self.mpc_frozen_output_file.exists():
            self.status.append("No MPC - Frozen HONU result is available.")
            return
        self.output_file = self.mpc_frozen_output_file
        self.current_result_mode = "mpc_frozen"
        self.load_result(update_log=False, preserve_view=False)
        self.tabs.setCurrentIndex(0)

    def show_mpc_result(self):
        if not self.mpc_output_file.exists():
            self.status.append("No HONU MPC result is available.")
            return
        self.output_file = self.mpc_sliding_output_file
        self.current_result_mode = "mpc_sliding"
        self.load_result(update_log=False, preserve_view=False)
        self.tabs.setCurrentIndex(0)

    def _on_mpc_line_width_changed(self, _value):
        """Debounce expensive redraws while the line-width spin box is changing."""
        if not hasattr(self, "_line_width_redraw_timer"):
            self._line_width_redraw_timer = QTimer(self)
            self._line_width_redraw_timer.setSingleShot(True)
            self._line_width_redraw_timer.timeout.connect(self._redraw_mpc_line_width)
        self._line_width_redraw_timer.start(180)

    def _redraw_mpc_line_width(self):
        if self.output_file.exists() and (self.process is None or self.process.state() == QProcess.NotRunning):
            try:
                self.load_result(update_log=False, preserve_view=True)
            except Exception:
                pass

    def load_result(self, update_log=True, preserve_view=False):
        saved_view_ranges = {}
        QApplication.processEvents()
        if preserve_view:
            for widget, plots in self.tab_plots.items():
                saved_view_ranges[widget] = []
                for plot in plots:
                    try:
                        vr = plot.getViewBox().viewRange()
                        saved_view_ranges[widget].append([list(vr[0]), list(vr[1])])
                    except Exception:
                        saved_view_ranges[widget].append(None)
        z=np.load(self.output_file, allow_pickle=False)
        t=np.asarray(z["t"], dtype=float)
        result_meta=self._result_metadata_from_npz(z)
        self._loaded_result_metadata=dict(result_meta)
        dt_value=result_meta.get("dt_control")
        try:
            dt=float(dt_value)
        except (TypeError, ValueError):
            dt=float(self._series_dt(t) or 0.0)
        lw=float(self.line_width_spin.value())
        QApplication.processEvents()
        for p in self.response_plot+self.weights_plot+self.rho_plot:
            p.clear(); p.showGrid(x=True,y=True,alpha=0.55)
            p.getAxis("left").setGrid(180)
            p.getAxis("bottom").setGrid(180)
            p.getAxis("left").setPen(pg.mkPen("k")); p.getAxis("bottom").setPen(pg.mkPen("k"))
            p.getAxis("left").setTextPen(pg.mkPen("k")); p.getAxis("bottom").setTextPen(pg.mkPen("k"))
            p.getAxis("bottom").setLabel("")
        p0, p1, p2 = self.response_plot
        w0, w1 = self.weights_plot
        r0, r1 = self.rho_plot
        result_mode=str(result_meta.get("run_mode", "mpc"))
        self.current_result_mode=result_mode
        preg_enabled=bool(result_meta.get("preg_blackbox_enabled", False))
        try:
            r_preg=float(result_meta.get("r_preg", 1.0))
        except (TypeError, ValueError):
            r_preg=1.0
        plant_model=str(result_meta.get("plant_model", "")).strip()
        plant_title=plant_display_name(plant_model) if plant_model else "Saved physical plant"
        honu_name=str(result_meta.get("honu", "saved HONU")).strip() or "saved HONU"
        horizon_value=result_meta.get("horizon")
        try:
            horizon_text=str(int(horizon_value))
        except (TypeError, ValueError):
            horizon_text="saved"
        plant_mode_text = f"ODE + P regulator, r_Preg={r_preg:g}" if preg_enabled else "standalone ODE"

        # Pure measured data has no HONU/BIBS diagnostics. Keep only the
        # closed-loop/simulation graph visible; restore all result tabs for MPC.
        diagnostics_available = result_mode != "simulate"
        self.tabs.setTabVisible(1, diagnostics_available)
        self.tabs.setTabVisible(2, diagnostics_available)
        self.btn_result_simulation.setEnabled(self.simulation_output_file.exists())
        self.btn_result_identify.setEnabled(self.identification_output_file.exists())
        self.btn_result_frozen.setEnabled(self.mpc_frozen_output_file.exists())
        self.btn_result_mpc.setEnabled(self.mpc_sliding_output_file.exists())
        self.btn_result_weights.setEnabled(diagnostics_available)
        self.btn_result_rho.setEnabled(diagnostics_available)
        if not diagnostics_available:
            self.tabs.setCurrentIndex(0)
        if result_mode == "identify":
            self.tabs.setTabText(0, "HONU Plant identification")
            self.btn_result_identify.setText("2. Identified HONU Plant")
            learning_key = str(result_meta.get("plant_learning", "ridge")).strip().lower()
            use_epoch_diagnostics = learning_key == "lm"

            for plot in (p0, p1, p2, w0, w1, r0, r1):
                plot.show()

            y_n = np.asarray(z.get("y_n", np.full_like(t, np.nan)), dtype=float)
            e_ident = np.asarray(z.get("e_ident", np.asarray(z["y"], dtype=float) - y_n), dtype=float)
            p0.plot(t, z["y"], pen=pg.mkPen("k", width=lw), name="y")
            p0.plot(t, y_n, pen=pg.mkPen("g", width=lw), name="y_n")
            p0.setLabel("left", "y, y_n")
            p1.plot(t, z["u"], pen=pg.mkPen("b", width=lw), name="u")
            p1.setLabel("left", "u_new" if preg_enabled else "u")
            p2.plot(t, e_ident, pen=pg.mkPen("r", width=lw), name="e = y - y_n")
            p2.setLabel("left", "e = y - y_n")
            for plot in (p0, p1):
                plot.getAxis("bottom").setStyle(showValues=False)
                plot.getAxis("bottom").setLabel("")
            p2.getAxis("bottom").setStyle(showValues=True)
            p2.setLabel("bottom", f"time [s], dt MPC = {dt:g} s")

            epochs = np.asarray(z.get("training_epochs", []), dtype=float).reshape(-1)
            rmse = np.asarray(z.get("training_rmse", []), dtype=float).reshape(-1)
            weight_history = np.asarray(z.get("training_weight_history", []), dtype=float)
            if weight_history.ndim == 1 and weight_history.size:
                weight_history = weight_history[None, :]
            theta_final = np.asarray(z.get("theta", z.get("w", [])), dtype=float).reshape(-1)
            show_weight_history = False
            show_constant_weights = False
            show_rmse_history = False
            if use_epoch_diagnostics:
                show_weight_history = weight_history.ndim == 2 and weight_history.size and epochs.size
                show_rmse_history = rmse.size and epochs.size
            else:
                if theta_final.size == 0 and weight_history.ndim == 2 and weight_history.size:
                    theta_final = np.asarray(weight_history[-1], dtype=float).reshape(-1)
                show_constant_weights = theta_final.size > 0
            w0.setVisible(show_weight_history or show_constant_weights)
            w1.setVisible(show_rmse_history)
            if show_weight_history:
                n_epochs = min(epochs.size, weight_history.shape[0])
                for j in range(weight_history.shape[1]):
                    color = pg.intColor(j, hues=max(8, weight_history.shape[1]), values=1, maxValue=220)
                    w0.plot(epochs[:n_epochs], weight_history[:n_epochs, j],
                            pen=pg.mkPen(color, width=max(1.0, lw * 0.8)))
                w0.setLabel("left", "w", **{"font-weight": "bold"})
                w0.getAxis("bottom").setStyle(showValues=False)
                w0.getAxis("bottom").setLabel("")
            elif show_constant_weights:
                k_axis = np.arange(1, t.size + 1, dtype=float)
                for j in range(theta_final.size):
                    color = pg.intColor(j, hues=max(8, theta_final.size), values=1, maxValue=220)
                    w0.plot(k_axis, np.full(k_axis.shape, float(theta_final[j]), dtype=float),
                            pen=pg.mkPen(color, width=max(1.0, lw * 0.8)))
                w0.setLabel("left", "w", **{"font-weight": "bold"})
                w0.setLabel("bottom", "k [sample]")
            if show_rmse_history:
                n_rmse = min(epochs.size, rmse.size)
                w1.plot(epochs[:n_rmse], rmse[:n_rmse], pen=pg.mkPen("r", width=lw),
                        symbol="o", symbolSize=max(3.0, 1.5 * lw))
                w1.setLabel("left", "RMSE")
                w1.setLabel("bottom", "epoch")

            rho_aw_values = np.asarray(z.get("rho_aw", []), dtype=float).reshape(-1)
            rho_ay_values = np.asarray(z.get("rho_ay", []), dtype=float).reshape(-1)
            finite_aw = rho_aw_values[np.isfinite(rho_aw_values)]
            finite_ay = rho_ay_values[np.isfinite(rho_ay_values)]
            show_aw = use_epoch_diagnostics and finite_aw.size > 0
            show_ay = finite_ay.size > 0
            if use_epoch_diagnostics:
                # L-M rho(A_w) is indexed by epoch, while rho(A_y) is indexed
                # by prediction sample k. Their x axes must remain independent.
                r0.setVisible(show_aw)
                r1.setVisible(show_ay)
                ay_plot = r1
                try:
                    r0.setXLink(None)
                    r0.getViewBox().setXLink(None)
                    r1.setXLink(None)
                    r1.getViewBox().setXLink(None)
                except Exception:
                    pass
                if show_aw:
                    rho_x_aw = np.arange(1, rho_aw_values.size + 1, dtype=float)
                    mask_aw = np.isfinite(rho_aw_values)
                    r0.plot(rho_x_aw[mask_aw], rho_aw_values[mask_aw], pen=pg.mkPen("b", width=lw),
                            symbol="o", symbolSize=max(4.0, 1.5 * lw))
                    r0.setLabel("left", "rho(A_w(epoch))")
                    r0.setLabel("bottom", "epoch")
                    r0.getAxis("bottom").setStyle(showValues=True)
            else:
                # Batch Ridge has no iterative weight-update dynamics.
                # Use the first plot for rho(A_y(k)) and suppress rho(A_w)
                # completely instead of leaving an empty upper graph.
                r0.setVisible(show_ay)
                r1.setVisible(False)
                ay_plot = r0
            if show_ay:
                rho_x_ay = np.arange(1, rho_ay_values.size + 1, dtype=float)
                mask_ay = np.isfinite(rho_ay_values)
                ay_plot.plot(rho_x_ay[mask_ay], rho_ay_values[mask_ay], pen=pg.mkPen("k", width=lw))
                ay_plot.setLabel("left", "rho(A_y(k))")
                ay_plot.setLabel("bottom", "k")
                ay_plot.getAxis("bottom").setStyle(showValues=True)

            if str(honu_name).upper() == "MLP":
                learning_name = {
                    "adam": "Adam",
                    "lbfgs": "L-BFGS",
                    "adam_lbfgs": "Adam + L-BFGS",
                }.get(learning_key, str(learning_key))
            else:
                learning_name = "L-M" if learning_key == "lm" else "RIDGE"
            self.tab_titles[self.tabs.widget(0)].setText(
                f'{plant_title} | batch identification of {honu_name} Plant HONU | {learning_name} | {plant_mode_text} | dt MPC = {dt:g} s',
                color='#183b73', size='12pt', bold=True)
            self.tab_titles[self.tabs.widget(1)].setText(
                "HONU weights w over epochs" if use_epoch_diagnostics else "HONU weights w over k",
                color="#183b73", size="12pt", bold=True)
            self.tab_titles[self.tabs.widget(2)].setText(
                "Spectral radii of identified HONU Plant",
                color="#183b73", size="12pt", bold=True)
        elif result_mode == "simulate":
            # Standalone plant simulation is not a closed loop. Show the dense
            self.tabs.setTabText(0, "measured data")
            self.btn_result_simulation.setText("1. Measured dataset")
            t_curve = np.asarray(z.get("t", t), dtype=float)
            y_sim = np.asarray(z.get("y_sim", z["y"]), dtype=float)
            u_sim = np.asarray(z.get("u_sim", z["u"]), dtype=float)
            t_mpc = np.asarray(z.get("t_mpc", []), dtype=float)
            y_mpc = np.asarray(z.get("y_mpc", []), dtype=float)
            p0.plot(t_curve, y_sim, pen=pg.mkPen("g", width=lw), name="y")
            if t_mpc.size and y_mpc.size:
                point_size = max(1.0, 1.5 * lw)
                point_edge_width = max(0.35, 0.3 * lw)
                p0.plot(t_mpc, y_mpc, pen=None, symbol="o", symbolSize=point_size,
                        symbolPen=pg.mkPen("b", width=point_edge_width),
                        symbolBrush=pg.mkBrush("b"), name="y(dt_MPC)")
            p0.setLabel("left", "y")
            self.tab_titles[self.tabs.widget(0)].setText(
                f'{plant_title} | measured data | {plant_mode_text} | dt MPC = {dt:g} s',
                color='#183b73', size='12pt', bold=True)
            p1.plot(t_curve, u_sim, pen=pg.mkPen("b", width=lw)); p1.setLabel("left", "u_new" if preg_enabled else "u")
            p1.getAxis("bottom").setStyle(showValues=True)
            p1.setLabel("bottom", f"time [s], dt MPC = {dt:g} s")
            p2.hide(); w0.hide(); w1.hide(); r0.hide(); r1.hide()
        else:
            self.tabs.setTabText(0, "Closed loop")
            frozen_mode = result_mode == "mpc_frozen"
            self.btn_result_frozen.setText("3.1 MPC - Frozen HONU")
            self.btn_result_mpc.setText("3.2 MPC - Sliding Retraining")
            p2.show(); w0.show(); w1.hide(); r0.hide(); r1.show()
            p1.getAxis("bottom").setStyle(showValues=False)
            p1.getAxis("bottom").setLabel("")
            p0.plot(t,z["d"],pen=pg.mkPen("k",width=max(1.0,lw*0.75),style=Qt.DotLine),name="d")
            p0.plot(t,z["ym"],pen=pg.mkPen("b",width=lw),name="y_ref")
            p0.plot(t,z["y"],pen=pg.mkPen("g",width=lw),name="y")
            p0.setLabel("left","d, y_ref, y")
            self.tab_titles[self.tabs.widget(0)].setText(
                f'{plant_title} | {honu_name} ' + ('batch-trained frozen HONU MPC' if result_mode == 'mpc_frozen' else 'sliding-retraining HONU MPC') + f' | {plant_mode_text} | dt MPC = {dt:g} s | Np = {horizon_text}',
                color='#183b73', size='12pt', bold=True)
            p1.plot(t,z["u"],pen=pg.mkPen("b",width=lw)); p1.setLabel("left","u_new" if preg_enabled else "u")
            p2.plot(t,z["e"],pen=pg.mkPen("r",width=lw)); p2.setLabel("left","e = y_ref - y"); p2.setLabel("bottom",f"time [s], dt MPC = {dt:g} s")
        if result_mode in {"mpc_frozen", "mpc_sliding"}:
            w=np.asarray(z["w"], dtype=float)
            if w.ndim == 1:
                w = w[:, None]
            for j in range(w.shape[1]):
                mask=np.isfinite(w[:,j])
                if np.any(mask):
                    color=pg.intColor(j,hues=max(8,w.shape[1]),values=1,maxValue=220)
                    w0.plot(t[mask],w[mask,j],pen=pg.mkPen(color,width=max(1.0,lw*0.8)))
                if j % 8 == 7:
                    QApplication.processEvents()
            weights_title = ("Frozen batch HONU coefficients in fixed PCA basis" if result_mode == "mpc_frozen" else "Sliding-retraining HONU coefficients in fixed PCA basis")
            self.tab_titles[self.tabs.widget(1)].setText(weights_title, color="#183b73", size="12pt", bold=True)
            w0.setLabel("left", "w", **{"font-weight": "bold"})
            w0.setLabel("bottom", f"time [s], dt update = {dt:g} s")

            rho_ay_values = np.asarray(z.get("rho_ay", []), dtype=float).reshape(-1)
            rho_x_ay = t[:rho_ay_values.size]
            rho_bottom_label = f"time [s], dt update = {dt:g} s"
            rho_title = ("Frozen HONU Plant spectral radius" if result_mode == "mpc_frozen"
                         else "Sliding-retraining HONU Plant spectral radius")
            finite_ay = rho_ay_values[np.isfinite(rho_ay_values)]
            r0.setVisible(False)
            self.tab_titles[self.tabs.widget(2)].setText(rho_title, color="#183b73", size="12pt", bold=True)
            r1.setVisible(finite_ay.size > 0)
            if finite_ay.size:
                mask_ay = np.isfinite(rho_ay_values)
                r1.plot(rho_x_ay[mask_ay], rho_ay_values[mask_ay], pen=pg.mkPen("k", width=lw))
            line = pg.InfiniteLine(pos=1.0, angle=0, pen=pg.mkPen("#666666", width=1, style=Qt.DashLine))
            r1.addItem(line)
            r1.setLabel("left", "rho(A_y(k))")
            r1.setLabel("bottom", rho_bottom_label)
        if update_log and "pca_rank" in z:
            rank=int(np.asarray(z["pca_rank"]).reshape(-1)[0])
            raw=int(np.asarray(z["pca_raw_feature_count"]).reshape(-1)[0])
            selected=int(np.asarray(z.get("pca_selected_components", [rank])).reshape(-1)[0])
            model_features=int(np.asarray(z.get("model_feature_count", [selected + 1])).reshape(-1)[0])
            mode_value=np.asarray(z.get("pca_selection_mode", ["rank"])).reshape(-1)[0]
            if isinstance(mode_value, bytes): mode_value=mode_value.decode("utf-8", errors="replace")
            mode=str(mode_value).capitalize()
            self.status.append(f"PCA_rank={rank}; PCA_used={selected}; HONU_features={model_features}")
            self.status.append(f"PCA_mode={mode}")
            if mode.lower() == "variability":
                target=float(np.asarray(z.get("pca_target_variability", [1.0])).reshape(-1)[0])*100.0
                actual=float(np.asarray(z.get("pca_retained_variability", [1.0])).reshape(-1)[0])*100.0
                self.status.append(
                    f"PCA variability: target={target:.4g}%; used_components={selected}; retained={actual:.6g}%"
                )

        if preserve_view:
            for widget, plots in self.tab_plots.items():
                for plot, view_range in zip(plots, saved_view_ranges.get(widget, [])):
                    if view_range is None:
                        continue
                    try:
                        plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
                        plot.setRange(xRange=view_range[0], yRange=view_range[1], padding=0.0)
                        plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
                    except Exception:
                        pass
        else:
            # Capture deterministic reset ranges after all data have been drawn.
            for widget, plots in self.tab_plots.items():
                stored_ranges = []
                for plot in plots:
                    try:
                        plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
                        plot.autoRange()
                        view_range = plot.getViewBox().viewRange()
                        stored_ranges.append([list(view_range[0]), list(view_range[1])])
                        plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=False)
                        plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)
                    except Exception:
                        stored_ranges.append(None)
                self._initial_plot_ranges[widget] = stored_ranges


class MainWindow(QMainWindow):
    @staticmethod
    def _top_label_text(text):
        return text

    def __init__(self):
        super().__init__()
        self.process = None
        self.run_start_time = None
        self.current_file = None
        self.last_requested_output_file = None
        self.active_output_kind = "01"
        self.plots = []
        self.base_plot = None
        self.tab_plots = {}
        self.initial_ranges = {}
        self.fixed_y_ranges = {}
        self.line_width = line_width_from_setup(2)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.25, 10.0)
        self.line_width_spin.setDecimals(2)
        self.line_width_spin.setSingleStep(0.25)
        self.line_width_spin.setFixedWidth(76)
        self.line_width_spin.setAlignment(Qt.AlignRight)
        self.line_width_spin.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.line_width_spin.setKeyboardTracking(False)
        self.line_width_spin.setValue(float(self.line_width))
        self.line_width_spin.setToolTip("Line width in pixels. Use the compact step buttons, mouse wheel, or direct numeric entry. Changes are applied immediately.")
        self.font_size = font_size_from_setup(10)
        self._loading_setup = False
        self._last_honu_plant = None
        self.plant_parameter_cache = {}
        self._last_controller_model = None
        self.controller_parameter_cache = {}
        self.measured_y_bounds = None
        self.running_script_name = None
        self.running_expected_outputs = []
        self.running_output_snapshot = {}
        self.running_output_kind = None
        self.running_setup_snapshot = None
        self.output_run_metadata = {}
        # Backward-compatible alias to the application-level comparison-window
        # registry. The lifetime of these windows is independent of MainWindow.
        self.full_screen_plot_windows = COMPARISON_PLOT_WINDOWS
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(180)
        self._autosave_timer.timeout.connect(self.auto_apply_settings)

        self.setWindowTitle(APP_TITLE.replace("Simulated", "Measured").replace("simulated", "measured"))
        self.resize(1900, 1000)
        self.setMinimumSize(1450, 800)

        self._build_menu()
        self._build_ui()
        self.load_metadata_from_setup()
        self._build_timer()
        self.refresh_file_list()
        # After a module finishes, reload the output that belongs to the action
        # that started it. Do not fall back to 01; that made the plots look stale.
        self.set_active_output(self.active_output_kind, load=True)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def show_about(self):
        about_path = BASE_DIR.parents[1] / "ABOUT.txt"
        try:
            about_text = about_path.read_text(encoding="utf-8").strip()
        except OSError:
            about_text = "HONU MRAC Laboratory"
        QMessageBox.information(self, "About", about_text)

    def _build_menu(self):
        menu_file = self.menuBar().addMenu("File")

        action_open_setup = QAction("Open project_setup.py", self)
        action_open_setup.triggered.connect(self.open_project_setup)
        menu_file.addAction(action_open_setup)

        action_open_folder = QAction("Open project folder", self)
        action_open_folder.triggered.connect(lambda: open_file_with_system(BASE_DIR))
        menu_file.addAction(action_open_folder)

        menu_file.addSeparator()

        action_reload = QAction("Reload selected output", self)
        action_reload.triggered.connect(self.load_selected_output)
        menu_file.addAction(action_reload)

        menu_file.addSeparator()

        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.close)
        menu_file.addAction(action_exit)

        menu_tools = self.menuBar().addMenu("Tools")

        action_install = QAction("Install GUI dependencies", self)
        action_install.triggered.connect(self.install_dependencies)
        menu_tools.addAction(action_install)

        action_clear_log = QAction("Clear log", self)
        action_clear_log.triggered.connect(self.clear_log)
        menu_tools.addAction(action_clear_log)

        menu_view = self.menuBar().addMenu("View")

        action_autorange = QAction("Auto range plots", self)
        action_autorange.triggered.connect(self.auto_range_all)
        menu_view.addAction(action_autorange)

        menu_help = self.menuBar().addMenu("Help")
        action_documentation = QAction("Open built documentation", self)
        action_documentation.triggered.connect(self.open_built_documentation)
        menu_help.addAction(action_documentation)
        menu_help.addSeparator()
        action_about = QAction("About", self)
        action_about.triggered.connect(self.show_about)
        menu_help.addAction(action_about)

    def open_built_documentation(self):
        index_path = BASE_DIR.parents[1] / "documentation" / "_build" / "html" / "index.html"
        if not index_path.is_file():
            QMessageBox.warning(
                self,
                "Documentation",
                f"Built documentation was not found:\n{index_path}\n\nBuild it with Sphinx first.",
            )
            return
        open_file_with_system(index_path)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(8)
        self.main_mode_tabs = QTabWidget()
        self.main_mode_tabs.setDocumentMode(True)
        outer_layout.addWidget(self.main_mode_tabs)

        mrac_page = QWidget()
        root_layout = QHBoxLayout(mrac_page)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        self.left_panel = self._make_left_panel()
        self.left_panel.setFixedWidth(385)
        root_layout.addWidget(self.left_panel)

        work_area = QWidget()
        work_layout = QVBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(8)
        work_layout.addWidget(self._make_top_panel())

        self.graph_tabs = QTabWidget()
        self.graph_tabs.setDocumentMode(True)
        self.graph_tabs.setTabsClosable(False)
        self.graph_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_widget = None
        work_layout.addWidget(self.graph_tabs, stretch=1)
        root_layout.addWidget(work_area, stretch=1)

        self.measured_page = MeasuredDataPage(BASE_DIR, BASE_DIR / "project_setup.py", self)
        self.measured_page.btn_back.setText("Continue to MRAC / MPC")
        self.measured_page.backRequested.connect(self._return_from_measured_data)
        self.measured_page.datasetExported.connect(self._on_measured_dataset_exported)
        self.main_mode_tabs.addTab(self.measured_page, "Measured data")

        self.main_mode_tabs.addTab(mrac_page, "HONU MRAC")
        self.mpc_page = HONUMPCPage(self)
        self.main_mode_tabs.addTab(self.mpc_page, "HONU MPC")
        self.main_mode_tabs.currentChanged.connect(self._on_main_mode_tab_changed)
        self.main_mode_tabs.setCurrentWidget(self.measured_page)
        meta_path = BASE_DIR / "data" / "data_uy.txt.runmeta.json"
        if meta_path.exists() and (BASE_DIR / "data_uy.txt").exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                self._set_active_dataset_status(meta)
                self._initialize_controller_dt_from_dataset(meta)
            except Exception:
                pass

    def _on_main_mode_tab_changed(self, index):
        if getattr(self, "mpc_page", None) is not None and self.main_mode_tabs.widget(index) is self.mpc_page:
            self.mpc_page.refresh_measured_dataset_preview(show_errors=False)

    def _return_from_measured_data(self):
        target = getattr(self, "_measured_return_tab", 1)
        if target == self.main_mode_tabs.indexOf(self.measured_page):
            target = 1
        self.main_mode_tabs.setCurrentIndex(target)

    def _open_measured_data_workspace(self):
        self._measured_return_tab = self.main_mode_tabs.currentIndex()
        self.main_mode_tabs.setCurrentWidget(self.measured_page)
        self.measured_page.open_data_file()

    def _set_active_dataset_status(self, meta):
        source_file = Path(str(meta.get("source_file", "")))
        source_name = source_file.name if source_file.name else "measured dataset"
        channel_u = str(meta.get("channel_u", "u"))
        channel_y = str(meta.get("channel_y", "y"))
        samples = int(meta.get("samples", 0))
        dt = float(meta.get("dt", float("nan")))
        text = f"{source_name} | u={channel_u}, y={channel_y} | N={samples} | dt={dt:g} s"
        for owner in (self, getattr(self, "mpc_page", None)):
            combo = getattr(owner, "physical_model_combo", None) if owner is not None else None
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(text, "measured")
            combo.setToolTip(str(source_file) if str(source_file) else text)
            combo.blockSignals(False)

    def _initialize_controller_dt_from_dataset(self, meta):
        dataset_dt = float(meta.get("dt", float("nan")))
        if not np.isfinite(dataset_dt) or dataset_dt <= 0.0:
            return
        self.dt_mrac_spin.blockSignals(True)
        self.dt_mrac_spin.setValue(dataset_dt)
        self.dt_mrac_spin.blockSignals(False)
        if getattr(self, "mpc_page", None) is not None:
            self.mpc_page.dt_mpc_spin.blockSignals(True)
            self.mpc_page.dt_mpc_spin.setValue(dataset_dt)
            self.mpc_page.dt_mpc_spin.blockSignals(False)

    def _on_measured_dataset_exported(self, _path):
        self.invalidate_downstream_artifacts_after_module01()
        try:
            self.set_active_output("01", load=True)
        except Exception as exc:
            self.append_log(f"Measured-data plot warning: {exc}")
        try:
            meta = json.loads((BASE_DIR / "data" / "data_uy.txt.runmeta.json").read_text(encoding="utf-8"))
            self._set_active_dataset_status(meta)
            self._initialize_controller_dt_from_dataset(meta)
            if getattr(self, "mpc_page", None) is not None:
                self.mpc_page.refresh_measured_dataset_preview(show_errors=False)
            # The measured-data workspace owns source selection and the base dataset only.
            # MRAC/MPC controls do not constrain loading or resampling.
            self.append_log(
                f"MEASURED DATA ACTIVE: {Path(meta['source_file']).name}; "
                f"u={meta.get('channel_u','u')}; y={meta.get('channel_y','y')}; "
                f"interval=[{meta.get('selection_t_start',meta['t_start']):.6g}, "
                f"{meta.get('selection_t_stop',meta['t_stop']):.6g}] s; "
                f"samples={meta['samples']}; dt={meta['dt']:.6g} s"
            )
        except Exception as exc:
            self.append_log(f"Measured dataset activated, metadata read warning: {exc}")
        self.refresh_file_list()

    def _make_top_panel(self):
        panel = QFrame()
        panel.setObjectName("topPanel")
        panel.setFrameShape(QFrame.StyledPanel)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(10, 7, 10, 8)
        outer.setSpacing(7)

        selector_layout = QHBoxLayout()
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.setSpacing(9)

        self.physical_model_combo = QComboBox()
        self.physical_model_combo.addItem("No active dataset", "")
        self.physical_model_combo.setEnabled(False)

        # Independent MRAC sampling period. It is initialized from the active
        # measured dataset, then remains user-adjustable in the MRAC panel.
        self.dt_mrac_spin = SelectAllDoubleSpinBox()
        self.dt_mrac_spin.setRange(1.0e-6, 1000.0)
        self.dt_mrac_spin.setDecimals(6)
        self.dt_mrac_spin.setSingleStep(0.01)
        self.dt_mrac_spin.setFixedWidth(78)
        self.dt_mrac_spin.setAlignment(Qt.AlignLeft)
        self.dt_mrac_spin.setKeyboardTracking(False)
        self.dt_mrac_spin.setToolTip("MRAC sampling period [s]. Initialized from the active measured dataset and independently adjustable.")
        # Compatibility alias for existing MRAC computation code.
        self.dt_spin = self.dt_mrac_spin

        self.plant_model_combo = QComboBox()
        for value in PLANT_APPROXIMATION_MODELS:
            self.plant_model_combo.addItem(value, value)

        self.controller_model_combo = QComboBox()
        for value in CONTROLLER_MODELS:
            self.controller_model_combo.addItem(value, value)

        self.learning_combo = QComboBox()
        self.learning_combo.addItem("Batch / Ridge", "batch")
        self.learning_combo.addItem("Levenberg-Marquardt", "LM")
        self.learning_combo.addItem("GD", "GD")
        self.learning_combo.addItem("NGD", "NGD")

        self.controller_learning_combo = QComboBox()
        for value in CONTROLLER_LEARNING_ALGORITHMS:
            self.controller_learning_combo.addItem(value, value)

        self.reference_combo = QComboBox()
        for label, value in REFERENCE_TYPES.items():
            self.reference_combo.addItem(label, value)
        self.reference_combo.setToolTip(
            "For Alternating/Random, this selector controls both the step-1 plant excitation u "
            "and the step-3/4 reference d. Alternating steps are deterministic: after the initial block "
            "they switch d_max, d_min, d_max, ... . Random steps are the only random "
            "mode. Plant input replays the step-1 excitation."
        )

        def add_top_selector(label, combo, width):
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(2)
            lab = QLabel(self._top_label_text(label))
            lab.setObjectName("topLabel")
            lab.setToolTip(label)
            lab.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
            combo.setMinimumWidth(width)
            v.addWidget(lab)
            v.addWidget(combo)
            selector_layout.addWidget(box)

        add_top_selector("active dataset", self.physical_model_combo, 300)

        dt_box = QWidget()
        dt_layout = QVBoxLayout(dt_box)
        dt_layout.setContentsMargins(0, 0, 0, 0)
        dt_layout.setSpacing(2)
        dt_label = QLabel("dt_MRAC [sec]")
        dt_label.setObjectName("topLabel")
        dt_layout.addWidget(dt_label)
        dt_layout.addWidget(self.dt_mrac_spin)
        selector_layout.addWidget(dt_box)

        for label, combo, width in (
            ("HONU plant", self.plant_model_combo, 72),
            ("controller", self.controller_model_combo, 72),
            ("plant learning", self.learning_combo, 125),
            ("controller learning", self.controller_learning_combo, 68),
            ("excitation u / reference d", self.reference_combo, 92),
        ):
            add_top_selector(label, combo, width)

        self.btn_full_screen = QPushButton("Full screen")
        self.btn_full_screen.setMinimumWidth(100)
        self.btn_full_screen.setToolTip("Open an independent movable and resizable comparison window.")
        self.btn_full_screen.clicked.connect(self.open_current_graph_full_screen)

        # Use the same two-row geometry as the neighbouring selector widgets.
        # The empty top-label row aligns the button with the combo-box row.
        full_screen_box = QWidget()
        full_screen_layout = QVBoxLayout(full_screen_box)
        full_screen_layout.setContentsMargins(0, 0, 0, 0)
        full_screen_layout.setSpacing(2)
        full_screen_placeholder = QLabel(" ")
        full_screen_placeholder.setObjectName("topLabel")
        full_screen_layout.addWidget(full_screen_placeholder)
        full_screen_layout.addWidget(self.btn_full_screen, 0, Qt.AlignHCenter)

        line_width_box = QWidget()
        line_width_layout = QVBoxLayout(line_width_box)
        line_width_layout.setContentsMargins(0, 0, 0, 0)
        line_width_layout.setSpacing(2)
        line_width_label = QLabel("line width [px]")
        line_width_label.setObjectName("topLabel")
        line_width_layout.addWidget(line_width_label)
        line_width_layout.addWidget(self.line_width_spin)
        selector_layout.addWidget(line_width_box)

        selector_layout.addWidget(full_screen_box)

        selector_layout.addStretch(1)
        outer.addLayout(selector_layout)

        def int_spin(minimum=1, maximum=100000, step=1, width=72):
            spin = QSpinBox()
            spin.setRange(minimum, maximum)
            spin.setSingleStep(step)
            spin.setFixedWidth(min(int(width), 72))
            spin.setAlignment(Qt.AlignLeft)
            return spin

        def double_spin(minimum, maximum, decimals, step, width=78):
            spin = SelectAllDoubleSpinBox()
            spin.setRange(minimum, maximum)
            spin.setDecimals(max(4, decimals))
            spin.setSingleStep(step)
            spin.setFixedWidth(min(int(width), 78))
            spin.setAlignment(Qt.AlignLeft)
            spin.setKeyboardTracking(False)
            return spin

        self.plant_n_y_spin = int_spin(width=100)
        self.plant_n_u_spin = int_spin(width=100)
        self.tau_u_spin = double_spin(0.0, 10000.0, 6, 0.1, 145)
        self.plant_epochs_spin = int_spin(width=150)
        self.mu_w_spin = double_spin(0.0, 1.0e9, 10, 0.01, 165)
        self.plant_lambda_spin = double_spin(0.0, 1.0e9, 10, 0.0001, 185)

        self.controller_epochs_spin = int_spin(width=120)
        self.mu_v_spin = double_spin(0.0, 1.0e9, 10, 0.001, 170)
        self.mu_r0_spin = double_spin(0.0, 1.0e9, 10, 0.001, 170)
        self.alpha_v_spin = double_spin(0.0, 1.0, 6, 0.05, 135)
        self.alpha_r0_spin = double_spin(0.0, 1.0, 6, 0.05, 135)
        self.r0_init_spin = double_spin(-1.0e6, 1.0e6, 8, 0.1, 145)
        self.tau_1_spin = double_spin(1.0e-6, 10000.0, 6, 0.1, 145)
        self.tau_2_spin = double_spin(1.0e-6, 10000.0, 6, 0.1, 145)
        self.tau_d_spin = double_spin(0.0, 10000.0, 6, 0.1, 145)
        self.tau_u_spin.setToolTip("Input switching period tau_u [s]. Linked bidirectionally with tau_d.")
        self.tau_d_spin.setToolTip("Reference switching period tau_d [s]. Linked bidirectionally with tau_u.")
        # Nine decimals and an adaptive step are used because some plants have
        # output ranges much smaller than 0.1. The range is tightened to the
        # measured y2 interval after data_uy.txt becomes available.
        self.d_min_spin = double_spin(-1.0e12, 1.0e12, 9, 0.01, 160)
        self.d_max_spin = double_spin(-1.0e12, 1.0e12, 9, 0.01, 160)
        self.u_min_spin = double_spin(-1.0e12, 1.0e12, 9, 0.1, 145)
        self.u_max_spin = double_spin(-1.0e12, 1.0e12, 9, 0.1, 145)
        self.u_min_spin.setToolTip("Minimum excitation-signal value used only in module 01. Controller u in modules 03/04 is unrestricted.")
        self.u_max_spin.setToolTip("Maximum excitation-signal value used only in module 01. Controller u in modules 03/04 is unrestricted.")

        self.t_end_spin = double_spin(0.01, 1.0e7, 3, 10.0, 145)
        self.step_hold_spin = double_spin(1.0e-6, 1.0e7, 6, 0.1, 145)
        self.reference_duration_spin = double_spin(1.0e-6, 1.0e7, 6, 1.0, 145)
        self.reference_step_hold_spin = double_spin(1.0e-6, 1.0e7, 6, 0.1, 145)
        self.preg_enabled_check = QCheckBox("Use P regulator")
        self.preg_enabled_check.setToolTip(
            "Enable the inner P-regulated plant black box. Clear the checkbox to use the original plant."
        )
        self.r_preg_spin = double_spin(-1.0e6, 1.0e6, 8, 0.05, 145)
        self.r_preg_spin.setToolTip("Inner P-controller gain r_Preg. Used only in 'With P regulator' mode.")
        self.reference_duration_spin.setToolTip("Total duration of reference d used by modules 03 and 04 [s].")
        self.reference_step_hold_spin.setToolTip("Duration of one constant level of reference d [s]. Rounded to an integer number of dt MRAC samples.")
        self.dt_spin.setToolTip("Sampling period used by generated data, HONU identification, and MRAC [s].")
        parameters_group = QGroupBox("MRAC parameters")
        grid = QGridLayout(parameters_group)
        grid.setContentsMargins(10, 9, 10, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)

        simulation_fields = (
            ("test duration [s]", self.t_end_spin),
            ("u step width [s]", self.step_hold_spin),
            ("tau_u [s]", self.tau_u_spin),
            ("dt MRAC [s]", self.dt_spin),
            ("u_min", self.u_min_spin),
            ("u_max", self.u_max_spin),
            ("P regulator", self.preg_enabled_check),
            ("r_Preg", self.r_preg_spin),
        )
        reference_fields = (
            ("d duration [s]", self.reference_duration_spin),
            ("d step width [s]", self.reference_step_hold_spin),
            ("tau_d [s]", self.tau_d_spin),
            ("tau_1 [s]", self.tau_1_spin),
            ("tau_2 [s]", self.tau_2_spin),
            ("d_min", self.d_min_spin),
            ("d_max", self.d_max_spin),
        )
        plant_fields = (
            ("n_y", self.plant_n_y_spin),
            ("n_u", self.plant_n_u_spin),
            ("epochs", self.plant_epochs_spin),
            ("mu_w", self.mu_w_spin),
            ("lambda", self.plant_lambda_spin),
        )
        controller_learning_fields = (
            ("epochs", self.controller_epochs_spin),
            ("mu_v", self.mu_v_spin),
            ("mu_(r_0)", self.mu_r0_spin),
            ("alpha_v", self.alpha_v_spin),
            ("alpha_(r_0)", self.alpha_r0_spin),
            ("r_(0,init)", self.r0_init_spin),
        )

        def add_parameter_row(row, row_title, fields):
            grid.addWidget(QLabel(row_title), row, 0, alignment=Qt.AlignLeft | Qt.AlignVCenter)
            for col, (label, widget) in enumerate(fields, start=1):
                box = QWidget()
                v = QVBoxLayout(box)
                v.setContentsMargins(0, 0, 0, 0)
                v.setSpacing(1)
                lab = QLabel(label)
                lab.setObjectName("parameterLabel")
                lab.setToolTip(label)
                v.addWidget(lab)
                v.addWidget(widget)
                grid.addWidget(box, row, col)

        add_parameter_row(0, "Reference d", reference_fields)
        add_parameter_row(1, "Plant HONU", plant_fields)
        add_parameter_row(2, "Controller\nlearning", controller_learning_fields)

        self.reference_range_label = QLabel(
            "Reference d range: load and activate measured data first"
        )
        self.reference_range_label.setObjectName("parameterLabel")
        self.reference_range_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.reference_range_label.setToolTip(
            "The reference range is constrained by the active measured output y in data_uy.txt."
        )
        grid.addWidget(self.reference_range_label, 3, 1, 1, 7)

        for col in range(1, 8):
            grid.setColumnStretch(col, 1)
        outer.addWidget(parameters_group)

        self.plant_model_combo.currentIndexChanged.connect(self.on_honu_plant_changed)
        self.controller_model_combo.currentIndexChanged.connect(self.on_controller_model_changed)
        self.learning_combo.currentIndexChanged.connect(self.on_metadata_changed)
        self.controller_learning_combo.currentIndexChanged.connect(self.on_parameter_changed)
        self.reference_combo.currentIndexChanged.connect(self.on_parameter_changed)

        for widget in (
            self.plant_n_y_spin,
            self.plant_n_u_spin,
            self.tau_u_spin,
            self.plant_epochs_spin,
            self.mu_w_spin,
            self.plant_lambda_spin,
            self.controller_epochs_spin,
            self.mu_v_spin,
            self.mu_r0_spin,
            self.alpha_v_spin,
            self.alpha_r0_spin,
            self.r0_init_spin,
            self.tau_1_spin,
            self.tau_2_spin,
            self.tau_d_spin,
            self.d_min_spin,
            self.d_max_spin,
            self.dt_spin,
            self.t_end_spin,
            self.step_hold_spin,
            self.reference_duration_spin,
            self.reference_step_hold_spin,
            self.r_preg_spin,
        ):
            widget.valueChanged.connect(self.on_parameter_changed)
        # Keep the plant-input and desired-reference switching periods identical.
        # Signal blocking prevents recursive updates while preserving bidirectional editing.
        self.tau_u_spin.valueChanged.connect(self._sync_tau_d_from_tau_u)
        self.tau_d_spin.valueChanged.connect(self._sync_tau_u_from_tau_d)
        self.line_width_spin.valueChanged.connect(self.on_line_width_changed)
        self.preg_enabled_check.toggled.connect(self.on_preg_mode_changed)
        return panel

    def _sync_tau_d_from_tau_u(self, value):
        if abs(float(self.tau_d_spin.value()) - float(value)) <= 1.0e-12:
            return
        self.tau_d_spin.blockSignals(True)
        try:
            self.tau_d_spin.setValue(float(value))
        finally:
            self.tau_d_spin.blockSignals(False)
        self.on_parameter_changed()

    def _sync_tau_u_from_tau_d(self, value):
        if abs(float(self.tau_u_spin.value()) - float(value)) <= 1.0e-12:
            return
        self.tau_u_spin.blockSignals(True)
        try:
            self.tau_u_spin.setValue(float(value))
        finally:
            self.tau_u_spin.blockSignals(False)
        self.on_parameter_changed()

    def preg_mode_enabled(self):
        return self.preg_enabled_check.isChecked()

    def on_preg_mode_changed(self, *_args):
        enabled = self.preg_mode_enabled()
        self.r_preg_spin.setEnabled(enabled)
        self.on_parameter_changed()

    def _make_left_panel(self):
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        title = QLabel("HONU MRAC")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        setup_group = QGroupBox("Project")
        setup_layout = QVBoxLayout(setup_group)
        self.btn_open_setup = QPushButton("Open project_setup.py")
        self.btn_open_setup.clicked.connect(self.open_project_setup)
        self.btn_folder = QPushButton("Open project folder")
        self.btn_folder.clicked.connect(lambda: open_file_with_system(BASE_DIR))
        setup_layout.addWidget(self.btn_open_setup)
        setup_layout.addWidget(self.btn_folder)
        layout.addWidget(setup_group)

        run_group = QGroupBox("Complete MRAC workflow - measured data")
        run_layout = QVBoxLayout(run_group)
        self.btn_run_data = QPushButton("1. Load measured data")
        self.btn_run_data.clicked.connect(self.run_generate_data)
        self.btn_run_identification = QPushButton("2. Identify HONU plant")
        self.btn_run_identification.clicked.connect(self.run_identification_from_metadata)
        self.btn_run_controller = QPushButton("3. Train controller on HONU plant")
        self.btn_run_controller.clicked.connect(self.run_controller_from_metadata)
        run_layout.addWidget(self.btn_run_data)
        run_layout.addWidget(self.btn_run_identification)
        run_layout.addWidget(self.btn_run_controller)
        layout.addWidget(run_group)

        self.btn_stop = QPushButton("Stop current calculation")
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)

        output_group = QGroupBox("Results")
        output_layout = QGridLayout(output_group)
        output_layout.setContentsMargins(8, 10, 8, 8)
        output_layout.setHorizontalSpacing(6)
        output_layout.setVerticalSpacing(5)
        self.output_combo = QComboBox()
        self.output_combo.currentIndexChanged.connect(self.load_selected_output)
        output_layout.addWidget(self.output_combo, 0, 0, 1, 2)
        self.btn_show_data = QPushButton("Plant data")
        self.btn_show_data.clicked.connect(lambda: self.set_active_output("01", load=True))
        self.btn_show_id = QPushButton("Plant ID")
        self.btn_show_id.clicked.connect(lambda: self.set_active_output("02", load=True))
        self.btn_show_ctrl = QPushButton("Controller training")
        self.btn_show_ctrl.clicked.connect(lambda: self.set_active_output("03train", load=True))
        self.btn_show_eval = QPushButton("Controller evaluation")
        self.btn_show_eval.clicked.connect(lambda: self.set_active_output("04eval", load=True))
        self.btn_refresh = QPushButton("Refresh result")
        self.btn_refresh.clicked.connect(self.load_selected_output)
        output_layout.addWidget(self.btn_show_data, 1, 0)
        output_layout.addWidget(self.btn_show_id, 1, 1)
        output_layout.addWidget(self.btn_show_ctrl, 2, 0)
        output_layout.addWidget(self.btn_show_eval, 2, 1)
        output_layout.addWidget(self.btn_refresh, 3, 0, 1, 2)
        layout.addWidget(output_group)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(8, 10, 8, 8)
        status_layout.setSpacing(4)
        self.status_led = QLabel("● Idle")
        self.status_led.setObjectName("statusIdle")
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(18)
        self.time_label = QLabel("elapsed: 0.0 s")
        self.time_label.hide()
        self.metric_label = QLabel("-")
        self.metric_label.setWordWrap(True)
        self.metric_label.hide()
        status_layout.addWidget(self.status_led)
        status_layout.addWidget(self.progress)
        layout.addWidget(status_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 10, 8, 8)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(70)
        self.log.setMaximumHeight(105)
        self.log.setFont(QFont("Consolas", 8))
        log_layout.addWidget(self.log)
        layout.addWidget(log_group)
        layout.addStretch(1)

        return panel

    def _build_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(400)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def apply_light_style(self):
        pg.setConfigOptions(antialias=True, foreground="k", background="w")
        self.setStyleSheet(
            """
            QMainWindow { background: #f2f5f8; }
            QFrame#leftPanel { background: #ffffff; border: 1px solid #c8d2df; border-radius: 8px; }
            QFrame#topPanel { background: #ffffff; border: 1px solid #c8d2df; border-radius: 8px; }
            QLabel#appTitle { font-size: 18px; font-weight: 700; color: #102a56; }
            QLabel#topLabel { font-size: 8pt; color: #475569; font-weight: 600; }
            QLabel#parameterLabel { font-size: 8pt; color: #334155; font-weight: 600; }
            QGroupBox { font-weight: 600; border: 1px solid #c8d2df; border-radius: 7px; margin-top: 8px; padding-top: 11px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px 0 4px; }
            QPushButton { min-height: 27px; border-radius: 5px; border: 1px solid #9fb0c4; background: #f7f9fc; text-align: center; }
            QPushButton:hover { background: #e8f0fb; }
            QPushButton:pressed { background: #d8e6f7; }
            QMenuBar { background: #f2f5f8; color: #111827; }
            QMenuBar::item { background: transparent; color: #111827; padding: 4px 8px; }
            QMenuBar::item:selected { background: #dbeafe; color: #111827; }
            QMenuBar::item:pressed { background: #bfdbfe; color: #111827; }
            QMenu { background: #ffffff; color: #111827; border: 1px solid #9fb0c4; }
            QMenu::item { background: transparent; color: #111827; padding: 5px 24px 5px 22px; }
            QMenu::item:selected { background: #dbeafe; color: #111827; }
            QMenu::item:disabled { color: #94a3b8; }
            QComboBox { min-height: 25px; border-radius: 4px; border: 1px solid #9fb0c4; padding-left: 5px; background: white; color: #111827; }
            QSpinBox, QDoubleSpinBox { min-height: 25px; border-radius: 4px; border: 1px solid #9fb0c4; padding-left: 5px; background: white; color: #111827; }
            QComboBox QAbstractItemView { background: #ffffff; color: #111827; selection-background-color: #dbeafe; selection-color: #111827; outline: 0; }
            QTextEdit { background: #ffffff; color: #111827; border: 1px solid #c8d2df; border-radius: 6px; }
            QLabel#statusIdle { color: #475569; font-weight: 700; }
            QLabel#statusRunning { color: #166534; font-weight: 700; }
            QLabel#statusError { color: #991b1b; font-weight: 700; }
            QLabel#statusDone { color: #1d4ed8; font-weight: 700; }
            """
        )

    # ------------------------------------------------------------------
    # Metadata and process operations
    # ------------------------------------------------------------------

    def combo_value(self, combo):
        value = combo.currentData()
        if value is None:
            return combo.currentText()
        return value

    def set_combo_value(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return True
        idx = combo.findText(str(value))
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return True
        return False

    def current_honu_plant(self):
        return self.combo_value(self.plant_model_combo)

    def current_controller(self):
        return self.combo_value(self.controller_model_combo)

    def current_learning_algorithm(self):
        return self.combo_value(self.learning_combo)

    def current_controller_learning(self):
        return self.combo_value(self.controller_learning_combo)

    def current_reference_type(self):
        return self.combo_value(self.reference_combo)

    def read_plant_parameters_from_setup(self, honu_plant):
        if honu_plant == "QNU":
            return {
                "mu_w": read_setup_float("plant_qnu_mu_w", 0.03),
                "lambda": read_setup_float("plant_qnu_batch_r_0", 1.0e-2),
            }
        return {
            "mu_w": read_setup_float("mu_w", 0.4),
            "lambda": read_setup_float("plant_batch_r_0", 1.0e-4),
        }

    def capture_plant_widgets(self):
        return {
            "mu_w": float(self.mu_w_spin.value()),
            "lambda": float(self.plant_lambda_spin.value()),
        }

    def load_plant_widgets(self, honu_plant):
        values = self.plant_parameter_cache.get(honu_plant)
        if values is None:
            values = self.read_plant_parameters_from_setup(honu_plant)
            self.plant_parameter_cache[honu_plant] = values
        self.mu_w_spin.setValue(float(values.get("mu_w", 0.03 if honu_plant == "QNU" else 0.4)))
        self.plant_lambda_spin.setValue(float(values.get("lambda", 1.0e-2 if honu_plant == "QNU" else 1.0e-4)))
        if honu_plant == "QNU":
            tip = (
                "QNU uses its own learning rate and Ridge lambda. The defaults are "
                "smaller mu_w and stronger regularization than LNU because the "
                "quadratic feature vector has much higher energy."
            )
        else:
            tip = "LNU-specific learning rate and Ridge lambda."
        self.mu_w_spin.setToolTip(tip)
        self.plant_lambda_spin.setToolTip(tip)

    def read_controller_parameters_from_setup(self, controller):
        if controller == "QNU":
            return {
                "learning": read_setup_string("ctrl_qnu_learning", "NGD"),
                "epochs": read_setup_int("ctrl_qnu_epochs", 100),
                "mu_v": read_setup_float("mu_v_qnu", 0.02),
                "mu_r_0": read_setup_float("mu_r_0_qnu", 0.0005),
                "alpha_v": read_setup_float("alpha_v_qnu", 1.0),
                "alpha_r_0": read_setup_float("alpha_r_0_qnu", 1.0),
            }
        return {
            "learning": read_setup_string("ctrl_learning", "GD"),
            "epochs": read_setup_int("ctrl_epochs", 100),
            "mu_v": read_setup_float("mu_v", 0.01),
            "mu_r_0": read_setup_float("mu_r_0", 0.001),
            "alpha_v": read_setup_float("alpha_v", 1.0),
            "alpha_r_0": read_setup_float("alpha_r_0", 1.0),
        }

    def capture_controller_widgets(self):
        return {
            "learning": self.current_controller_learning(),
            "epochs": int(self.controller_epochs_spin.value()),
            "mu_v": float(self.mu_v_spin.value()),
            "mu_r_0": float(self.mu_r0_spin.value()),
            "alpha_v": float(self.alpha_v_spin.value()),
            "alpha_r_0": float(self.alpha_r0_spin.value()),
        }

    def load_controller_widgets(self, controller):
        values = self.controller_parameter_cache.get(controller)
        if values is None:
            values = self.read_controller_parameters_from_setup(controller)
            self.controller_parameter_cache[controller] = values
        self.set_combo_value(self.controller_learning_combo, values.get("learning", "NGD"))
        self.controller_epochs_spin.setValue(int(values.get("epochs", 100)))
        self.mu_v_spin.setValue(float(values.get("mu_v", 0.01)))
        self.mu_r0_spin.setValue(float(values.get("mu_r_0", 0.001)))
        self.alpha_v_spin.setValue(float(values.get("alpha_v", 1.0)))
        self.alpha_r0_spin.setValue(float(values.get("alpha_r_0", 1.0)))

    def measured_output_path(self):
        """Return the current module-01 data path from project_setup.py."""
        return BASE_DIR / read_setup_string("uy_file", "data_uy.txt")

    def current_data_path(self):
        """Return the active module-01 dataset used by MRAC validation.

        Kept as a dedicated method because the validation pipeline calls it
        after the current widget state has been written to project_setup.py.
        """
        return self.measured_output_path()

    def read_measured_y_bounds(self):
        """Read finite y2 limits used only by the module-04 test reference."""
        path = self.measured_output_path()
        if not path.exists():
            return None

        columns, data = load_table(path)
        y_index = column_index(columns, "y")
        if y_index is None:
            y_index = read_setup_int("reference_measured_y_column", 4)
        if y_index < 0 or y_index >= data.shape[1]:
            raise ValueError(
                f"{path.name} has {data.shape[1]} columns; common controlled-output column y is unavailable"
            )

        y = np.asarray(data[:, y_index], dtype=float)
        y = y[np.isfinite(y)]
        if y.size == 0:
            raise ValueError(f"{path.name}: controlled output y contains no finite samples")
        y_min = float(np.min(y))
        y_max = float(np.max(y))
        if not y_min < y_max:
            raise ValueError(
                f"{path.name}: controlled output y has zero range ({y_min:.12g})"
            )
        return y_min, y_max

    def refresh_reference_bounds_from_data(self, adjust_values=True, log=False):
        """Configure d_min/d_max in the physical controlled-output scale."""
        self.measured_y_bounds = None
        spins = (self.d_min_spin, self.d_max_spin)
        for spin in spins:
            spin.blockSignals(True)
        try:
            for spin in spins:
                spin.setDecimals(max(9, spin.decimals()))
                spin.setRange(-1.0e12, 1.0e12)
                spin.setSingleStep(0.05)
            self.reference_range_label.setText(
                "d interval in physical output scale y"
            )
            tip = (
                "d_min and d_max are physical desired-output values. "
                "Modules 03 and 04 internally normalize the reference with the module-01 "
                "statistics, but the GUI values and the saved plots stay in physical y units."
            )
            self.reference_range_label.setToolTip(tip)
            self.d_min_spin.setToolTip(tip)
            self.d_max_spin.setToolTip(tip)
            self.reference_combo.setToolTip(
                tip + " The same reference is used in steps 3 and 4. Alternating steps are deterministic."
            )
        finally:
            for spin in spins:
                spin.blockSignals(False)
        if log:
            self.append_log(
                "REFERENCE SCALE: d_min/d_max are expressed in physical y coordinates"
            )
        return None

    def load_metadata_from_setup(self):
        self._loading_setup = True
        try:
            physical_value = read_setup_string("plant_model_name", "two_mass_actuator_grounded_m2_lugre")
            honu_plant = read_setup_string("gui_honu_plant", "LNU")
            controller = read_setup_string("gui_controller_model", "LNU")
            learning_source = read_setup_string("plant_training_method", "batch")
            learning_detail = read_setup_string("plant_gd_ngd_learning", "NGD")
            self.plant_gradient_learning = learning_detail if learning_detail in ("GD", "NGD") else "NGD"

            self.set_combo_value(self.physical_model_combo, physical_value)
            self.set_combo_value(self.plant_model_combo, honu_plant if honu_plant in PLANT_APPROXIMATION_MODELS else "LNU")
            self.set_combo_value(self.controller_model_combo, controller if controller in CONTROLLER_MODELS else "LNU")
            if learning_source == "batch":
                self.set_combo_value(self.learning_combo, "batch")
            elif learning_source == "lm":
                self.set_combo_value(self.learning_combo, "LM")
            else:
                self.set_combo_value(self.learning_combo, self.plant_gradient_learning)
            self.set_combo_value(self.reference_combo, read_setup_string("reference_type", "steps"))

            self.plant_n_y_spin.setValue(read_setup_int("plant_n_y", 5))
            self.plant_n_u_spin.setValue(read_setup_int("plant_n_u", 5))
            self.tau_u_spin.setValue(read_setup_float("tau_u", 0.5))
            self.dt_spin.setValue(read_setup_float("dt", 0.1))
            self.t_end_spin.setValue(read_setup_float("t_end", 120.0))
            self.step_hold_spin.setValue(read_setup_float("step_hold_sec", 3.0))
            self.reference_duration_spin.setValue(read_setup_float("reference_duration_sec", read_setup_float("t_end", 120.0)))
            self.reference_step_hold_spin.setValue(read_setup_float("reference_step_hold_sec", read_setup_float("step_hold_sec", 3.0)))
            preg_enabled = bool(read_setup_value("preg_blackbox_enabled", False))
            self.preg_enabled_check.setChecked(preg_enabled)
            self.on_preg_mode_changed()
            self.r_preg_spin.setValue(read_setup_float("r_preg", 1.0))
            self.line_width_spin.setValue(read_setup_float("line_width", 2.0))
            self.line_width = float(self.line_width_spin.value())
            self.plant_epochs_spin.setValue(read_setup_int("plant_lm_epochs", 10) if learning_source == "lm" else read_setup_int("plant_gd_ngd_epochs", 5))
            self.plant_parameter_cache = {
                "LNU": self.read_plant_parameters_from_setup("LNU"),
                "QNU": self.read_plant_parameters_from_setup("QNU"),
            }
            self._last_honu_plant = self.current_honu_plant()
            self.load_plant_widgets(self._last_honu_plant)

            self.r0_init_spin.setValue(read_setup_float("r_0_init", 1.0))
            self.tau_1_spin.setValue(read_setup_float("Tau_1", 1.0))
            self.tau_2_spin.setValue(read_setup_float("Tau_2", 1.0))
            self.tau_d_spin.setValue(float(self.tau_u_spin.value()))
            self.d_min_spin.setValue(read_setup_float("d_min", -0.5))
            self.d_max_spin.setValue(read_setup_float("d_max", 0.5))
            self.u_min_spin.setValue(read_setup_float("u_min", -read_setup_float("u_amp", 1.0)))
            self.u_max_spin.setValue(read_setup_float("u_max", read_setup_float("u_amp", 1.0)))
            self.refresh_reference_bounds_from_data(adjust_values=True, log=False)

            self.controller_parameter_cache = {
                "LNU": self.read_controller_parameters_from_setup("LNU"),
                "QNU": self.read_controller_parameters_from_setup("QNU"),
            }
            self._last_controller_model = self.current_controller()
            self.load_controller_widgets(self._last_controller_model)
        finally:
            self._loading_setup = False

        self.update_selected_scripts_display()
        self.append_log("Loaded complete MRAC setup from project_setup.py.")

    def current_identification_script(self):
        key = (self.current_honu_plant(), self.current_learning_algorithm())
        return IDENTIFICATION_SCRIPT_BY_METADATA[key]

    def current_control_script(self):
        key = (self.current_honu_plant(), self.current_controller())
        return CONTROL_SCRIPT_BY_METADATA[key]

    def current_evaluation_script(self):
        key = (self.current_honu_plant(), self.current_controller())
        return EVALUATION_SCRIPT_BY_METADATA[key]

    def current_identification_output_file(self):
        return plant_bibs_file(self.current_honu_plant(), self.current_learning_algorithm())

    def current_controller_bibs_file(self):
        return controller_bibs_file(self.current_honu_plant(), self.current_controller())

    def current_controller_training_file(self):
        return controller_training_trace_file(self.current_honu_plant(), self.current_controller())

    def current_eval_output_file(self):
        return eval_file(self.current_honu_plant(), self.current_controller())

    def on_parameter_changed(self, *_args):
        if self._loading_setup:
            return
        if self._last_honu_plant:
            self.plant_parameter_cache[self._last_honu_plant] = self.capture_plant_widgets()
        if self._last_controller_model:
            self.controller_parameter_cache[self._last_controller_model] = self.capture_controller_widgets()
        self.update_selected_scripts_display()
        self.schedule_auto_apply()

    def on_line_width_changed(self, value):
        old_line_width = max(float(self.line_width), 1.0e-12)
        self.line_width = float(value)
        if self._loading_setup:
            return

        # Update all already drawn curves directly; no file reload and no delay.
        # Preserve deliberately thinner or thicker curves by scaling their pen width.
        # Sampling markers use exactly the same size law as MPC.
        width_scale = self.line_width / old_line_width
        point_size = max(1.0, 1.5 * self.line_width)
        point_edge_width = max(0.35, 0.3 * self.line_width)
        seen = set()
        plot_groups = list(self.tab_plots.values()) + [self.plots]
        for plots in plot_groups:
            for plot in plots or []:
                if id(plot) in seen:
                    continue
                seen.add(id(plot))
                for item in plot.listDataItems():
                    pen = item.opts.get("pen")
                    if pen is not None:
                        new_pen = pg.mkPen(pen)
                        new_pen.setWidthF(max(0.1, float(pen.widthF()) * width_scale))
                        item.setPen(new_pen)
                    if item.opts.get("symbol") is not None:
                        item.setSymbolSize(point_size)
                        symbol_pen = item.opts.get("symbolPen")
                        if symbol_pen is not None:
                            new_symbol_pen = pg.mkPen(symbol_pen)
                            new_symbol_pen.setWidthF(point_edge_width)
                            item.setSymbolPen(new_symbol_pen)
        if self.plot_widget is not None:
            self.plot_widget.update()
            self.plot_widget.scene().update()
        self.schedule_auto_apply()

    def on_honu_plant_changed(self, *_args):
        if self._loading_setup:
            return
        old_plant = self._last_honu_plant
        if old_plant:
            self.plant_parameter_cache[old_plant] = self.capture_plant_widgets()
        new_plant = self.current_honu_plant()
        self._loading_setup = True
        try:
            self.load_plant_widgets(new_plant)
        finally:
            self._loading_setup = False
        self._last_honu_plant = new_plant
        self.on_metadata_changed()

    def on_controller_model_changed(self, *_args):
        if self._loading_setup:
            return
        old_controller = self._last_controller_model
        if old_controller:
            self.controller_parameter_cache[old_controller] = self.capture_controller_widgets()
        new_controller = self.current_controller()
        self._loading_setup = True
        try:
            self.load_controller_widgets(new_controller)
        finally:
            self._loading_setup = False
        self._last_controller_model = new_controller
        self.on_metadata_changed()

    def on_metadata_changed(self, *_args):
        if self._loading_setup:
            return
        current_learning = self.current_learning_algorithm()
        if current_learning in ("GD", "NGD"):
            self.plant_gradient_learning = current_learning
        if self._last_honu_plant:
            self.plant_parameter_cache[self._last_honu_plant] = self.capture_plant_widgets()
        if self._last_controller_model:
            self.controller_parameter_cache[self._last_controller_model] = self.capture_controller_widgets()
        self.update_selected_scripts_display()
        # Keep the displayed graph synchronized with the selected active architecture.
        self.set_active_output(self.active_output_kind, load=True)
        self.schedule_auto_apply()

    def schedule_auto_apply(self):
        if self._loading_setup:
            return
        self._autosave_timer.start()

    def auto_apply_settings(self):
        self.apply_settings_to_setup(show_success=False, reload_plot=False, write_log=False)

    def current_output_file_for_kind(self, kind):
        if kind == "01":
            return "data_uy.txt"
        if kind == "02":
            return self.current_identification_output_file()
        if kind == "03train":
            return self.current_controller_bibs_file()
        if kind == "04eval":
            return self.current_eval_output_file()
        return self.output_combo.currentData() if hasattr(self, "output_combo") else "data_uy.txt"

    def infer_output_kind_from_file(self, file_name):
        if file_name == "data_uy.txt":
            return "01"
        if file_name == self.current_identification_output_file():
            return "02"
        if file_name == self.current_controller_training_file():
            return "03train"
        if file_name == self.current_controller_bibs_file():
            return "03train"
        if file_name == self.current_eval_output_file():
            return "04eval"
        return self.active_output_kind

    def set_active_output(self, kind, load=True):
        self.active_output_kind = kind
        file_name = self.current_output_file_for_kind(kind)
        self.last_requested_output_file = file_name
        self.refresh_file_list()
        ok = self.select_output_file(file_name, load=load)
        if not ok and load:
            self.show_missing_output_state(file_name)
        return ok

    def select_output_file(self, file_name, load=True):
        if not hasattr(self, "output_combo"):
            return False
        found = False
        self.output_combo.blockSignals(True)
        for i in range(self.output_combo.count()):
            if self.output_combo.itemData(i) == file_name:
                self.output_combo.setCurrentIndex(i)
                found = True
                break
        self.output_combo.blockSignals(False)
        if load and found:
            self.load_selected_output()
        return found

    def update_selected_scripts_display(self):
        if not hasattr(self, "btn_run_data"):
            return
        script_01 = "measured_import.py"
        script_02 = self.current_identification_script()
        script_03 = self.current_control_script()
        plant_model_file = ""

        self.btn_run_data.setText("1. Load measured data")
        self.btn_run_identification.setText("2. Identify HONU plant")
        self.btn_run_controller.setText("3. Train controller on HONU plant")
        self.btn_run_data.setToolTip(script_01)
        self.btn_run_identification.setToolTip(script_02)
        self.btn_run_controller.setToolTip(script_03)
        self.physical_model_combo.setToolTip("The format is detected automatically from the selected file")
        if hasattr(self, "btn_show_id"):
            self.btn_show_id.setToolTip(self.current_identification_output_file())
            self.btn_show_ctrl.setToolTip(
                f"{self.current_controller_training_file()}\n{self.current_controller_bibs_file()}"
            )
            self.btn_show_eval.setToolTip(self.current_eval_output_file())

    def on_physical_model_changed(self, *_args):
        """Compatibility no-op for the measured-data build.

        The active dataset is selected on the Measured data page; there are no
        physical-model presets in this application variant.
        """
        return

    def selected_physical_model_value(self):
        return self.combo_value(self.physical_model_combo)

    def validate_setup_widgets(self):
        d_min_value = float(self.d_min_spin.value())
        d_max_value = float(self.d_max_spin.value())
        if d_min_value >= d_max_value:
            raise ValueError("d_min must be smaller than d_max.")
        u_min_value = float(self.u_min_spin.value())
        u_max_value = float(self.u_max_spin.value())
        if u_min_value >= u_max_value:
            raise ValueError("u_min must be smaller than u_max.")
        if not (0.0 <= self.alpha_v_spin.value() <= 1.0 and 0.0 <= self.alpha_r0_spin.value() <= 1.0):
            raise ValueError("alpha_v and alpha_r_0 must lie in [0, 1].")
        if self.tau_1_spin.value() <= 0.0 or self.tau_2_spin.value() <= 0.0:
            raise ValueError("tau_1 and tau_2 must be positive.")
        if self.tau_u_spin.value() < 0.0 or self.tau_d_spin.value() < 0.0:
            raise ValueError("tau_u and tau_d must be non-negative.")
        if self.dt_spin.value() <= 0.0:
            raise ValueError("dt_MRAC must be positive.")
        # Measured workflow: the active dataset defines the available interval.
        # The active dataset defines the available time interval; dt_MRAC is
        # validated independently and may be increased by the user.
        if self.reference_duration_spin.value() <= self.reference_step_hold_spin.value():
            raise ValueError("d duration must be larger than d step width.")
        d_samples = round(self.reference_duration_spin.value() / self.dt_spin.value())
        hold_samples = round(self.reference_step_hold_spin.value() / self.dt_spin.value())
        if d_samples < 2 or hold_samples < 1:
            raise ValueError("d duration and d step width are too short for dt MRAC.")
        if self.preg_mode_enabled() and abs(self.r_preg_spin.value()) < 1.0e-15:
            raise ValueError("Enabled P-regulated black box requires non-zero r_preg.")
        if self.current_learning_algorithm() == "LM" and self.plant_lambda_spin.value() <= 0.0:
            raise ValueError("Levenberg-Marquardt requires a positive initial lambda.")
        ratio = self.tau_u_spin.value() / self.dt_spin.value()
        if abs(ratio - round(ratio)) > 1.0e-8:
            raise ValueError("tau_u must be an integer multiple of the MRAC sampling period dt.")

    def collect_setup_values(self):
        # Re-read data_uy.txt before every write so module 04 always uses the
        # current measured-y2 envelope for its test reference.
        self.refresh_reference_bounds_from_data(adjust_values=True, log=False)
        self.validate_setup_widgets()
        current_plant = self.current_honu_plant()
        self.plant_parameter_cache[current_plant] = self.capture_plant_widgets()
        lnu_plant = self.plant_parameter_cache.get("LNU", self.read_plant_parameters_from_setup("LNU"))
        qnu_plant = self.plant_parameter_cache.get("QNU", self.read_plant_parameters_from_setup("QNU"))

        current_controller = self.current_controller()
        self.controller_parameter_cache[current_controller] = self.capture_controller_widgets()
        lnu = self.controller_parameter_cache.get("LNU", self.read_controller_parameters_from_setup("LNU"))
        qnu = self.controller_parameter_cache.get("QNU", self.read_controller_parameters_from_setup("QNU"))

        learning = self.current_learning_algorithm()
        values = {
            "plant_model_name": self.selected_physical_model_value(),
            "gui_honu_plant": self.current_honu_plant(),
            "gui_controller_model": current_controller,
            "plant_n_y": int(self.plant_n_y_spin.value()),
            "plant_n_u": int(self.plant_n_u_spin.value()),
            "tau_u": float(self.tau_u_spin.value()),
            "dt": float(self.dt_spin.value()),
            "t_end": float(self.t_end_spin.value()),
            "step_hold_sec": float(self.step_hold_spin.value()),
            "u_min": float(self.u_min_spin.value()),
            "u_max": float(self.u_max_spin.value()),
            "u_amp": 0.5 * float(self.u_max_spin.value() - self.u_min_spin.value()),
            "reference_duration_sec": float(self.reference_duration_spin.value()),
            "reference_step_hold_sec": float(self.reference_step_hold_spin.value()),
            "preg_blackbox_enabled": self.preg_mode_enabled(),
            "r_preg": float(self.r_preg_spin.value()),
            "line_width": float(self.line_width_spin.value()),
            "plant_training_method": "batch" if learning == "batch" else ("lm" if learning == "LM" else "gd_ngd"),
            "plant_gd_ngd_learning": self.plant_gradient_learning,
            "plant_gd_ngd_epochs": int(self.plant_epochs_spin.value()),
            "plant_lm_epochs": int(self.plant_epochs_spin.value()),
            "plant_lm_lambda": float(self.plant_lambda_spin.value()),
            "mu_w": float(lnu_plant["mu_w"]),
            "plant_batch_r_0": float(lnu_plant["lambda"]),
            "plant_qnu_mu_w": float(qnu_plant["mu_w"]),
            "plant_qnu_batch_r_0": float(qnu_plant["lambda"]),
            "ctrl_learning": str(lnu["learning"]),
            "ctrl_epochs": int(lnu["epochs"]),
            "mu_v": float(lnu["mu_v"]),
            "mu_r_0": float(lnu["mu_r_0"]),
            "alpha_v": float(lnu["alpha_v"]),
            "alpha_r_0": float(lnu["alpha_r_0"]),
            "ctrl_qnu_learning": str(qnu["learning"]),
            "ctrl_qnu_epochs": int(qnu["epochs"]),
            "mu_v_qnu": float(qnu["mu_v"]),
            "mu_r_0_qnu": float(qnu["mu_r_0"]),
            "alpha_v_qnu": float(qnu["alpha_v"]),
            "alpha_r_0_qnu": float(qnu["alpha_r_0"]),
            "r_0_init": float(self.r0_init_spin.value()),
            "Tau_1": float(self.tau_1_spin.value()),
            "Tau_2": float(self.tau_2_spin.value()),
            # For alternating/random modes the visible selector controls both
            # the step-1 plant excitation u and the step-3/4 reference d.
            # This avoids a stale hidden input_type in project_setup.py.
            "input_type": (
                self.current_reference_type()
                if self.current_reference_type() in ("alternating_steps", "random_steps")
                else read_setup_string("input_type", "alternating_steps")
            ),
            "reference_type": self.current_reference_type(),
            "tau_d": float(self.tau_d_spin.value()),
            "d_min": float(self.d_min_spin.value()),
            "d_max": float(self.d_max_spin.value()),
        }
        return values

    def apply_settings_to_setup(self, *_args, show_success=True, reload_plot=True, write_log=True):
        try:
            values = self.collect_setup_values()
            write_setup_values(values)
            self.line_width = float(self.line_width_spin.value())
            self.update_selected_scripts_display()
            if reload_plot and self.current_file is not None:
                self.load_selected_output()
            self.status_label.setText("Setup saved automatically" if not show_success else "Applied GUI settings to project_setup.py")
            if write_log:
                self.append_log(
                "SETUP APPLIED: "
                f"plant={self.selected_physical_model_value()}, "
                f"HONU={self.current_honu_plant()}, controller={self.current_controller()}, "
                f"plant learning={self.current_learning_algorithm()}, "
                f"mu_w={self.mu_w_spin.value():.8g}, lambda={self.plant_lambda_spin.value():.8g}, "
                f"controller learning={self.current_controller_learning()}, "
                f"test reference={self.current_reference_type()}, "
                f"dt_MRAC={self.dt_spin.value():.8g} s, "
                f"line width={self.line_width:.3g}, "
                f"u=[{self.u_min_spin.value():.8g}, {self.u_max_spin.value():.8g}], "
                f"d=[{self.d_min_spin.value():.8g}, {self.d_max_spin.value():.8g}]"
            )
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Setup update failed", str(exc))
            return False

    def apply_metadata_to_setup(self):
        return self.apply_settings_to_setup(show_success=False)

    def script_from_file_name(self, file_name):
        for label, script_file in SCRIPT_MODULES.items():
            if script_file == file_name:
                return label, BASE_DIR / script_file
        return file_name, BASE_DIR / file_name

    def run_script_file(self, file_name):
        label, script = self.script_from_file_name(file_name)
        self.run_script(script, label)

    def active_parameter_summary(self):
        model_name = self.selected_physical_model_value()
        try:
            model_title = plant_display_name(model_name)
            meta = plant_signal_metadata(model_name)
            io_text = f"u={plant_signal_symbol(model_name, 'u')}, y={plant_signal_symbol(model_name, 'y')}"
        except Exception:
            model_title = model_name
            io_text = "u=u, y=y"
        learning = self.current_learning_algorithm()
        if learning == "batch":
            plant_learning = f"batch Ridge, lambda={self.plant_lambda_spin.value():.6g}"
        elif learning == "LM":
            plant_learning = f"Levenberg-Marquardt, epochs={self.plant_epochs_spin.value()}, lambda_0={self.plant_lambda_spin.value():.6g}"
        else:
            plant_learning = f"{learning}, epochs={self.plant_epochs_spin.value()}, mu_w={self.mu_w_spin.value():.6g}"
        ctrl_learning = self.current_controller_learning()
        return (
            f"model={model_title}; {io_text}; dt_MRAC={self.dt_spin.value():.6g} s; normalization=3 sigma\n"
            f"HONU plant={self.current_honu_plant()}, embedding n_y={self.plant_n_y_spin.value()}, "
            f"n_u={self.plant_n_u_spin.value()}, tau_u={self.tau_u_spin.value():.6g} s; learning={plant_learning}\n"
            f"controller={self.current_controller()}, learning={ctrl_learning}; "
            f"reference={self.current_reference_type()}, d=[{self.d_min_spin.value():.6g}, {self.d_max_spin.value():.6g}]"
        )

    def log_active_configuration(self):
        for line in self.active_parameter_summary().splitlines():
            self.append_log(f"Active setup: {line}")

    def log_step_request(self, step, description, output_file):
        self.append_log(f"STEP {step} requested: {description}")
        self.log_active_configuration()
        if output_file:
            self.append_log(f"Expected output: {BASE_DIR / output_file}")

    def validate_current_dataset_identity(self):
        """Validate only that a measured dataset has been exported successfully.

        Dataset channel selection, interval and resampling period are owned by the
        first ``Measured data`` tab and are intentionally independent of MRAC/MPC
        widgets.
        """
        path = self.current_data_path()
        if not path.exists():
            raise FileNotFoundError("No active measured dataset. Load and activate data in the first tab.")
        meta_path = BASE_DIR / "data" / "data_uy.txt.runmeta.json"
        if not meta_path.exists():
            raise FileNotFoundError("Measured dataset metadata are missing. Activate the dataset again.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if str(meta.get("source", "")).lower() != "measured":
            raise ValueError("The active dataset is not marked as measured data.")
        dt = float(meta.get("dt", 0.0))
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("The active measured dataset has an invalid sampling period.")
        return meta

    def run_generate_data(self):
        self._open_measured_data_workspace()

    def run_identification_from_metadata(self):
        if not self.apply_metadata_to_setup():
            return
        try:
            self.validate_current_dataset_identity()
        except Exception as exc:
            QMessageBox.warning(self, "Stale module-01 data", str(exc))
            self.append_log(f"RUN BLOCKED: {exc}")
            return
        self.set_active_output("02", load=False)
        self.log_step_request(2, "identify HONU plant", self.current_identification_output_file())
        self.run_script_file(self.current_identification_script())

    def current_training_plant_model_file(self):
        learning = self.current_learning_algorithm()
        if learning == "batch":
            tag = "batch"
        elif learning == "LM":
            tag = "lm"
        else:
            tag = "gd_ngd"
        return BASE_DIR / f"plant_{self.current_honu_plant()}_{tag}.txt"

    def invalidate_downstream_artifacts_after_module01(self):
        """Remove all artifacts whose normalization depends on module-01 data."""
        patterns = (
            "plant_*.txt",
            "plant_*.txt.normalization.npz",
            "bibs_plant_*.txt",
            "controller_*.txt",
            "controller_*.txt.normalization.npz",
            "training_controller_*.txt",
            "bibs_controller_*.txt",
            "eval_*_physical.txt",
            "test04.log",
        )
        removed = []
        for pattern in patterns:
            for path in BASE_DIR.glob(pattern):
                try:
                    path.unlink()
                    removed.append(path.name)
                except OSError:
                    pass
                meta = self.run_metadata_path(path)
                try:
                    if meta.exists():
                        meta.unlink()
                except OSError:
                    pass
        self.output_run_metadata.pop("02", None)
        self.output_run_metadata.pop("03train", None)
        self.output_run_metadata.pop("04eval", None)
        if removed:
            self.append_log(
                "DOWNSTREAM INVALIDATED: module 01 generated a new dataset; "
                "module-02, module-03 and module-04 artifacts were removed. "
                "Run modules 02, 03 and 04 again."
            )

    def verify_training_plant_matches_current_dataset(self, plant_model):
        """Reject stale HONU artifacts before launching module 03."""
        dataset_stats = load_stats(BASE_DIR / "data" / "simulated_normalization.npz")
        plant_stats = load_artifact_stats(plant_model)
        assert_same_stats(
            dataset_stats, plant_stats,
            "current module-01 dataset versus selected module-02 HONU plant",
        )

    def run_controller_from_metadata(self):
        self.append_log("STEP 3 requested: train MRAC controller")
        try:
            # Store all current GUI values first, exactly as the measured branch
            # stores its runtime configuration before controller training.
            if not self.apply_settings_to_setup(show_success=False, reload_plot=False, write_log=False):
                return

            self.validate_current_dataset_identity()
            training_dataset = BASE_DIR / "data" / "data_uy_normalized.txt"
            if not training_dataset.exists():
                QMessageBox.warning(
                    self,
                    "Missing simulated training data",
                    "Run step 1 to generate and normalize the physical-plant training data first.\n\n"
                    + str(training_dataset),
                )
                self.append_log(f"STEP 3 ERROR: missing training dataset: {training_dataset}")
                return

            plant_model = self.current_training_plant_model_file()
            if not plant_model.exists():
                QMessageBox.warning(
                    self,
                    "Missing trained plant model",
                    "Run step 2 with the currently selected HONU architecture and plant-learning method "
                    "before controller training.\n\n" + str(plant_model),
                )
                self.append_log(f"STEP 3 ERROR: missing training plant model: {plant_model}")
                return
            try:
                self.verify_training_plant_matches_current_dataset(plant_model)
            except Exception as exc:
                message = (
                    "The selected HONU plant was trained from a different module-01 dataset.\n\n"
                    "Run module 02 again before module 03.\n\n" + str(exc)
                )
                QMessageBox.warning(self, "Stale HONU plant", message)
                self.append_log(f"STEP 3 BLOCKED: stale module-02 plant: {exc}")
                return

            self.append_log(f"Active training dataset: {training_dataset}")
            self.append_log(f"Training plant model: {plant_model}")
            self.append_log(
                f"Simulated setup applied: physical plant={plant_display_name(self.selected_physical_model_value())}, "
                f"HONU plant={self.current_honu_plant()}, "
                f"plant learning={self.current_learning_algorithm()}, "
                f"controller={self.current_controller()}, "
                f"controller learning={self.current_controller_learning()}, "
                f"d={self.current_reference_type()}"
            )
            summary = self.active_parameter_summary().replace("\n", "; ")
            self.append_log(f"Active parameters: {summary}")

            self.set_active_output("03train", load=False)
            trace_file = BASE_DIR / self.current_controller_training_file()
            bibs_file = BASE_DIR / self.current_controller_bibs_file()
            self.append_log(f"Controller training output: {trace_file}")
            self.append_log(f"Controller BIBS output: {bibs_file}")
            self.run_script_file(self.current_control_script())
        except Exception as exc:
            self.append_log(f"STEP 3 ERROR: {type(exc).__name__}: {exc}")
            QMessageBox.critical(self, "Controller training failed to start", str(exc))

    def run_evaluation_from_metadata(self):
        if not self.apply_metadata_to_setup():
            return
        try:
            self.validate_current_dataset_identity()
        except Exception as exc:
            QMessageBox.warning(self, "Stale module-01 data", str(exc))
            self.append_log(f"RUN BLOCKED: {exc}")
            return
        self.set_active_output("03train", load=True)
        self.append_log(
            "STEP 4: validation is performed directly on the trained HONU plant. "
            "The controller-training closed-loop response is the active HONU validation result; no ODE model is called."
        )

    def open_project_setup(self):
        if not PROJECT_SETUP_FILE.exists():
            QMessageBox.warning(self, "Missing file", f"Cannot find {PROJECT_SETUP_FILE}")
            return
        try:
            open_file_with_system(PROJECT_SETUP_FILE)
            self.append_log(f"Opened {PROJECT_SETUP_FILE.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def install_dependencies(self):
        bat = BASE_DIR / "INSTALL_GUI_DEPENDENCIES.bat"
        if bat.exists() and sys.platform.startswith("win"):
            open_file_with_system(bat)
        else:
            QMessageBox.information(self, "Install dependencies", "Run: python -m pip install PySide6 pyqtgraph numpy scipy matplotlib")

    def set_run_buttons_enabled(self, enabled):
        self.btn_run_data.setEnabled(enabled)
        self.btn_run_identification.setEnabled(enabled)
        self.btn_run_controller.setEnabled(enabled)

    def expected_outputs_for_script(self, script_name):
        """Return files that must be freshly produced by a successful module run."""
        if script_name == "measured_import.py":
            return [BASE_DIR / "data_uy.txt", BASE_DIR / "data" / "data_uy_normalized.txt", BASE_DIR / "data" / "simulated_normalization.npz"]
        if script_name.startswith("02_identify_plant_"):
            return [BASE_DIR / self.current_identification_output_file(), self.current_training_plant_model_file()]
        if script_name.startswith("03_train_controller_"):
            return [BASE_DIR / self.current_controller_training_file(), BASE_DIR / self.current_controller_bibs_file()]
        if False:
            return [BASE_DIR / self.current_eval_output_file()]
        return []

    @staticmethod
    def output_signature(path):
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def invalidate_running_result_view(self, label, expected_outputs):
        """Hide previously loaded graphs while a new computation is pending."""
        self.clear_graph_tabs()
        names = ", ".join(path.name for path in expected_outputs) or "module output"
        self.show_message_tab("Calculation running", f"{label}\n\nWaiting for new output:\n{names}")
        self.metric_label.setText("Calculation running; previous result hidden")

    def show_failed_run_state(self, script_name, exit_code, reason=""):
        """Never display stale result files after a failed or incomplete run."""
        self.clear_graph_tabs()
        message = f"{script_name}\ncalculation failed\nexit code: {exit_code}"
        if reason:
            message += f"\n\n{reason}"
        message += "\n\nPrevious result is intentionally not displayed."
        self.show_message_tab("Calculation failed", message)
        self.metric_label.setText("Calculation failed; no new result loaded")

    def run_metadata_path(self, output_path):
        output_path = Path(output_path)
        return output_path.with_name(output_path.name + ".runmeta.json")

    def save_run_metadata_for_outputs(self, output_paths, metadata):
        payload = dict(metadata or {})
        for output_path in output_paths:
            try:
                meta_path = self.run_metadata_path(output_path)
                meta_path.write_text(
                    json.dumps(payload, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            except Exception as exc:
                self.append_log(f"RUN METADATA WRITE FAILED: {output_path}: {exc}")

    def load_run_metadata_for_output(self, output_path):
        try:
            meta_path = self.run_metadata_path(output_path)
            if not meta_path.exists():
                return {}
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            self.append_log(f"RUN METADATA READ FAILED: {output_path}: {exc}")
            return {}

    def load_embedded_output_metadata(self, output_path):
        """Read immutable configuration fields embedded in a text result.

        This is a legacy fallback for result files created before run-specific
        ``.runmeta.json`` sidecars were introduced.  It deliberately reads only
        the result file itself and never the current widgets or project setup.
        """
        path = Path(output_path) if output_path is not None else None
        if path is None or not path.exists() or path.suffix.lower() != ".txt":
            return {}
        try:
            header_lines = []
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for _ in range(16):
                    line = handle.readline()
                    if not line or not line.startswith("#"):
                        break
                    header_lines.append(line.lstrip("# ").strip())
            text = " ".join(header_lines)
        except Exception:
            return {}

        metadata = {}
        patterns = {
            "plant_model_name": r"\bmodel_name\s*=\s*([^,\s]+)",
            "dt": r"\bdt\s*=\s*([-+0-9.eE]+)",
            "tau_u": r"\btau_u\s*=\s*([-+0-9.eE]+)",
            "tau_d": r"\b(?:requested_)?tau_d\s*=\s*([-+0-9.eE]+)",
            "r_preg": r"\br_preg\s*=\s*([-+0-9.eE]+)",
            "preg_blackbox_enabled": r"\bpreg_blackbox_enabled\s*=\s*(True|False|0|1)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            raw = match.group(1)
            if key == "preg_blackbox_enabled":
                metadata[key] = raw.lower() in ("true", "1")
            elif key == "plant_model_name":
                metadata[key] = raw.strip()
            else:
                try:
                    metadata[key] = float(raw)
                except ValueError:
                    pass
        return metadata

    def current_result_metadata(self):
        """Return metadata belonging to the displayed result, never widgets."""
        metadata = dict(self.output_run_metadata.get(self.active_output_kind, {}))
        if self.current_file is not None:
            for key, value in self.load_embedded_output_metadata(self.current_file).items():
                metadata.setdefault(key, value)

            file_name = self.current_file.name
            plant_match = re.search(r"(?:bibs_plant_|plant_)(LNU|QNU)", file_name)
            if plant_match:
                metadata.setdefault("gui_honu_plant", plant_match.group(1))
            pair_match = re.search(
                r"(?:bibs_controller_|training_controller_|eval_)(LNU|QNU)_(LNU|QNU)",
                file_name,
            )
            if pair_match:
                metadata.setdefault("gui_honu_plant", pair_match.group(1))
                metadata.setdefault("gui_controller_model", pair_match.group(2))
            if "_batch" in file_name:
                metadata.setdefault("plant_training_method", "batch")
            elif "_lm" in file_name:
                metadata.setdefault("plant_training_method", "lm")
            elif "_gd_ngd" in file_name:
                metadata.setdefault("plant_training_method", "gd_ngd")

            if file_name.startswith("bibs_plant"):
                try:
                    ident = self.load_plant_identification_metadata(file_name) or {}
                except Exception:
                    ident = {}
                if ident:
                    metadata.setdefault("gui_honu_plant", ident.get("model"))
                    metadata.setdefault("plant_n_u", ident.get("n_u"))
                    metadata.setdefault("plant_n_y", ident.get("n_y"))
                    metadata.setdefault("tau_u", ident.get("tau_u"))
                    metadata.setdefault("dt", ident.get("dt"))
        return metadata

    def capture_effective_run_metadata(self):
        """Read the exact setup values that the launched module will consume.

        This snapshot is taken immediately before QProcess starts. Fullscreen
        comparison windows must use this immutable run snapshot rather than
        the current GUI widgets or a later version of project_setup.py.
        """
        return {
            "plant_model_name": read_setup_string(
                "plant_model_name", self.selected_physical_model_value()
            ),
            "gui_honu_plant": read_setup_string(
                "gui_honu_plant", self.current_honu_plant()
            ),
            "gui_controller_model": read_setup_string(
                "gui_controller_model", self.current_controller()
            ),
            "plant_n_u": int(read_setup_int("plant_n_u", int(self.plant_n_u_spin.value()))),
            "plant_n_y": int(read_setup_int("plant_n_y", int(self.plant_n_y_spin.value()))),
            "preg_blackbox_enabled": bool(read_setup_value(
                "preg_blackbox_enabled", self.preg_mode_enabled()
            )),
            "r_preg": float(read_setup_float("r_preg", float(self.r_preg_spin.value()))),
            "dt": float(read_setup_float("dt", float(self.dt_spin.value()))),
            "tau_u": float(read_setup_float("tau_u", float(self.tau_u_spin.value()))),
            "tau_d": float(read_setup_float("tau_d", float(self.tau_d_spin.value()))),
            "plant_training_method": read_setup_string(
                "plant_training_method",
                "batch" if self.current_learning_algorithm() == "batch" else
                ("lm" if self.current_learning_algorithm() == "LM" else "gd_ngd")
            ),
            "plant_gd_ngd_learning": read_setup_string(
                "plant_gd_ngd_learning", self.plant_gradient_learning
            ),
            "plant_gd_ngd_epochs": int(read_setup_int(
                "plant_gd_ngd_epochs", int(self.plant_epochs_spin.value())
            )),
            "plant_lm_epochs": int(read_setup_int(
                "plant_lm_epochs", int(self.plant_epochs_spin.value())
            )),
            "plant_lm_lambda": float(read_setup_float(
                "plant_lm_lambda", float(self.plant_lambda_spin.value())
            )),
            "mu_w": float(read_setup_float("mu_w", float(self.mu_w_spin.value()))),
            "plant_qnu_mu_w": float(read_setup_float(
                "plant_qnu_mu_w", float(self.mu_w_spin.value())
            )),
            "plant_batch_r_0": float(read_setup_float(
                "plant_batch_r_0", float(self.plant_lambda_spin.value())
            )),
            "plant_qnu_batch_r_0": float(read_setup_float(
                "plant_qnu_batch_r_0", float(self.plant_lambda_spin.value())
            )),
            # Module 03 controller-training parameters. These values are read
            # from project_setup.py immediately before the process starts, so
            # they are the exact values imported by the training script.
            "ctrl_learning": read_setup_string("ctrl_learning", "GD"),
            "ctrl_epochs": int(read_setup_int("ctrl_epochs", 100)),
            "mu_v": float(read_setup_float("mu_v", 0.01)),
            "mu_r_0": float(read_setup_float("mu_r_0", 0.001)),
            "alpha_v": float(read_setup_float("alpha_v", 1.0)),
            "alpha_r_0": float(read_setup_float("alpha_r_0", 1.0)),
            "ctrl_qnu_learning": read_setup_string("ctrl_qnu_learning", "NGD"),
            "ctrl_qnu_epochs": int(read_setup_int("ctrl_qnu_epochs", 100)),
            "mu_v_qnu": float(read_setup_float("mu_v_qnu", 0.02)),
            "mu_r_0_qnu": float(read_setup_float("mu_r_0_qnu", 0.0005)),
            "alpha_v_qnu": float(read_setup_float("alpha_v_qnu", 1.0)),
            "alpha_r_0_qnu": float(read_setup_float("alpha_r_0_qnu", 1.0)),
            "r_0_init": float(read_setup_float("r_0_init", 1.0)),
            "Tau_1": float(read_setup_float("Tau_1", 1.0)),
            "Tau_2": float(read_setup_float("Tau_2", 1.0)),
            # Module 03/04 reference and evaluation parameters actually read
            # by the scripts.
            "reference_type": read_setup_string("reference_type", "alternating_steps"),
            "reference_seed": int(read_setup_int("reference_seed", 17)),
            "reference_duration_sec": float(read_setup_float("reference_duration_sec", read_setup_float("t_end", 24.0))),
            "reference_step_hold_sec": float(read_setup_float("reference_step_hold_sec", 0.8)),
            "d_min": float(read_setup_float("d_min", -0.5)),
            "d_max": float(read_setup_float("d_max", 0.5)),
        }

    def run_script(self, script, label):
        if self.process is not None:
            QMessageBox.information(self, "Running", "A module is already running.")
            return
        if not script.exists():
            QMessageBox.warning(self, "Missing script", str(script))
            return

        self.running_expected_outputs = self.expected_outputs_for_script(script.name)
        self.running_output_snapshot = {path: self.output_signature(path) for path in self.running_expected_outputs}
        self.running_output_kind = self.active_output_kind
        self.running_setup_snapshot = self.capture_effective_run_metadata()
        self.invalidate_running_result_view(label, self.running_expected_outputs)

        self.process = QProcess(self)
        self.running_script_name = script.name
        self.process.setWorkingDirectory(str(BASE_DIR))
        self.process.setProgram(PYTHON_EXE)
        self.process.setArguments([script.name])

        env = QProcessEnvironment.systemEnvironment()
        env.insert("HONU_GUI_NO_MPL", "1")
        env.insert("MPLBACKEND", "Agg")
        old_pythonpath = env.value("PYTHONPATH")
        env.insert("PYTHONPATH", str(BASE_DIR) if not old_pythonpath else str(BASE_DIR) + os.pathsep + old_pythonpath)
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self.on_process_stdout)
        self.process.readyReadStandardError.connect(self.on_process_stderr)
        self.process.finished.connect(self.on_process_finished)
        self.process.errorOccurred.connect(self.on_process_error)

        self.run_start_time = time.time()
        self.progress.setRange(0, 0)
        self.set_run_buttons_enabled(False)
        self.btn_stop.setEnabled(True)
        self.status_led.setObjectName("statusRunning")
        self.status_led.setText("● Running")
        self.status_led.style().unpolish(self.status_led)
        self.status_led.style().polish(self.status_led)
        self.status_label.setText(label)
        self.append_log(f"RUN: {script.name}")
        self.process.start()

    def stop_process(self):
        if self.process is not None:
            self.append_log("STOP requested.")
            self.process.kill()

    def on_process_stdout(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if text.strip():
            self.append_log(text.rstrip())

    def on_process_stderr(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardError()).decode(errors="replace")
        if text.strip():
            self.append_log(text.rstrip())

    def on_process_finished(self, exit_code, exit_status):
        finished_script = self.running_script_name or "unknown module"
        expected_outputs = list(self.running_expected_outputs)
        old_signatures = dict(self.running_output_snapshot)
        requested_kind = self.running_output_kind or self.active_output_kind
        completed_run_metadata = dict(self.running_setup_snapshot or {})

        self.running_script_name = None
        self.running_expected_outputs = []
        self.running_output_snapshot = {}
        self.running_output_kind = None
        self.running_setup_snapshot = None
        self.append_log(f"FINISHED: exit_code={exit_code}, exit_status={exit_status}")
        self.process = None
        self.set_run_buttons_enabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setRange(0, 100)

        missing = [path.name for path in expected_outputs if not path.exists()]
        unchanged = [
            path.name for path in expected_outputs
            if path.exists() and self.output_signature(path) == old_signatures.get(path)
        ]
        fresh_outputs = (not missing) and (not unchanged)
        success = (exit_code == 0) and fresh_outputs

        self.progress.setValue(100 if success else 0)
        self.status_led.setObjectName("statusDone" if success else "statusError")
        self.status_led.setText("● Finished" if success else "● Error")
        self.status_led.style().unpolish(self.status_led)
        self.status_led.style().polish(self.status_led)

        if not success:
            details = []
            if exit_code != 0:
                details.append(f"process exit code {exit_code}")
            if missing:
                details.append("missing new files: " + ", ".join(missing))
            if unchanged:
                details.append("files were not regenerated: " + ", ".join(unchanged))
            reason = "; ".join(details) or "output validation failed"
            self.status_label.setText("Calculation failed or produced no new result")
            self.append_log("RESULT REJECTED: " + reason)
            self.refresh_file_list()
            self.show_failed_run_state(finished_script, exit_code, reason)
            return

        self.status_label.setText("Finished")
        self.refresh_file_list()
        if finished_script == "measured_import.py":
            self.invalidate_downstream_artifacts_after_module01()
            self.refresh_reference_bounds_from_data(adjust_values=True, log=True)
        # Persist metadata beside every generated result. This makes the
        # displayed configuration belong to the result file itself, even
        # after changing widgets, switching modules, or restarting the GUI.
        self.save_run_metadata_for_outputs(expected_outputs, completed_run_metadata)
        self.output_run_metadata[requested_kind] = completed_run_metadata
        self.active_output_kind = requested_kind
        self.set_active_output(requested_kind, load=True)

    def on_process_error(self, error):
        self.append_log(f"PROCESS ERROR: {error}")
        script_name = self.running_script_name or "unknown module"
        self.show_failed_run_state(script_name, -1, f"QProcess error: {error}")

    def on_timer(self):
        if self.process is not None and self.run_start_time is not None:
            self.time_label.setText(f"elapsed: {time.time() - self.run_start_time:.1f} s")

    # ------------------------------------------------------------------
    # Plot layout and pyqtgraph rendering
    # ------------------------------------------------------------------

    def _clone_current_graph_for_full_screen(self, source_widget, title):
        """Create an independent pyqtgraph snapshot of the active graph tab.

        The clone owns its PlotItems and data arrays.  Subsequent simulations
        may therefore clear or replace the main-window tabs without changing
        an already opened comparison window.
        """
        clone_widget = pg.GraphicsLayoutWidget()
        clone_widget.setBackground("w")
        clone_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Full-screen comparison titles are intentionally smaller than the
        # main-GUI title because they also contain run metadata.
        full_screen_title_size = max(8, int(round(0.8 * (self.font_size + 3))))
        title_label = pg.LabelItem(
            title, size=f"{full_screen_title_size}pt", color="#102a56", justify="center"
        )
        clone_widget.addItem(title_label, row=0, col=0)
        try:
            layout = clone_widget.ci.layout
            layout.setRowFixedHeight(0, max(24, full_screen_title_size + 14))
            layout.setRowSpacing(0, 4)
        except Exception:
            pass

        source_plots = list(self.tab_plots.get(source_widget, []))
        clone_plots = []
        initial_ranges = []
        base_plot = None

        for i, source_plot in enumerate(source_plots):
            view_box = pg.ViewBox()
            plot = clone_widget.addPlot(
                row=i + 1,
                col=0,
                viewBox=view_box,
                axisItems={"left": CompactYAxis("left")},
            )
            plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
            plot.setMenuEnabled(True)
            plot.setMouseEnabled(x=True, y=True)
            plot.getViewBox().setMouseMode(pg.ViewBox.RectMode)

            try:
                plot.setLabel("left", source_plot.getAxis("left").labelText or "")
                plot.setLabel("bottom", source_plot.getAxis("bottom").labelText or "")
            except Exception:
                pass

            if base_plot is None:
                base_plot = plot
            else:
                plot.setXLink(base_plot)

            for source_item in source_plot.listDataItems():
                try:
                    x, y = source_item.getData()
                    if x is None or y is None:
                        continue
                    opts = source_item.opts
                    pen = opts.get("pen", None)
                    shadow_pen = opts.get("shadowPen", None)
                    item = plot.plot(
                        np.array(x, copy=True),
                        np.array(y, copy=True),
                        pen=pg.mkPen(pen) if pen is not None else None,
                        shadowPen=pg.mkPen(shadow_pen) if shadow_pen is not None else None,
                        name=source_item.name(),
                        symbol=opts.get("symbol", None),
                        symbolSize=opts.get("symbolSize", 10),
                        symbolPen=opts.get("symbolPen", None),
                        symbolBrush=opts.get("symbolBrush", None),
                        connect=opts.get("connect", "auto"),
                        stepMode=opts.get("stepMode", None),
                    )
                    item.setVisible(source_item.isVisible())
                    self.optimize_curve_item(item, allow_downsampling=(opts.get("stepMode", None) is None))
                except Exception as exc:
                    self.append_log(f"FULL SCREEN COPY WARNING: {exc}")

            try:
                ranges = source_plot.getViewBox().viewRange()
                copied_ranges = [list(ranges[0]), list(ranges[1])]
                plot.setRange(
                    xRange=copied_ranges[0], yRange=copied_ranges[1], padding=0.0
                )
                initial_ranges.append(copied_ranges)
            except Exception:
                initial_ranges.append(None)

            plot.setVisible(source_plot.isVisible())
            clone_plots.append(plot)

        return clone_widget, clone_plots, initial_ranges

    def open_current_graph_full_screen(self):
        if not hasattr(self, "graph_tabs") or self.graph_tabs.count() == 0:
            QMessageBox.information(self, "Full screen", "No graph is currently available.")
            return

        index = self.graph_tabs.currentIndex()
        source_widget = self.graph_tabs.widget(index)
        if source_widget is None:
            return
        graph_title = self.graph_tabs.tabText(index) or "HONU MRAC graph"

        # All descriptive values come from the displayed result.  Widget values
        # may already describe a future run and must never rewrite an existing
        # graph or comparison window.
        run_meta = self.current_result_metadata()
        output_kind = str(self.active_output_kind)

        plant_model = str(run_meta.get("plant_model_name", "")).strip()
        plant_name = plant_display_name(plant_model) if plant_model else "saved physical plant"
        honu_name = str(run_meta.get("gui_honu_plant", "saved HONU")).strip() or "saved HONU"
        controller_name = str(run_meta.get("gui_controller_model", "saved controller")).strip() or "saved controller"

        def numeric_text(key, label, unit="", integer=False):
            if key not in run_meta or run_meta.get(key) is None:
                return None
            try:
                value = int(run_meta[key]) if integer else float(run_meta[key])
            except (TypeError, ValueError):
                return None
            value_text = str(value) if integer else f"{value:.8g}"
            return f"{label}={value_text}{unit}"

        preg_suffix = ""
        if bool(run_meta.get("preg_blackbox_enabled", False)):
            if "r_preg" in run_meta:
                try:
                    preg_suffix = f" | p-reg r_Preg={float(run_meta['r_preg']):.8g}"
                except (TypeError, ValueError):
                    preg_suffix = " | p-reg enabled"
            else:
                preg_suffix = " | p-reg enabled"

        parameter_parts = [
            numeric_text("plant_n_u", "n_u", integer=True),
            numeric_text("plant_n_y", "n_y", integer=True),
            numeric_text("tau_u", "tau_u", " s"),
        ]
        parameter_text = ", ".join(part for part in parameter_parts if part)
        control_parts = parameter_parts + [numeric_text("tau_d", "tau_d", " s")]
        control_parameter_text = ", ".join(part for part in control_parts if part)
        sampling_parts = [
            numeric_text("dt", "dt_MRAC", " s"),
        ]
        sampling_text = ", ".join(part for part in sampling_parts if part)

        if output_kind == "01":
            metadata_parts = [plant_name]
            if sampling_text:
                metadata_parts.append(sampling_text)
            metadata_text = " | ".join(metadata_parts) + preg_suffix
            if not run_meta:
                metadata_text += " | exact run metadata unavailable"
            window_title = f"Plant data | {graph_title}"
        elif output_kind == "02":
            method = str(run_meta.get("plant_training_method", "")).lower()
            learning_text = "saved identification"
            if method == "batch":
                key = "plant_qnu_batch_r_0" if honu_name.upper() == "QNU" else "plant_batch_r_0"
                if key in run_meta:
                    try:
                        learning_text = f"batch Ridge, lambda={float(run_meta[key]):.8g}"
                    except (TypeError, ValueError):
                        learning_text = "batch Ridge"
                else:
                    learning_text = "batch Ridge"
            elif method == "lm":
                details = []
                if "plant_lm_epochs" in run_meta:
                    details.append(f"epochs={int(run_meta['plant_lm_epochs'])}")
                if "plant_lm_lambda" in run_meta:
                    details.append(f"lambda_0={float(run_meta['plant_lm_lambda']):.8g}")
                learning_text = "LM" + (", " + ", ".join(details) if details else "")
            elif method == "gd_ngd":
                algorithm = str(run_meta.get("plant_gd_ngd_learning", "GD/NGD"))
                details = []
                if "plant_gd_ngd_epochs" in run_meta:
                    details.append(f"epochs={int(run_meta['plant_gd_ngd_epochs'])}")
                mu_key = "plant_qnu_mu_w" if honu_name.upper() == "QNU" else "mu_w"
                if mu_key in run_meta:
                    details.append(f"mu_w={float(run_meta[mu_key]):.8g}")
                learning_text = algorithm + (", " + ", ".join(details) if details else "")
            metadata_parts = [plant_name, f"HONU plant {honu_name}", learning_text]
            if parameter_text:
                metadata_parts.append(parameter_text)
            metadata_text = " | ".join(metadata_parts) + preg_suffix
            if not run_meta:
                metadata_text += " | exact run metadata unavailable"
            window_title = f"Plant identification | {graph_title}"
        elif output_kind == "03train":
            metadata_parts = [f"HONU plant {honu_name}", f"controller {controller_name}"]
            if control_parameter_text:
                metadata_parts.append(control_parameter_text)

            is_qnu_controller = controller_name.upper() == "QNU"
            epoch_key = "ctrl_qnu_epochs" if is_qnu_controller else "ctrl_epochs"
            learning_key = "ctrl_qnu_learning" if is_qnu_controller else "ctrl_learning"
            mu_v_key = "mu_v_qnu" if is_qnu_controller else "mu_v"
            mu_r0_key = "mu_r_0_qnu" if is_qnu_controller else "mu_r_0"
            alpha_v_key = "alpha_v_qnu" if is_qnu_controller else "alpha_v"
            alpha_r0_key = "alpha_r_0_qnu" if is_qnu_controller else "alpha_r_0"
            if epoch_key in run_meta:
                learning_details = [
                    str(run_meta.get(learning_key, "learning")),
                    f"epochs={int(run_meta[epoch_key])}",
                ]
                for key, label in (
                    (mu_v_key, "mu_v"),
                    (mu_r0_key, "mu_r0"),
                    (alpha_v_key, "alpha_v"),
                    (alpha_r0_key, "alpha_r0"),
                ):
                    if key in run_meta:
                        learning_details.append(f"{label}={float(run_meta[key]):.8g}")
                metadata_parts.append("learning: " + ", ".join(learning_details))
            else:
                metadata_parts.append("saved run; exact learning snapshot unavailable")
            metadata_text = " | ".join(metadata_parts) + preg_suffix
            window_title = f"Controller training | {graph_title}"
        elif output_kind == "04eval":
            metadata_parts = [
                plant_name,
                f"loaded HONU plant {honu_name}",
                f"loaded controller {controller_name}",
            ]
            if control_parameter_text:
                metadata_parts.append(control_parameter_text)
            if not run_meta:
                metadata_parts.append("exact run metadata unavailable")
            metadata_text = " | ".join(metadata_parts) + preg_suffix
            window_title = f"Controller evaluation | {graph_title}"
        else:
            metadata_parts = [plant_name]
            if parameter_text:
                metadata_parts.append(parameter_text)
            metadata_text = " | ".join(metadata_parts) + preg_suffix
            if not run_meta:
                metadata_text += " | exact run metadata unavailable"
            window_title = f"HONU MRAC | {graph_title}"

        # The long run metadata is rendered only in the top QLabel panel.
        # Keep the pyqtgraph title short so it never consumes plot width.
        clone_widget, clone_plots, ranges = self._clone_current_graph_for_full_screen(
            source_widget, graph_title
        )

        window = FullScreenPlotWindow(
            clone_widget, clone_plots, ranges, window_title, restore_callback=None,
            metadata_text=metadata_text, footer_text="", parent=None
        )
        COMPARISON_PLOT_WINDOWS.append(window)

        def forget_closed_window(*_args, current_window=window):
            try:
                COMPARISON_PLOT_WINDOWS.remove(current_window)
            except ValueError:
                pass

        window.destroyed.connect(forget_closed_window)
        # Normal independent top-level window with native minimize, maximize,
        # restore and resize controls. It remains unchanged during later runs.
        window.setWindowFlag(Qt.Window, True)
        window.resize(max(1100, int(self.width() * 0.82)), max(700, int(self.height() * 0.82)))
        window.show()
        window.raise_()
        window.activateWindow()
        QTimer.singleShot(0, clone_widget.show)
        QTimer.singleShot(0, clone_widget.update)

    def clear_graph_tabs(self):
        if hasattr(self, "graph_tabs"):
            self.graph_tabs.clear()
        self.plot_widget = None
        self.plots = []
        self.base_plot = None
        self.tab_plots = {}
        self.initial_ranges = {}
        self.fixed_y_ranges = {}

    def add_graph_tab(self, title):
        widget = pg.GraphicsLayoutWidget()
        widget.setBackground("w")
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self, "graph_tabs"):
            self.graph_tabs.addTab(widget, title)
            self.graph_tabs.setCurrentWidget(widget)
        self.plot_widget = widget
        self.plots = []
        self.base_plot = None
        self.tab_plots[widget] = self.plots
        return widget

    def show_message_tab(self, title, message):
        self.add_graph_tab(title)
        label = pg.LabelItem(message, size=f"{self.font_size + 2}pt", color="#334155", justify="center")
        self.plot_widget.addItem(label, row=0, col=0)

    def load_table_if_exists(self, file_name):
        path = BASE_DIR / file_name
        if not path.exists():
            return None
        try:
            return load_table(path)
        except Exception as exc:
            self.append_log(f"LOAD ERROR: {path.name}: {exc}")
            return None

    def plant_weight_file_from_bibs_file(self, file_name):
        if "LNU_batch" in file_name:
            return "plant_LNU_batch.txt"
        if "LNU_gd_ngd" in file_name:
            return "plant_LNU_gd_ngd.txt"
        if "LNU_lm" in file_name:
            return "plant_LNU_lm.txt"
        if "QNU_batch" in file_name:
            return "plant_QNU_batch.txt"
        if "QNU_gd_ngd" in file_name:
            return "plant_QNU_gd_ngd.txt"
        if "QNU_lm" in file_name:
            return "plant_QNU_lm.txt"
        return None

    def plant_trace_file_from_bibs_file(self, file_name):
        if "LNU_lm" in file_name:
            return "lm_trace_plant_LNU.txt"
        if "QNU_lm" in file_name:
            return "lm_trace_plant_QNU.txt"
        return None

    def load_plant_identification_metadata(self, bibs_file_name):
        weight_file = self.plant_weight_file_from_bibs_file(bibs_file_name)
        if weight_file is None:
            return None
        weight_path = BASE_DIR / weight_file
        if not weight_path.exists():
            return None
        wdata = np.loadtxt(weight_path)
        wdata = np.asarray(wdata, dtype=float).ravel()
        if wdata.size < 6:
            return None
        dt = float(wdata[0])
        tau_u = float(wdata[1])
        n_u = int(round(wdata[2]))
        n_u1 = int(round(wdata[3]))
        n_y = int(round(wdata[4]))
        model = "QNU" if "QNU" in bibs_file_name else "LNU"
        if model == "QNU":
            if wdata.size < 8:
                return None
            n_xi = int(round(wdata[5]))
            n_phi = int(round(wdata[6]))
            expected_n_xi = 1 + n_y + n_u
            expected_n_phi = expected_n_xi * (expected_n_xi + 1) // 2
            if n_xi != expected_n_xi or n_phi != expected_n_phi:
                return None
            w = wdata[7:]
            if w.size != n_phi:
                return None
        else:
            w = wdata[5:]
            if w.size != 1 + n_y + n_u:
                return None
        return {
            "weight_file": weight_file,
            "model": model,
            "dt": dt,
            "tau_u": tau_u,
            "n_u": n_u,
            "n_u1": n_u1,
            "n_y": n_y,
            "w": np.asarray(w, dtype=float).reshape(-1),
        }

    def plant_identification_series_length(self):
        data_path = BASE_DIR / "data" / "data_uy_normalized.txt"
        if not data_path.exists():
            return None
        try:
            _cols, data = load_table(data_path)
        except Exception:
            return None
        return int(data.shape[0])

    def plant_identification_rmse_and_weights(self, bibs_file_name):
        meta = self.load_plant_identification_metadata(bibs_file_name)
        if meta is None:
            return None
        learning = "lm" if "_lm" in bibs_file_name.lower() else ("ridge" if "_batch" in bibs_file_name.lower() else "gd_ngd")
        out = {
            "learning": learning,
            "theta_final": np.asarray(meta["w"], dtype=float).reshape(-1),
            "sample_count": self.plant_identification_series_length(),
            "epoch_axis": None,
            "weight_history": None,
            "rmse": None,
        }
        if learning != "lm":
            return out
        trace_file = self.plant_trace_file_from_bibs_file(bibs_file_name)
        loaded = self.load_table_if_exists(trace_file) if trace_file else None
        if loaded is None:
            return out
        trace_columns, trace_data = loaded
        iter_idx = column_index(trace_columns, "epoch")
        if iter_idx is None:
            iter_idx = column_index(trace_columns, "iteration")
        if iter_idx is None:
            iter_idx = 0
        sse_idx = column_index(trace_columns, "SSE")
        if sse_idx is None:
            sse_idx = 1 if trace_data.shape[1] > 1 else None
        weight_start_idx = 3 if trace_data.shape[1] > 3 else None
        epoch_axis = np.asarray(trace_data[:, iter_idx], dtype=float).reshape(-1)
        out["epoch_axis"] = epoch_axis
        if weight_start_idx is not None and trace_data.shape[1] > weight_start_idx:
            out["weight_history"] = np.asarray(trace_data[:, weight_start_idx:], dtype=float)
        if sse_idx is not None:
            sse = np.asarray(trace_data[:, sse_idx], dtype=float).reshape(-1)
            denom = max(1, int(out["sample_count"] or 1))
            out["rmse"] = np.sqrt(np.maximum(sse, 0.0) / float(denom))
        return out

    def qnu_phi(self, x):
        x = np.asarray(x, dtype=float)
        xi = np.empty(len(x) + 1, dtype=float)
        xi[0] = 1.0
        xi[1:] = x
        terms = []
        for i in range(len(xi)):
            for j in range(i, len(xi)):
                terms.append(xi[i] * xi[j])
        return np.asarray(terms, dtype=float)

    def compute_identification_fit(self, bibs_file_name):
        meta = self.load_plant_identification_metadata(bibs_file_name)
        if meta is None:
            return None
        weight_file = meta["weight_file"]
        # Module 02 identifies the plant in fixed normalized coordinates.
        # Therefore the GUI fit must use exactly the same normalized dataset;
        # combining HONU weights with physical data_uy.txt produces a false
        # apparent mismatch between the identified response and source data.
        data_path = BASE_DIR / "data" / "data_uy_normalized.txt"
        if not data_path.exists():
            return None
        uy_columns, uy = load_table(data_path)
        dt = float(meta["dt"])
        n_u = int(meta["n_u"])
        n_u1 = int(meta["n_u1"])
        n_y = int(meta["n_y"])
        model = str(meta["model"])
        w = np.asarray(meta["w"], dtype=float).reshape(-1)

        t_idx = column_index(uy_columns, "t") or 0
        # Normalized files use u_z and y_z, while older files may retain
        # the generic u/y names. Prefer the explicit normalized channels.
        u_idx = column_index(uy_columns, "u_z")
        if u_idx is None:
            u_idx = column_index(uy_columns, "u")
        y_idx = column_index(uy_columns, "y_z")
        if y_idx is None:
            y_idx = column_index(uy_columns, "y")
        if u_idx is None:
            u_idx = 1
        if y_idx is None:
            y_idx = 2 if uy.shape[1] > 2 else uy.shape[1] - 1
        t = uy[:, t_idx]
        u = uy[:, u_idx]
        y = uy[:, y_idx]
        y_n = np.full_like(y, np.nan, dtype=float)
        e = np.full_like(y, np.nan, dtype=float)
        n_start = max(n_u1 + n_u, n_y)
        for k in range(n_start, len(y)):
            x = np.empty(n_y + n_u, dtype=float)
            x[:n_y] = y[k - n_y:k][::-1]
            x[n_y:n_y + n_u] = u[k - n_u1 - n_u:k - n_u1][::-1]
            if model == "QNU":
                phi = self.qnu_phi(x)
            else:
                phi = np.concatenate(([1.0], x))
            if len(phi) == len(w):
                y_n[k] = float(w @ phi)
                e[k] = y[k] - y_n[k]
        # The HONU calculation above intentionally stays normalized. Only the
        # values returned to the GUI plotting layer are converted to physical units.
        stats = load_stats(BASE_DIR / "data" / "simulated_normalization.npz")
        u_plot = denormalize_u(u, stats)
        y_plot = denormalize_y(y, stats)
        y_n_plot = denormalize_y(y_n, stats)
        e_plot = denormalize_error(e, stats)
        cols = ["t", "u", "y", "y_n", "e"]
        out = np.column_stack((t, u_plot, y_plot, y_n_plot, e_plot))
        return cols, out, dt

    def plot_identification_fit(self, bibs_file_name):
        fit = self.compute_identification_fit(bibs_file_name)
        if fit is None:
            self.plot_widget.clear()
            label = pg.LabelItem("Identification fit is not available. Run 01 and 02 first.", size=f"{self.font_size + 2}pt", color="#334155", justify="center")
            self.plot_widget.addItem(label, row=0, col=0)
            return
        columns, data, dt = fit
        t = data[:, 0]
        xlabel = f"t [sec], dt={dt:.6g} [sec]"
        self.clear_and_make_vertical_plots(self.plant_bibs_title(bibs_file_name) + ": identification fit", ["u", "y, y_n", "e"], xlabel)
        self.add_curve_to_axis(0, columns, data, t, "u", "b")
        self.maybe_legend(1)
        self.add_curve_to_axis(1, columns, data, t, "y", "b", label="y")
        self.add_curve_to_axis(1, columns, data, t, "y_n", "g", label="y_n")
        self.add_curve_to_axis(2, columns, data, t, "e", "r")

    def plot_plant_identification_diagnostics(self, bibs_file_name):
        diag = self.plant_identification_rmse_and_weights(bibs_file_name)
        if diag is None:
            self.plot_widget.clear()
            label = pg.LabelItem(
                "Plant identification diagnostics are not available. Run 01 and 02 first.",
                size=f"{self.font_size + 2}pt",
                color="#334155",
                justify="center",
            )
            self.plot_widget.addItem(label, row=0, col=0)
            return

        use_epoch_diagnostics = str(diag.get("learning", "ridge")).lower() == "lm"
        if use_epoch_diagnostics:
            self.clear_and_make_vertical_plots(
                self.plant_bibs_title(bibs_file_name) + ": HONU weights + RMSE",
                ["w", "RMSE"],
                "epoch",
            )
        else:
            self.clear_and_make_vertical_plots(
                self.plant_bibs_title(bibs_file_name) + ": HONU weights",
                ["w"],
                "k [sample]",
            )

        theta_final = np.asarray(diag.get("theta_final", []), dtype=float).reshape(-1)
        weight_history = np.asarray(diag.get("weight_history", []), dtype=float)
        if weight_history.ndim == 1 and weight_history.size:
            weight_history = weight_history[None, :]
        epoch_axis = np.asarray(diag.get("epoch_axis", []), dtype=float).reshape(-1)
        rmse = np.asarray(diag.get("rmse", []), dtype=float).reshape(-1)

        if use_epoch_diagnostics and weight_history.ndim == 2 and weight_history.size and epoch_axis.size:
            n_epochs = min(epoch_axis.size, weight_history.shape[0])
            for j in range(weight_history.shape[1]):
                color = pg.intColor(j, hues=max(8, weight_history.shape[1]), values=1, maxValue=220)
                item = self.plots[0].plot(
                    epoch_axis[:n_epochs],
                    weight_history[:n_epochs, j],
                    pen=pg.mkPen(color, width=max(1.0, self.line_width * 0.8)),
                )
                self.optimize_curve_item(item, allow_downsampling=False)
            self.plots[0].setLabel("left", "w", **{"font-weight": "bold"})
            self.plots[0].getAxis("bottom").setStyle(showValues=False)
            self.plots[0].getAxis("bottom").setLabel("")
            if rmse.size:
                n_rmse = min(epoch_axis.size, rmse.size)
                pen = pg.mkPen("r", width=self.line_width)
                item = self.plots[1].plot(
                    epoch_axis[:n_rmse],
                    rmse[:n_rmse],
                    pen=pen,
                    symbol="o",
                    symbolSize=5,
                    symbolPen=pen,
                    symbolBrush=pg.mkBrush("r"),
                    name="RMSE",
                )
                self.optimize_curve_item(item, allow_downsampling=False)
                self.plots[1].setLabel("left", "RMSE")
                self.plots[1].setLabel("bottom", "epoch")
                self.maybe_legend(1)
            return

        sample_count = int(diag.get("sample_count") or max(1, theta_final.size))
        k_axis = np.arange(1, sample_count + 1, dtype=float)
        for j in range(theta_final.size):
            color = pg.intColor(j, hues=max(8, theta_final.size), values=1, maxValue=220)
            item = self.plots[0].plot(
                k_axis,
                np.full(k_axis.shape, float(theta_final[j]), dtype=float),
                pen=pg.mkPen(color, width=max(1.0, self.line_width * 0.8)),
            )
            self.optimize_curve_item(item, allow_downsampling=True)
        self.plots[0].setLabel("left", "w", **{"font-weight": "bold"})
        self.plots[0].setLabel("bottom", "k [sample]")

    def plot_output_bundle(self, file_name, columns, data, dt_txt):
        self.clear_graph_tabs()
        if file_name.startswith("bibs_plant"):
            self.add_graph_tab("02 identification fit")
            self.plot_identification_fit(file_name)
            self.add_graph_tab("02 identification weights / RMSE")
            self.plot_plant_identification_diagnostics(file_name)
            self.add_graph_tab("02 Spectral radius")
            self.plot_data(columns, data, file_name, dt_txt)
        elif file_name.startswith("training_controller") or file_name.startswith("bibs_controller"):
            # Resolve the companion files from the selected result name.  The
            # current architecture widgets may already describe a future run.
            if file_name.startswith("training_controller"):
                trace_file = file_name
                bibs_file = file_name.replace("training_controller_", "bibs_controller_", 1)
            else:
                bibs_file = file_name
                trace_file = file_name.replace("bibs_controller_", "training_controller_", 1)
            loaded_trace = self.load_table_if_exists(trace_file)
            loaded_bibs = self.load_table_if_exists(bibs_file)
            if loaded_trace is not None:
                trace_cols, trace_data = loaded_trace
                dt_trace = self.dt_text_from_data(trace_data)
                self.add_graph_tab("03 training response")
                self.plot_data(trace_cols, trace_data, trace_file, dt_trace)
            else:
                self.show_message_tab(
                    "03 training response",
                    f"Missing {trace_file}\nRun module 03 controller training first.",
                )
            if loaded_bibs is not None:
                bibs_cols, bibs_data = loaded_bibs
                dt_bibs = self.dt_text_from_data(bibs_data)
                self.add_graph_tab("03 training spectral radius")
                self.plot_data(bibs_cols, bibs_data, bibs_file, dt_bibs)
            else:
                self.show_message_tab(
                    "03 training spectral radius",
                    f"Missing {bibs_file}\nRun module 03 controller training first.",
                )
        elif file_name.startswith("eval_"):
            self.add_graph_tab("04 controller evaluation")
            self.plot_data(columns, data, file_name, dt_txt)
        else:
            title = "01 plant data" if file_name.startswith("data_uy") else file_name
            self.add_graph_tab(title)
            self.plot_data(columns, data, file_name, dt_txt)

    def dt_text_from_data(self, data):
        if data.shape[0] > 1:
            t = data[:, 0]
            dt = np.nanmedian(np.diff(t))
            if np.isfinite(dt):
                return f"{dt:.6g} s"
        return "-"

    def refresh_file_list(self):
        current_file = self.output_combo.currentData() if hasattr(self, "output_combo") else None
        active_outputs = (
            ("01 active plant data", "data_uy.txt"),
            ("02 active plant identification", self.current_identification_output_file()),
            ("03 active controller training", self.current_controller_bibs_file()),
            ("04 active controller evaluation", self.current_eval_output_file()),
        )
        self.output_combo.blockSignals(True)
        self.output_combo.clear()
        for label, file_name in active_outputs:
            suffix = "" if (BASE_DIR / file_name).exists() else "  [missing]"
            self.output_combo.addItem(label + suffix, file_name)
        target_file = self.current_output_file_for_kind(self.active_output_kind) or self.last_requested_output_file or current_file
        if target_file:
            for i in range(self.output_combo.count()):
                if self.output_combo.itemData(i) == target_file:
                    self.output_combo.setCurrentIndex(i)
                    break
        self.output_combo.blockSignals(False)

    def load_selected_output(self):
        if not hasattr(self, "output_combo") or self.output_combo.count() == 0:
            return
        file_name = self.output_combo.currentData()
        if not file_name:
            return
        self.active_output_kind = self.infer_output_kind_from_file(file_name)
        self.last_requested_output_file = file_name
        path = BASE_DIR / file_name
        self.current_file = path
        # Restore immutable metadata associated with this exact result file.
        # Never let a later checkbox/widget change rewrite the description of
        # an already generated module 03/04 result.
        persisted_meta = self.load_run_metadata_for_output(path)
        if persisted_meta:
            self.output_run_metadata[self.active_output_kind] = persisted_meta
        else:
            # Never leave metadata from another file of the same workflow step
            # attached to a legacy result that has no sidecar of its own.
            self.output_run_metadata.pop(self.active_output_kind, None)
        try:
            columns, data = load_table(path)
        except Exception as exc:
            self.show_missing_output_state(path.name, detail=str(exc))
            return

        dt_txt = self.dt_text_from_data(data)
        self.metric_label.setText(f"{path.name}\nsamples={data.shape[0]}, columns={data.shape[1]}\ndt={dt_txt}")
        self.status_label.setText(f"Loaded {path.name}")
        self.append_log(f"LOADED: {path.name}, shape={data.shape}")
        self.plot_output_bundle(path.name, columns, data, dt_txt)

    def next_step_hint_for_file(self, file_name):
        if file_name == "data_uy.txt":
            return "Run module 01 first."
        if file_name.startswith("bibs_plant"):
            return "Run module 01, then the selected module 02 plant identification."
        if file_name.startswith("training_controller") or file_name.startswith("bibs_controller"):
            return "Run modules 01 and 02, then module 03 controller training."
        if file_name.startswith("eval_"):
            return "Run modules 01, 02, and 03, then module 04 controller evaluation."
        return "Run the module that generates this output file."

    def show_missing_output_state(self, file_name, detail=""):
        self.clear_graph_tabs()
        hint = self.next_step_hint_for_file(file_name)
        status = f"{file_name}\nnot generated yet\n\n{hint}"
        if detail:
            status += f"\n\nread status: {detail}"
        if file_name.startswith("bibs_plant"):
            self.show_message_tab("02 identification fit", status)
            self.show_message_tab("02 identification weights / RMSE", status)
            self.show_message_tab("02 Spectral radius", status)
        elif file_name.startswith("training_controller") or file_name.startswith("bibs_controller"):
            trace_file = self.current_controller_training_file()
            bibs_file = self.current_controller_bibs_file()
            self.show_message_tab("03 training response", f"{trace_file}\nnot generated yet\n\n{hint}")
            self.show_message_tab("03 training spectral radius", f"{bibs_file}\nnot generated yet\n\n{hint}")
        elif file_name.startswith("eval_"):
            eval_name = self.current_eval_output_file()
            self.show_message_tab("04 controller evaluation", f"{eval_name}\nnot generated yet\n\n{hint}")
        else:
            self.show_message_tab("01 plant data", status)
        self.metric_label.setText(f"{file_name}\nnot generated yet")
        self.status_label.setText(f"Ready; missing {file_name}")
        self.status_led.setObjectName("statusIdle")
        self.status_led.setText("● Ready")
        self.status_led.style().unpolish(self.status_led)
        self.status_led.style().polish(self.status_led)
        self.append_log(f"WAITING FOR OUTPUT: {file_name}. {hint}")

    def clear_and_make_vertical_plots(self, title, ylabels, xlabel):
        if self.plot_widget is None:
            self.add_graph_tab(title)
        self.plot_widget.clear()
        self.plots = []
        self.base_plot = None
        title_label = pg.LabelItem(title, size=f"{self.font_size + 3}pt", color="#102a56", justify="center")
        self.plot_widget.addItem(title_label, row=0, col=0)
        self.plot_title_label = title_label
        # Keep the graph title in a compact, dedicated row at the very top.
        # Without a fixed row height, GraphicsLayout may distribute excessive
        # vertical space to LabelItem, making the title appear inside the plot.
        try:
            graphics_layout = self.plot_widget.ci.layout
            graphics_layout.setRowFixedHeight(0, max(28, self.font_size + 18))
            graphics_layout.setRowSpacing(0, 4)
        except Exception:
            pass
        for i, ylabel in enumerate(ylabels):
            view_box = ZoomResetViewBox(owner=self)
            p = self.plot_widget.addPlot(
                row=i + 1, col=0, viewBox=view_box,
                axisItems={"left": CompactYAxis("left")},
            )
            p.showGrid(x=True, y=True, alpha=GRID_ALPHA)
            p.setLabel("left", ylabel)
            p.setLabel("bottom", xlabel if i == len(ylabels) - 1 else "")
            p.setMenuEnabled(True)
            p.setMouseEnabled(x=True, y=True)
            p.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            if i == 0:
                self.base_plot = p
            else:
                p.setXLink(self.base_plot)
            self.plots.append(p)
        if self.plot_widget is not None:
            self.tab_plots[self.plot_widget] = list(self.plots)
        return self.plots

    def add_curve_to_axis(self, axis_index, columns, data, t, name, color, width=None, style=Qt.SolidLine, label=None, step_mode=None):
        if axis_index >= len(self.plots):
            return False
        idx = column_index(columns, name)
        if idx is None:
            return False
        x, y = finite_xy(t, data[:, idx])
        if len(x) == 0:
            return False
        pen = pg.mkPen(color=color, width=width or self.line_width, style=style)
        plot_kwargs = {"pen": pen, "name": label or name, "symbol": None}
        if step_mode is not None:
            plot_kwargs["stepMode"] = step_mode
        item = self.plots[axis_index].plot(x, y, **plot_kwargs)
        self.optimize_curve_item(item, allow_downsampling=(step_mode is None))
        return item is not None

    def add_array_to_axis(self, axis_index, t, y, color, name, width=None, style=Qt.SolidLine):
        if axis_index >= len(self.plots):
            return False
        x, yy = finite_xy(t, y)
        if len(x) == 0:
            return False
        pen = pg.mkPen(color=color, width=width or self.line_width, style=style)
        item = self.plots[axis_index].plot(x, yy, pen=pen, name=name, symbol=None)
        self.optimize_curve_item(item)
        return True

    def add_limit_line(self, axis_index, value=1.0):
        if axis_index < len(self.plots):
            line = pg.InfiniteLine(pos=value, angle=0, pen=pg.mkPen("#666666", width=1, style=Qt.DashLine))
            self.plots[axis_index].addItem(line)

    def add_measured_y_limit_lines(self, axis_index):
        """No physical y2 limit lines are drawn on normalized y_z plots."""
        return

    def disable_auto_si_prefix(self, axis_index):
        """Show literal decimal values on d/y axes instead of SI multipliers."""
        if axis_index >= len(self.plots):
            return
        try:
            self.plots[axis_index].getAxis("left").enableAutoSIPrefix(False)
        except Exception:
            pass

    def fix_axis_to_measured_y_bounds(self, axis_index):
        """Leave normalized d/y axes on automatic scaling."""
        return

    def maybe_legend(self, axis_index):
        if axis_index < len(self.plots):
            self.plots[axis_index].addLegend(offset=(8, 8))

    def plot_data(self, columns, data, file_name, dt_txt):
        t_idx = column_index(columns, "t") or 0
        t = data[:, t_idx]
        if file_name.startswith("data_uy"):
            self.plot_plant_data(columns, data, t, dt_txt)
        elif file_name.startswith("training_controller"):
            self.plot_controller_training_trace(columns, data, t, file_name, dt_txt)
        elif file_name.startswith("eval_"):
            self.plot_eval_data(columns, data, t, file_name, dt_txt)
        elif file_name.startswith("bibs_controller"):
            self.plot_controller_bibs(columns, data, t, file_name, dt_txt)
        elif file_name.startswith("bibs_plant"):
            self.plot_plant_bibs(columns, data, t, file_name, dt_txt)
        else:
            self.plot_generic(columns, data, t, file_name, dt_txt)
        self.auto_range_all()

    def plot_plant_data(self, columns, data, t, dt_txt):
        run_meta = self.current_result_metadata()
        model_name = str(run_meta.get("plant_model_name", "")).strip()
        try:
            meta = plant_signal_metadata(model_name)
            labels = {"u": meta["input"][1], "y": meta["output"][1]}
            labels.update({key: label for key, label, _unit in meta["signals"]})
            units = {"u": meta["input"][2], "y": meta["output"][2]}
            units.update({key: unit for key, _label, unit in meta["signals"]})
            title = plant_display_name(model_name)
        except Exception:
            labels = {key: key for key in columns}
            units = {key: "-" for key in columns}
            title = plant_display_name(model_name) if model_name else "Physical plant (saved result)"

        # State explicitly whether module 01 generated the physical plant
        # directly or through the inner proportional regulator.  Only metadata
        # attached to the displayed result is allowed to affect the title.
        if "preg_blackbox_enabled" in run_meta:
            preg_enabled = bool(run_meta.get("preg_blackbox_enabled", False))
            preg_description = "Plant with P-reg" if preg_enabled else "Plant without P-reg"
            title = f"{title} -- {preg_description}"

        signal_columns = [key for key in columns if key != "t"]
        ordered_signal_columns = []
        for preferred_key in ("u", "y"):
            if preferred_key in signal_columns:
                ordered_signal_columns.append(preferred_key)
        ordered_signal_columns.extend([key for key in signal_columns if key not in ordered_signal_columns])
        signal_columns = ordered_signal_columns
        ylabels = [plant_signal_symbol(model_name, key) for key in signal_columns]
        xlabel = f"t [sec], dt={dt_txt}"
        self.clear_and_make_vertical_plots(title, ylabels, xlabel)

        # Module 01 uses physical signal symbols, which are often wider than
        # the compact labels used by modules 02--04.  CompactYAxis has a fixed
        # default width; with these wider labels Qt can consume the available
        # axis space and suppress/clip the numeric y tick labels.  Reserve
        # explicit space for both the rotated physical symbol and tick text.
        for axis_index, plot in enumerate(self.plots):
            try:
                axis = plot.getAxis("left")
                axis.enableAutoSIPrefix(False)
                axis.setStyle(
                    autoExpandTextSpace=True,
                    tickTextWidth=76,
                    tickTextHeight=16,
                    showValues=True,
                    maxTextLevel=0,
                    hideOverlappingLabels=False,
                    textFillLimits=[(0, 10.0)],
                )
                axis.setWidth(118)
                axis.show()
            except Exception:
                pass

        for axis_index, key in enumerate(signal_columns):
            if key == "y":
                color = "g"
            elif key == "u":
                color = "b"
            else:
                color = "k"
            item = self.add_curve_to_axis(axis_index, columns, data, t, key, color, step_mode=False)
            if item and key == "y":
                idx_y = column_index(columns, key)
                if idx_y is not None:
                    x_y, values_y = finite_xy(t, data[:, idx_y])
                    if len(x_y):
                        point_size = max(1.0, 1.5 * self.line_width)
                        point_edge_width = max(0.35, 0.3 * self.line_width)
                        sample_item = self.plots[axis_index].plot(
                            x_y, values_y, pen=None, symbol="o", symbolSize=point_size,
                            symbolPen=pg.mkPen("b", width=point_edge_width),
                            symbolBrush=pg.mkBrush("b")
                        )
                        self.optimize_curve_item(sample_item, allow_downsampling=False)
            idx = column_index(columns, key)
            if item and idx is not None:
                values = np.asarray(data[:, idx], dtype=float)
                values = values[np.isfinite(values)]
                if values.size:
                    lo = float(np.min(values)); hi = float(np.max(values))
                    if not lo < hi:
                        pad = max(1.0, abs(lo)) * 0.05
                    else:
                        pad = 0.05 * (hi - lo)
                    plot = self.plots[axis_index]
                    plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
                    plot.setYRange(lo - pad, hi + pad, padding=0.0)
                    self.fixed_y_ranges[id(plot)] = (lo - pad, hi + pad)

    def plant_bibs_title(self, file_name):
        if "LNU_batch" in file_name:
            return "Plant LNU batch Ridge, BIBS spectral radii"
        if "LNU_gd_ngd" in file_name:
            return "Plant LNU GD/NGD, BIBS spectral radii"
        if "LNU_lm" in file_name:
            return "Plant LNU Levenberg-Marquardt, BIBS spectral radii"
        if "QNU_batch" in file_name:
            return "Plant QNU batch Ridge, BIBS spectral radii"
        if "QNU_gd_ngd" in file_name:
            return "Plant QNU GD/NGD, BIBS spectral radii"
        if "QNU_lm" in file_name:
            return "Plant QNU Levenberg-Marquardt, BIBS spectral radii"
        return "Plant BIBS spectral radii"

    def plot_plant_bibs(self, columns, data, t, file_name, dt_txt):
        # rho(A_w) is meaningful as the actual sample-wise weight-update map
        # only for GD/NGD. Batch Ridge and L-M have no such update in time, so
        # their BIBS tab displays only the exact local output dynamics rho(A_y).
        iterative_weights = "gd_ngd" in file_name.lower()
        ylabels = ["rho(A_w)", "rho(A_y(k))"] if iterative_weights else ["rho(A_y(k))"]
        xlabel = f"t [sec], dt={dt_txt}"
        self.clear_and_make_vertical_plots(self.plant_bibs_title(file_name), ylabels, xlabel)
        if iterative_weights:
            self.add_curve_to_axis(0, columns, data, t, "Rho_Aw", "k")
            self.add_curve_to_axis(0, columns, data, t, "Rho_w", "k")
            self.add_limit_line(0, 1.0)
            ay_axis = 1
        else:
            ay_axis = 0
        self.add_curve_to_axis(ay_axis, columns, data, t, "Rho_Ay", "k")
        self.add_curve_to_axis(ay_axis, columns, data, t, "Rho_y", "k")
        self.add_limit_line(ay_axis, 1.0)

    def controller_pair_from_file(self, file_name):
        match = re.search(r"(LNU|QNU)_(LNU|QNU)", file_name)
        if match:
            return match.group(1), match.group(2)
        run_meta = self.current_result_metadata()
        return (
            str(run_meta.get("gui_honu_plant", "saved HONU")),
            str(run_meta.get("gui_controller_model", "saved")),
        )

    def _column_data_range(self, columns, data, names):
        vals = []
        for name in names:
            idx = column_index(columns, name)
            if idx is None:
                continue
            arr = np.asarray(data[:, idx], dtype=float)
            arr = arr[np.isfinite(arr)]
            if arr.size:
                vals.append(arr)
        if not vals:
            return None
        merged = np.concatenate(vals)
        return float(np.min(merged)), float(np.max(merged))

    def _set_fixed_y_range(self, axis_index, lo, hi, pad_ratio=0.05, min_pad=1e-9):
        if axis_index < 0 or axis_index >= len(self.plots):
            return
        if not np.isfinite(lo) or not np.isfinite(hi):
            return
        if hi <= lo:
            pad = max(min_pad, 0.05 * max(1.0, abs(lo)))
        else:
            pad = max(min_pad, pad_ratio * (hi - lo))
        plot = self.plots[axis_index]
        fixed = (float(lo - pad), float(hi + pad))
        try:
            plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
            plot.setYRange(fixed[0], fixed[1], padding=0.0)
        except Exception:
            return
        self.fixed_y_ranges[id(plot)] = fixed

    def plot_controller_training_trace(self, columns, data, t, file_name, dt_txt):
        plant, controller = self.controller_pair_from_file(file_name)
        title = f"{plant} plant + {controller} controller training response and parameters"
        ylabels = ["d", "y, y_ref", "e_ref", "v", "r_0"]
        xlabel = f"training time t [sec], dt={dt_txt}"
        self.clear_and_make_vertical_plots(title, ylabels, xlabel)
        self.disable_auto_si_prefix(0)
        self.disable_auto_si_prefix(1)
        self.add_curve_to_axis(0, columns, data, t, "d", "b", label="training d", step_mode="right")
        self.maybe_legend(0)
        self.maybe_legend(1)
        self.add_curve_to_axis(1, columns, data, t, "y_ref", "b", label="y_ref")
        self.add_curve_to_axis(1, columns, data, t, "y", "g", label="y")
        self.add_curve_to_axis(2, columns, data, t, "e_ref", "r")
        v_cols = [c for c in columns if re.fullmatch(r"v_\d+", c)]
        for c in v_cols:
            self.add_curve_to_axis(3, columns, data, t, c, "k", width=max(1, self.line_width - 1))
        self.add_curve_to_axis(4, columns, data, t, "r_0", "b")

        d_range = self._column_data_range(columns, data, ["d"])
        if d_range is not None:
            self._set_fixed_y_range(0, d_range[0], d_range[1], pad_ratio=0.02)
        yy_range = self._column_data_range(columns, data, ["y_ref", "y"])
        if yy_range is not None:
            self._set_fixed_y_range(1, yy_range[0], yy_range[1], pad_ratio=0.05)
        e_range = self._column_data_range(columns, data, ["e_ref"])
        if e_range is not None:
            self._set_fixed_y_range(2, e_range[0], e_range[1], pad_ratio=0.05)
        r0_range = self._column_data_range(columns, data, ["r_0"])
        if r0_range is not None:
            self._set_fixed_y_range(4, r0_range[0], r0_range[1], pad_ratio=0.05)

    def controller_training_trace_file_from_bibs(self, bibs_file_name):
        if str(bibs_file_name).startswith("bibs_controller_"):
            return str(bibs_file_name).replace("bibs_controller_", "training_controller_", 1)
        return ""

    def controller_training_epoch_count(self, file_name):
        _plant, controller = self.controller_pair_from_file(file_name)
        run_meta = self.current_result_metadata()
        if controller == "QNU":
            epochs = int(run_meta.get("ctrl_qnu_epochs", 0))
        else:
            epochs = int(run_meta.get("ctrl_epochs", 0))
        return max(0, epochs)

    def controller_training_rmse_history(self, bibs_file_name):
        trace_file = self.controller_training_trace_file_from_bibs(bibs_file_name)
        if not trace_file:
            return None, None
        loaded = self.load_table_if_exists(trace_file)
        if loaded is None:
            return None, None
        trace_columns, trace_data = loaded
        e_idx = column_index(trace_columns, "e_ref")
        if e_idx is None:
            return None, None
        epochs = self.controller_training_epoch_count(bibs_file_name)
        sample_count = int(trace_data.shape[0])
        if epochs <= 0:
            # Legacy traces have no sidecar metadata, but each epoch restarts
            # its local time axis. Infer the count from those immutable resets
            # instead of consulting the current epoch widget.
            t_idx = column_index(trace_columns, "t")
            if t_idx is not None and sample_count > 1:
                t_values = np.asarray(trace_data[:, t_idx], dtype=float)
                finite_pairs = np.isfinite(t_values[:-1]) & np.isfinite(t_values[1:])
                resets = np.sum((np.diff(t_values) < 0.0) & finite_pairs)
                if resets > 0:
                    epochs = int(resets) + 1
        if epochs <= 0 or sample_count <= 0 or epochs > sample_count:
            return None, None

        base_len = sample_count // epochs
        remainder = sample_count % epochs
        if base_len <= 0:
            return None, None

        rmse = []
        start = 0
        for epoch in range(epochs):
            segment_len = base_len + (1 if epoch < remainder else 0)
            stop = start + segment_len
            e_epoch = np.asarray(trace_data[start:stop, e_idx], dtype=float)
            finite = np.isfinite(e_epoch)
            if np.any(finite):
                rmse.append(float(np.sqrt(np.mean(e_epoch[finite] ** 2))))
            else:
                rmse.append(np.nan)
            start = stop
        epoch_axis = np.arange(1, epochs + 1, dtype=float)
        return epoch_axis, np.asarray(rmse, dtype=float)

    def plot_controller_bibs(self, columns, data, t, file_name, dt_txt):
        # Matrix-norm and scalar |A_r0| columns remain in the saved files for
        # compatibility and offline diagnostics. The GUI displays the spectral
        # radii and, below them, the controller-training RMSE per epoch.
        plant, controller = self.controller_pair_from_file(file_name)
        title = f"{plant} plant + {controller} controller training, BIBS spectral radii + RMSE"
        ylabels = ["rho(A_v)", "rho(M)", "RMSE"]
        self.clear_and_make_vertical_plots(title, ylabels, "epoch")

        # Top two plots share the training-time axis coming from the BIBS file.
        self.add_curve_to_axis(0, columns, data, t, "Rho_Av", "k")
        self.add_curve_to_axis(0, columns, data, t, "Rho_v", "k")
        self.add_limit_line(0, 1.0)
        self.add_curve_to_axis(1, columns, data, t, "Rho_M", "k")
        self.add_curve_to_axis(1, columns, data, t, "Rho", "k")
        self.add_limit_line(1, 1.0)

        # The bottom plot is indexed strictly by epoch, not by training time.
        if len(self.plots) >= 3:
            rmse_plot = self.plots[2]
            try:
                rmse_plot.setXLink(None)
                rmse_plot.getViewBox().setXLink(None)
            except Exception:
                pass

            self.plots[1].setLabel("bottom", f"training time t [sec], dt={dt_txt}")
            rmse_plot.setLabel("left", "RMSE")
            rmse_plot.setLabel("bottom", "epoch")

            epoch_axis, rmse = self.controller_training_rmse_history(file_name)
            if epoch_axis is not None and rmse is not None:
                x_epoch, y_rmse = finite_xy(epoch_axis, rmse)
                if len(x_epoch):
                    pen = pg.mkPen(color="b", width=self.line_width)
                    item = rmse_plot.plot(
                        x=x_epoch,
                        y=y_rmse,
                        pen=pen,
                        symbol="o",
                        symbolSize=5,
                        symbolPen=pen,
                        name="RMSE",
                    )
                    self.optimize_curve_item(item, allow_downsampling=False)
                    rmse_plot.setXRange(1.0, float(max(1.0, x_epoch[-1])), padding=0.02)
                    self.maybe_legend(2)

    def plot_eval_data(self, columns, data, t, file_name, dt_txt):
        plant, controller = self.controller_pair_from_file(file_name)
        run_meta = self.current_result_metadata()
        model_name = str(run_meta.get("plant_model_name", "")).strip()
        physical_title = plant_display_name(model_name) if model_name else "Physical plant (saved result)"
        title = (
            physical_title + "\n" +
            f"Module 04 trained HONU validation: controller trained with "
            f"{plant} HONU plant + {controller} controller"
        )
        xlabel = f"physical plant time t [sec], dt={dt_txt}"
        self.clear_and_make_vertical_plots(
            title,
            ["d, y_ref, y", "u", "controller weights v", "r_0", "rho(A_v), |A_r0|", "rho(M)"],
            xlabel,
        )
        self.disable_auto_si_prefix(0)
        # Current module-04 files already contain physical d, y_ref and y.
        # Legacy files may contain d_z, y_ref_z and y_z; convert those copies
        # before plotting, never changing the stored result or internal model data.
        plot_columns = list(columns)
        plot_data = np.asarray(data, dtype=float)
        if column_index(plot_columns, "d") is None:
            stats = load_stats(BASE_DIR / "data" / "simulated_normalization.npz")
            extras = []
            names = []
            for physical_name, normalized_name in (("d", "d_z"), ("y_ref", "y_ref_z"), ("y", "y_z")):
                idx = column_index(plot_columns, normalized_name)
                if idx is not None:
                    extras.append(denormalize_y(plot_data[:, idx], stats))
                    names.append(physical_name)
            if extras:
                plot_data = np.column_stack([plot_data] + extras)
                plot_columns.extend(names)
        self.add_curve_to_axis(0, plot_columns, plot_data, t, "d", "k", label="d", step_mode="right")
        self.add_curve_to_axis(0, plot_columns, plot_data, t, "y_ref", "m", label="y_ref")
        self.add_curve_to_axis(0, plot_columns, plot_data, t, "y", "g", label="y")
        self.maybe_legend(0)
        self.add_curve_to_axis(1, plot_columns, plot_data, t, "u_physical", "b", label="u")
        self.maybe_legend(1)

        v_cols = [c for c in plot_columns if re.fullmatch(r"v_\d+", c)]
        for c in v_cols:
            self.add_curve_to_axis(2, plot_columns, plot_data, t, c, "k", width=max(1, self.line_width - 1))
        self.add_curve_to_axis(3, plot_columns, plot_data, t, "r_0", "b", label="r_0")
        self.maybe_legend(3)
        self.add_curve_to_axis(4, plot_columns, plot_data, t, "Rho_Av", "k", label="rho(A_v)")
        self.add_curve_to_axis(4, plot_columns, plot_data, t, "A_abs_r_0", "r", label="|A_r0|")
        self.add_limit_line(4, 1.0)
        self.maybe_legend(4)
        self.add_curve_to_axis(5, plot_columns, plot_data, t, "Rho_M", "k", label="rho(M)")
        self.add_limit_line(5, 1.0)
        self.maybe_legend(5)

        top_range = self._column_data_range(plot_columns, plot_data, ["d", "y_ref", "y"])
        if top_range is not None:
            self._set_fixed_y_range(0, top_range[0], top_range[1], pad_ratio=0.05)
        u_range = self._column_data_range(plot_columns, plot_data, ["u_physical"])
        if u_range is not None:
            self._set_fixed_y_range(1, u_range[0], u_range[1], pad_ratio=0.05)
        r0_range = self._column_data_range(plot_columns, plot_data, ["r_0"])
        if r0_range is not None:
            self._set_fixed_y_range(3, r0_range[0], r0_range[1], pad_ratio=0.05)

    def plot_generic(self, columns, data, t, file_name, dt_txt):
        ylabels = columns[1: min(8, len(columns))]
        if not ylabels:
            ylabels = ["value"]
        xlabel = f"t [sec], dt={dt_txt}"
        self.clear_and_make_vertical_plots(file_name, ylabels, xlabel)
        colors = ["b", "g", "r", "k", "m", "c", "#666666"]
        for i, col in enumerate(ylabels):
            self.add_curve_to_axis(i, columns, data, t, col, colors[i % len(colors)])

    def optimize_curve_item(self, item, allow_downsampling=True):
        if item is None:
            return
        try:
            item.setClipToView(True)
        except Exception:
            pass
        try:
            if allow_downsampling:
                item.setDownsampling(auto=True, method="mean")
            else:
                item.setDownsampling(ds=1, auto=False)
        except Exception:
            pass

    def current_tab_plots(self):
        if hasattr(self, "graph_tabs") and self.graph_tabs.currentWidget() is not None:
            widget = self.graph_tabs.currentWidget()
            return self.tab_plots.get(widget, self.plots)
        return self.plots

    def auto_range_all(self):
        for p in self.current_tab_plots():
            try:
                p.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
                p.autoRange()
                fixed_range = self.fixed_y_ranges.get(id(p))
                if fixed_range is not None:
                    p.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
                    p.setYRange(fixed_range[0], fixed_range[1], padding=0.0)
                p.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            except Exception:
                pass
        self.store_initial_ranges()

    def store_initial_ranges(self):
        self.initial_ranges = {}
        for widget, plots in self.tab_plots.items():
            ranges = []
            for p in plots:
                try:
                    ranges.append(p.getViewBox().viewRange())
                except Exception:
                    ranges.append(None)
            self.initial_ranges[widget] = ranges

    def reset_current_graph_ranges(self):
        plots = self.current_tab_plots()
        widget = self.graph_tabs.currentWidget() if hasattr(self, "graph_tabs") else None
        ranges = self.initial_ranges.get(widget, [])
        if not plots:
            return
        if len(ranges) != len(plots) or any(r is None for r in ranges):
            self.auto_range_all()
            return
        for p, rng in zip(plots, ranges):
            try:
                p.setRange(xRange=rng[0], yRange=rng[1], padding=0.02)
                p.getViewBox().setMouseMode(pg.ViewBox.RectMode)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------

    def append_log(self, text):
        if not hasattr(self, "log"):
            return
        timestamp = time.strftime("%H:%M:%S")
        for line in str(text).splitlines():
            self.log.append(f"[{timestamp}] {line}")
        self.log.moveCursor(QTextCursor.End)

    def clear_log(self):
        self.log.clear()

    def closeEvent(self, event):
        """Stop child processes before Qt destroys their QProcess wrappers."""
        processes = []
        if isinstance(getattr(self, "process", None), QProcess):
            processes.append(self.process)
        mpc_page = getattr(self, "mpc_page", None)
        if mpc_page is not None and isinstance(getattr(mpc_page, "process", None), QProcess):
            processes.append(mpc_page.process)
        for process in processes:
            if process.state() != QProcess.NotRunning:
                process.terminate()
                if not process.waitForFinished(1200):
                    process.kill()
                    process.waitForFinished(1200)
        super().closeEvent(event)

# =============================================================================
# Application entry point
# =============================================================================


def main():
    pg.setConfigOptions(antialias=True, foreground="k", background="w")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f2f5f8"))
    palette.setColor(QPalette.WindowText, QColor("#111827"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#eef2f7"))
    palette.setColor(QPalette.Text, QColor("#111827"))
    palette.setColor(QPalette.Button, QColor("#f7f9fc"))
    palette.setColor(QPalette.ButtonText, QColor("#111827"))
    app.setPalette(palette)

    win = MainWindow()
    win.apply_light_style()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
