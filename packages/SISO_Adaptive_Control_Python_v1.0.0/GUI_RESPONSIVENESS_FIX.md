# GUI responsiveness fix

The MRAC and MPC GUIs now keep returning control to the Qt event loop during expensive result rendering.

Changes:

- completed MPC results are loaded on the next Qt event-loop cycle instead of directly inside the `QProcess.finished` callback;
- Qt events are serviced before, during, and after large plot updates;
- HONU weight-trajectory rendering yields periodically when many coefficient curves are present;
- line-width changes are debounced to avoid repeated complete NPZ reloads and redraws while editing the spin box;
- the numerical child process remains asynchronous through `QProcess`.

This addresses desktop "application is not responding" warnings caused by synchronous post-processing and plotting after a calculation. Numerical execution time is unchanged.
