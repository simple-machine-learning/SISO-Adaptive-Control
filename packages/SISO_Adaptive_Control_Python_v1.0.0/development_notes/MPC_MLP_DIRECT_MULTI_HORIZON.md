# MPC direct multi-horizon MLP

The simulated MPC plant selector now supports MLP with `Direct multi-horizon` prediction.

A single residual MLP receives the measured output/input history together with the complete candidate control sequence and returns all Np predicted outputs in one forward pass:

`[y history, u history, U(k:k+Np-1)] -> [y(k+1|k), ..., y(k+Np|k)]`.

The network has two tanh hidden layers and Np linear outputs. It is trained by Adam on direct multi-step targets. The model is tied to the selected prediction horizon Np and must be identified again after Np changes.

For this predictor the MPC control sequence is found by SciPy SLSQP. SLSQP evaluates the true nonlinear MPC objective repeatedly and estimates the objective gradient numerically. The previous optimal sequence is shifted and reused as the warm start.

The existing recursive one-step and recursive rollout-trained MLP variants remain available. Local recursive rho(J_y(k)) is defined only for recursive MLP. For the direct model, the GUI retains the existing per-horizon local output-history sensitivity diagnostics; these are not recursive stability certificates.
