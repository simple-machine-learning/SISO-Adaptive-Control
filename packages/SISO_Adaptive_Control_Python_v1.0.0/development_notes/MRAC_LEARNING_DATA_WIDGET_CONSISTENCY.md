# MRAC learning/data widget consistency

- Renamed `t_sim [s]` to `plant data duration [s]` because it controls the module-01 identification dataset length.
- Renamed `d duration [s]` to `controller/reference duration [s]` because it controls modules 03 and 04, not plant identification.
- Plant-learning controls now follow the selected algorithm:
  - Batch / Ridge: epochs and `mu_w` disabled; `ridge lambda` enabled.
  - Levenberg-Marquardt: iterations and `lambda_0` enabled; `mu_w` disabled.
  - GD/NGD: epochs and `mu_w` enabled; lambda disabled.
- Tooltips now distinguish plant dataset length, plant-identification iterations/epochs, and controller-training epochs.
