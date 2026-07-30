# MPC MLP target selection

- LNU and QNU use absolute-output identification only.
- The GUI disables the target selector for LNU/QNU and forces `prediction_target=absolute`.
- MLP supports both `absolute` and `delta` targets for recursive and direct multi-horizon prediction.
- MLP target selection is stored in the fitted model and used consistently in prediction and Jacobian evaluation.
- Legacy configurations requesting delta for LNU/QNU are normalized to absolute in the runner.
