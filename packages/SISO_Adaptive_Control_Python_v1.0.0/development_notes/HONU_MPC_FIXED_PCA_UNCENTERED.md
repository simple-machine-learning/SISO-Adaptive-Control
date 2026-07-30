# HONU MPC: fixed initial PCA basis with uncentered projection

The MPC plant HONU now uses one PCA/SVD basis computed from the initial identification window.

For basis construction only, the nonconstant canonical HONU feature matrix is centered:

Phi_c = Phi - mean(Phi).

The frozen projection P is obtained from the right singular vectors of Phi_c. The mean is not used in subsequent HONU fitting or prediction.

Every initial and sliding-window sample is transformed as

z = [1; P^T phi(x)],

where phi(x) contains no constant feature. Thus the only bias is x_0 = 1 and measured/HONU features are not shifted after the PCA basis has been determined.

The same frozen uncentered projection is used for batch fitting, sliding-window updates, MPC prediction, QNU/LNU derivatives and rho(A_y). PCA rank and singular values are stored in the NPZ output.
