# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False
"""Compiled C++ RK4 sampled-interval integrator for all plant models."""
import math
import numpy as np
cimport numpy as cnp

cnp.import_array()

cpdef tuple simulate_interval(object state, double u_command, double dt,
                              double dt_internal, object rhs,
                              object output_function=None,
                              bint preg=False, double r_preg=1.0,
                              object parameters=None):
    cdef cnp.ndarray[cnp.double_t, ndim=1] x = np.ascontiguousarray(state, dtype=np.float64).copy()
    cdef cnp.ndarray[cnp.double_t, ndim=1] k1, k2, k3, k4, tmp
    cdef Py_ssize_t i, j, n_state = x.shape[0]
    cdef int n_steps
    cdef double h, u1, u2, u3, u4, u_final

    if dt <= 0.0 or dt_internal <= 0.0:
        raise ValueError("dt and dt_internal must be positive")
    if n_state < 1:
        raise ValueError("state must not be empty")
    if preg and output_function is None:
        raise ValueError("output_function is required for P-feedback integration")

    n_steps = max(1, <int>math.ceil(dt / dt_internal))
    h = dt / n_steps

    for i in range(n_steps):
        u1 = r_preg * (u_command - float(output_function(x, parameters))) if preg else u_command
        k1 = np.asarray(rhs(0.0, x, u1, parameters), dtype=np.float64)

        tmp = x + 0.5 * h * k1
        u2 = r_preg * (u_command - float(output_function(tmp, parameters))) if preg else u_command
        k2 = np.asarray(rhs(0.0, tmp, u2, parameters), dtype=np.float64)

        tmp = x + 0.5 * h * k2
        u3 = r_preg * (u_command - float(output_function(tmp, parameters))) if preg else u_command
        k3 = np.asarray(rhs(0.0, tmp, u3, parameters), dtype=np.float64)

        tmp = x + h * k3
        u4 = r_preg * (u_command - float(output_function(tmp, parameters))) if preg else u_command
        k4 = np.asarray(rhs(0.0, tmp, u4, parameters), dtype=np.float64)

        x += (h / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)

    u_final = r_preg * (u_command - float(output_function(x, parameters))) if preg else u_command
    return np.asarray(x), u_final
