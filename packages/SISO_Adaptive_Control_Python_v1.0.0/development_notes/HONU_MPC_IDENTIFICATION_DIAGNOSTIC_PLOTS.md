# HONU MPC identification diagnostic plots

The result of workflow step 2, Identify HONU Plant, now contains and plots:

1. physical output y and identified HONU one-step output y_n versus time,
2. excitation input u versus time,
3. identification residual e = y - y_n versus time,
4. training RMSE versus epoch,
5. all Plant HONU weights versus epoch.

Levenberg-Marquardt stores the full epoch histories. Ridge is represented by one final epoch point. The same five plots are copied to the full-screen graph window, including current view ranges and line-width behavior.
