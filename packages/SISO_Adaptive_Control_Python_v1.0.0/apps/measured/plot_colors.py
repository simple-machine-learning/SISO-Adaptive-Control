# -*- coding: utf-8 -*-
"""Canonical signal colors for the measured-data HONU MRAC package."""
from __future__ import annotations

U_COLOR = "b"
YN_COLOR = "g"
Y_COLOR = "k"
Y_REF_COLOR = "m"

_FALLBACK_COLORS = ("b", "g", "r", "k", "m", "c", "#666666")


def _normalized(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def signal_color(name: str, fallback_index: int = 0) -> str:
    """Return the fixed color assigned to a named signal.

    The original project convention is preserved:
    ``u`` is blue, neural output ``y_n``/``yn`` is green, measured or plant
    output ``y`` is black, and ``y_ref`` is magenta/purple.
    """
    key = _normalized(name)

    if key in {"u", "u_cl", "u_meas", "u_measured"}:
        return U_COLOR
    if key in {"yn", "y_n", "yhat", "y_hat", "y_model", "y_est"}:
        return YN_COLOR
    if key in {"y", "y_cl", "y_meas", "y_measured"}:
        return Y_COLOR
    if key in {"y_ref", "yref"}:
        return Y_REF_COLOR

    return _FALLBACK_COLORS[int(fallback_index) % len(_FALLBACK_COLORS)]
