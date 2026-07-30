# MRAC dataset validation and parameter layout fix

- Restored `MainWindow.current_data_path()` as the active module-01 dataset accessor used by MRAC steps 02-04.
- Dataset identity checks now proceed after module 01 instead of failing with a missing GUI attribute.
- Reordered the MRAC parameter rows to follow the MPC layout:
  - Simulation: `t_sim`, `u step width`, `tau_u`, `dt MRAC`, `dt_sim`, input range, P-regulator, line width.
  - Reference d: `d duration`, `d step width`, `tau_d`, `tau_1`, `tau_2`, reference range.
  - Plant HONU.
  - Controller learning.
- Connected `d duration` and `d step width` changes to automatic setup synchronization.
