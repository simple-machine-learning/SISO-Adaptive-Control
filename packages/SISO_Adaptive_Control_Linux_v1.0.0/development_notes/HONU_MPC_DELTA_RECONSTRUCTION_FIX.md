# HONU MPC delta reconstruction fix

For LNU/QNU models trained with `prediction_target=delta`, all identification plots, recursive prediction paths, and direct multi-horizon diagnostics now reconstruct the absolute output as `y_hat(k+j)=y(k)+Delta y_hat(k+j)` where applicable. The no-Jacobian rollout path now uses the same residual reconstruction as the Jacobian path. Direct-model local spectral-radius diagnostics include the unit residual derivative with respect to the current output.
