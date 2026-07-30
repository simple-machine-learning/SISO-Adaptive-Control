# Automatic Numba ODE backend

The physical-plant interface is unchanged. GUI and plotting files are untouched.
For ZOH integration, the backend attempts to compile the original Python model
source automatically with Numba in nopython mode. Numeric dataclass parameters
are mapped to a generated typed jitclass; no second copy of model equations is
maintained.

Models unsupported by Numba continue through the existing compiled Cython RK4
and compiled Cython model module. There is no pure-Python/SciPy runtime fallback.
P-feedback integration remains on the compiled Cython backend because controlled
output evaluation is model-specific.

Validation: 21/37 models compile automatically with Numba. Their maximum absolute
one-interval difference against the compiled Cython reference was
1.1102230246251565e-16. The remaining models are handled by Cython.
