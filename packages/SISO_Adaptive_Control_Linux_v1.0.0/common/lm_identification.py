# -*- coding: utf-8 -*-
"""Scale-aware Levenberg-Marquardt solver for HONU plant identification."""
from __future__ import annotations
import numpy as np


def solve_linear_lm(design, target, *, iterations, damping, damping_up=10.0,
                    damping_down=0.3, max_trials=12, tolerance=1.0e-12,
                    verbose=True):
    design = np.asarray(design, dtype=float)
    target = np.asarray(target, dtype=float).reshape(-1)
    if design.ndim != 2 or design.shape[0] != target.size:
        raise ValueError("design and target dimensions are inconsistent")
    if iterations <= 0 or damping <= 0.0:
        raise ValueError("LM iterations and damping must be positive")
    hessian = design.T @ design
    diagonal = np.maximum(np.diag(hessian), 1.0e-12)
    damping_matrix = np.diag(diagonal)
    weights = np.zeros(design.shape[1], dtype=float)
    residual = target - design @ weights
    sse = float(residual @ residual)
    current_damping = float(damping)
    weight_history = np.zeros((iterations, weights.size), dtype=float)
    sse_history = np.zeros(iterations, dtype=float)
    damping_history = np.zeros(iterations, dtype=float)
    for iteration in range(iterations):
        gradient = design.T @ residual
        accepted = False
        previous_sse = sse
        for _ in range(max_trials):
            system = hessian + current_damping * damping_matrix
            try:
                step = np.linalg.solve(system, gradient)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(system, gradient, rcond=None)[0]
            candidate = weights + step
            candidate_residual = target - design @ candidate
            candidate_sse = float(candidate_residual @ candidate_residual)
            if np.isfinite(candidate_sse) and candidate_sse < sse:
                weights = candidate
                residual = candidate_residual
                sse = candidate_sse
                current_damping = max(current_damping * damping_down, 1.0e-15)
                accepted = True
                break
            current_damping = min(current_damping * damping_up, 1.0e15)
        weight_history[iteration] = weights
        sse_history[iteration] = sse
        damping_history[iteration] = current_damping
        if verbose:
            print(f"LM iteration {iteration + 1}/{iterations}: SSE={sse:.12g}, lambda={current_damping:.12g}, accepted={accepted}", flush=True)
        if accepted and abs(previous_sse-sse) <= tolerance*max(1.0, previous_sse):
            weight_history[iteration+1:] = weights
            sse_history[iteration+1:] = sse
            damping_history[iteration+1:] = current_damping
            break
    if not np.all(np.isfinite(weights)):
        raise FloatingPointError("LM identification produced non-finite weights")
    return weights, weight_history, sse_history, damping_history
