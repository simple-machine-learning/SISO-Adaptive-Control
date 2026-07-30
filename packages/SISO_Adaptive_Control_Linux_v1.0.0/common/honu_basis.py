# -*- coding: utf-8 -*-
"""Canonical non-redundant LNU and QNU bases for plant and controller HONU."""
from __future__ import annotations
import numpy as np


def lnu_features(z):
    """LNU basis [z_0, ..., z_n], where the caller supplies z_0=1."""
    return np.asarray(z, dtype=float).reshape(-1)


def qnu_pairs(n):
    """Unique QNU index pairs (i,j), 0 <= i <= j < n."""
    return [(i, j) for i in range(int(n)) for j in range(i, int(n))]


def qnu_feature_count(n):
    n = int(n)
    return n * (n + 1) // 2


def qnu_features(z):
    """QNU basis [z_i*z_j] for 0 <= i <= j < n, each monomial once.

    With z_0=1 this contains bias z_0^2=1 and linear terms z_0*z_i=z_i,
    without adding separate duplicate constant or linear blocks.
    """
    z = np.asarray(z, dtype=float).reshape(-1)
    return np.asarray([z[i] * z[j] for i, j in qnu_pairs(z.size)], dtype=float)


def qnu_features_and_jacobian(z):
    """Canonical QNU basis and exact Jacobian d phi / d z."""
    z = np.asarray(z, dtype=float).reshape(-1)
    pairs = qnu_pairs(z.size)
    phi = np.empty(len(pairs), dtype=float)
    jac = np.zeros((len(pairs), z.size), dtype=float)
    for row, (i, j) in enumerate(pairs):
        phi[row] = z[i] * z[j]
        jac[row, i] += z[j]
        jac[row, j] += z[i]
    return phi, jac
