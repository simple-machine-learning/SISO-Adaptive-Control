# SISO Measured

Measured-data variant derived from SISO Simulated. Physical ODE models and ODE scripts are intentionally absent.

Data sources:
1. TXT/CSV/DAT tables
2. MATLAB v7.3 MAT
3. NPY/NPZ

The imported record is converted to the shared `data_uy.txt` dataset used by both MRAC and MPC. MPC validation evolves the trained HONU plant, not a physical ODE model.
