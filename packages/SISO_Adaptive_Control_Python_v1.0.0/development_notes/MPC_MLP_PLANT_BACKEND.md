# MPC MLP plant backend

The simulated-data MPC now supports `MLP` in addition to `LNU` and `QNU` as the identified plant predictor.

The MLP is a residual NARX predictor

`y[k+1] = y[k] + MLP(y-history, u-history)`

with two tanh hidden layers. Default dimensions are 32 and 32 neurons. Training uses Adam and the MPC rollout uses the exact analytic derivative of the MLP output with respect to its input regressor. This derivative is propagated through the recursive horizon by the existing MPC Jacobian machinery.

Supported prediction modes:

- Recursive one-step
- Recursive rollout use in MPC

Direct multi-horizon mode is intentionally rejected for MLP. Frozen-model save/load and frozen MPC execution are supported. Sliding retraining reuses the same MLP fitting backend.

The MLP option is currently added to the simulated-data MPC page. MRAC plant/controller selections remain LNU/QNU.

## Direct multi-horizon extension

MLP also supports `Direct multi-horizon`: one residual network has Np outputs and receives the whole candidate future control sequence. MPC uses SLSQP with numerical objective differentiation and shifted warm starts. This model is specific to the selected Np.
