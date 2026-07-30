# Exact local rho(A_y) in MRAC and MPC

- QNU rho(A_y(k)) is evaluated exactly at every available regressor sample from the analytic QNU basis Jacobian.
- LNU rho(A_y) uses the exact autoregressive companion matrix.
- Batch Ridge and L-M do not display rho(A_w), because no sample-wise weight update A_w is executed by those algorithms.
- MRAC GD/NGD retains rho(A_w(k)) because its weight-update map is actually applied sample by sample.
- MPC identify, frozen and sliding modes store and plot the exact local rho(A_y(k)) trajectory. Frozen QNU can vary with k because the regressor changes although the weights are fixed.
