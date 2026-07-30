
MPC MLP optimization and HONU prediction-target update
=======================================================

The MPC plant-model GUI now exposes Adam, L-BFGS, and hybrid Adam + L-BFGS
training for MLP models. The iteration/epoch widget is shared by the selected
optimizer; in hybrid mode it is split between Adam initialization and L-BFGS
refinement.

LNU and QNU models now expose an independent prediction target: absolute output
or output increment. Increment models are trained on y[k+1]-y[k] and reconstruct
the physical prediction as y[k]+delta_y[k+1]. Recursive gradients and the local
spectral-radius diagnostic include the residual identity branch.
