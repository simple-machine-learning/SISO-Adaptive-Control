# HONU MPC GUI: visible P regulator, shared graph titles, zoom-preserving line width

- Replaced the hidden MPC ODE plant-mode combo box with a visible `Use P regulator` checkbox and `r_Preg` in the Simulation parameter row, aligned with the MRAC GUI.
- The same checkbox controls both physical ODE simulation and sliding-window HONU MPC runs.
- Each MPC result tab now has one shared title above the complete graph block rather than a title on an individual axis.
- The response title includes the physical plant, HONU type, standalone/P-regulated mode, `r_Preg` when enabled, sampling times, and MPC horizon where applicable.
- Changing `line width [px]` redraws existing curves while preserving the current x/y zoom ranges and the stored double-click reset ranges.
- Full-screen copies also display the shared graph title.
