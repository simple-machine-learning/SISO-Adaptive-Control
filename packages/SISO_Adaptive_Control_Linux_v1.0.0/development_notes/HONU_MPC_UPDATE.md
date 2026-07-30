# HONU MPC GUI update

`HONU_MRAC_GUI_PySide6.py` now contains two main tabs:

- `HONU MRAC`: the original MRAC page; its existing widget names and internal layout are retained.
- `HONU MPC`: generic sliding-window LNU/QNU identification and receding-horizon MPC.

The MPC page uses every physical ODE model listed by the original GUI. The local HONU is reidentified by batch ridge regression from the current sliding window at every MPC sample after initial excitation. The control input remains without hard amplitude or rate bounds; only soft objective penalties are used.

MPC plots include the closed-loop response, all current HONU weights, `rho(A_w)`, and local `rho(A_y)`. Diagnostic samples are stored once per HONU reidentification/MPC update. Time-axis labels state `dt MPC`, `dt sim`, or the HONU update sampling interval.

The numerical implementation is in `HONU_MPC_runner.py`; the GUI launches it as a separate process and reads an NPZ result file, so the GUI remains responsive during computation.
