# MPC MLP local spectral-radius diagnostic

The recursive MLP plant now exposes the same trajectory diagnostic used by the
recursive QNU plant. For the history state

`[y(k), ..., y(k-ny+1)]`

the code evaluates the exact analytic MLP gradient with respect to the complete
base regressor, constructs the output-history companion Jacobian `J_y(k)`, and
stores

`rho_ay(k) = max(abs(eigvals(J_y(k))))`.

For LNU the matrix is constant and the GUI labels the quantity `rho(A_y)`. For
QNU and MLP it is state dependent and the GUI labels it `rho(J_y(k))`. Input
history is held fixed in this local output-recursion diagnostic. The existing
`rho_ay` data key is retained for backward compatibility.
