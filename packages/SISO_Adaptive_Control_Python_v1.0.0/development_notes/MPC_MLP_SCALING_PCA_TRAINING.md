# MPC MLP scaling, PCA and training update

The MPC MLP plant now uses standardized input histories and optional PCA selected by the existing PCA controls. For direct multi-horizon MLP, PCA is applied only to the measured input-output history; the candidate future control sequence is standardized separately and is not mixed into the PCA basis.

The MLP predicts a standardized output increment and converts it back to physical units. Adam uses the GUI epoch count and L2 parameter. The final stored network is the epoch with the lowest physical training RMSE. Ridge and Levenberg-Marquardt remain HONU-only learning methods.
