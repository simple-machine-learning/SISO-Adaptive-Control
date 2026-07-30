MPC QNU PCA order and live line-width update
============================================

QNU identification now uses this order:
1. build the base regressor [y lags, u lags],
2. compute and freeze PCA on that base regressor,
3. project the uncentred base regressor into PCA coordinates,
4. prepend x_0 = 1,
5. construct the canonical QNU basis using unique pairs i <= j.

Therefore the QNU basis contains exactly one constant, exactly one copy of each
linear term, and exactly one copy of each quadratic/cross term.

The MPC line-width widget now redraws existing plots immediately when its value
changes; no new simulation or MPC run is required.
