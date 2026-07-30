# Python module structure

The general HONU MPC implementation uses only two MPC-specific Python modules:

- `HONU_MPC_runner.py`: numerical simulation, initial excitation, fixed PCA basis, sliding-window HONU identification, and MPC optimization. It is launched as a separate process so the GUI remains responsive and `Stop` can terminate the computation.
- `honu_basis.py`: canonical LNU/QNU feature definitions shared by MRAC and MPC. QNU contains only the unique triangular products with the bias included exactly once.

The older standalone photobioreactor LNU and QNU MPC demonstration scripts were removed because their functionality is covered by the model-independent runner.
