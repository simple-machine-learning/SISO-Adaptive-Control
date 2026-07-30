# -*- coding: utf-8 -*-
"""Main launcher for the SISO Adaptive Control software."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

ROOT = Path(__file__).resolve().parent
APPS = ROOT / "apps"
COMMON = ROOT / "common"


class ModeCard(QFrame):
    def __init__(self, title: str, subtitle: str, description: str, button_text: str, callback):
        super().__init__()
        self.setObjectName("modeCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(13)

        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        sub = QLabel(subtitle)
        sub.setObjectName("cardSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        body = QLabel(description)
        body.setObjectName("cardBody")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(body, 1)

        button = QPushButton(button_text)
        button.setMinimumHeight(46)
        button.clicked.connect(callback)
        layout.addWidget(button)


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SISO Adaptive Control")
        self.setMinimumSize(1060, 690)

        menu_help = self.menuBar().addMenu("Help")
        action_about = QAction("About", self)
        action_about.triggered.connect(self.show_about)
        menu_help.addAction(action_about)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(44, 34, 44, 34)
        root.setSpacing(18)

        title = QLabel("SISO Adaptive Control")
        title.setObjectName("mainTitle")
        root.addWidget(title)

        intro = QLabel(
            "One software environment for learning, identification and control of "
            "single-input single-output systems using HONU plant models, MRAC and MPC."
        )
        intro.setObjectName("intro")
        intro.setWordWrap(True)
        root.addWidget(intro)

        cards = QHBoxLayout()
        cards.setSpacing(22)
        cards.addWidget(ModeCard(
            "Simulated systems",
            "Physical ODE plant → data → HONU model → controller",
            "Select a nonlinear physical plant, generate excitation and response data, "
            "identify an LNU or QNU model, train an MRAC controller, run closed-loop ODE "
            "tests, or investigate HONU-based MPC. This mode is intended for controlled "
            "experiments, comparison of learning methods and study of modelling and control concepts.",
            "Open simulated mode",
            lambda: self.launch_mode("simulated"),
        ), 1)
        cards.addWidget(ModeCard(
            "Measured systems",
            "Experimental file → channel selection → HONU model → controller",
            "Import measured SISO records, select and preprocess time, input and output channels, "
            "set the working sampling period, identify an LNU or QNU plant model, and use the "
            "same MRAC and MPC workflows on experimental data. This mode is intended for data-driven "
            "modelling, controller learning and analysis of real processes.",
            "Open measured mode",
            lambda: self.launch_mode("measured"),
        ), 1)
        root.addLayout(cards, 1)

        note = QLabel(
            "Both modes share the HONU basis, reference-signal generation and numerical learning utilities. "
            "Mode-specific data acquisition and plant execution remain separated to preserve their behaviour."
        )
        note.setObjectName("note")
        note.setWordWrap(True)
        root.addWidget(note)

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f4f6f8; color: #1f2933; }
            QLabel#mainTitle { font-size: 32px; font-weight: 700; }
            QLabel#intro { font-size: 16px; color: #52606d; padding-bottom: 8px; }
            QFrame#modeCard { background: white; border: 1px solid #cbd2d9; border-radius: 10px; }
            QLabel#cardTitle { font-size: 23px; font-weight: 650; }
            QLabel#cardSubtitle { font-size: 14px; font-weight: 600; color: #334e68; }
            QLabel#cardBody { font-size: 14px; line-height: 1.35; color: #3e4c59; }
            QLabel#note { color: #616e7c; font-size: 13px; padding-top: 4px; }
            QPushButton { background: #245b8a; color: white; border: 0; border-radius: 6px;
                          padding: 10px 18px; font-size: 14px; font-weight: 600; }
            QPushButton:hover { background: #1d4f7a; }
            QPushButton:pressed { background: #163f63; }
        """)

    def show_about(self) -> None:
        about_path = ROOT / "ABOUT.txt"
        try:
            about_text = about_path.read_text(encoding="utf-8").strip()
        except OSError:
            about_text = "SISO Adaptive Control"
        QMessageBox.information(self, "About", about_text)

    def launch_mode(self, mode: str) -> None:
        app_dir = APPS / mode
        script = app_dir / "HONU_MRAC_GUI_PySide6.py"
        if not script.exists():
            QMessageBox.critical(self, "Launch error", f"Application entry point not found:\n{script}")
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(COMMON) + (os.pathsep + existing if existing else "")
        try:
            subprocess.Popen([sys.executable, str(script)], cwd=str(app_dir), env=env)
        except OSError as exc:
            QMessageBox.critical(self, "Launch error", str(exc))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SISO Adaptive Control")
    app.setFont(QFont("Segoe UI", 10))
    window = Launcher()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
