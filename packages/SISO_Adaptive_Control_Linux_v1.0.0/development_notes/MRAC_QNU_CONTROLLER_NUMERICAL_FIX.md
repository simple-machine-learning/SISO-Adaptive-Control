# MRAC QNU controller numerical fix

The LNU-QNU and QNU-QNU module-03 scripts now evaluate NGD without forming
`g @ g`, `g_r_0**2`, or the dense matrix `I - eta*g*g.T`.

The mathematically equivalent scaled-norm form prevents floating-point
overflow for large but finite QNU sensitivities. The BIBS quantities are
computed from the exact rank-one eigenvalues, so no SVD is required.

No saturation or clipping of the controller output `u` was introduced.
Non-finite sensitivities are reported explicitly with epoch and sample index
instead of failing later with the misleading `SVD did not converge` error.
