Plant HONU: LNU and QNU
=======================

Purpose of the plant HONU
-------------------------

The plant HONU is a discrete-time, data-driven approximation of the controlled
SISO plant. It is not the physical ODE model itself. It maps a finite history of
measured outputs and delayed inputs to the next output sample and is subsequently
used as the differentiable plant model during MRAC-controller training and as the
prediction model in HONU MPC.

All identification and controller training are performed in normalized
coordinates. Physical units are recovered only for presentation and physical-ODE
validation. With the sampling period :math:`T_s=\mathtt{dt}` and the input delay

.. math::

   n_{u,1}=\left\lfloor\frac{\tau_u}{T_s}\right\rfloor,

an autoregressive plant regressor is formed as

.. math::

   \boldsymbol{x}(k)=
   \begin{bmatrix}
   1 & y(k-1) & \cdots & y(k-n_y) &
   u(k-n_{u,1}-1) & \cdots & u(k-n_{u,1}-n_u)
   \end{bmatrix}^{\mathsf T}.

The constant element is included in the current batch models and controller-
training models. Some legacy GD/NGD scripts use the unbiased form without the
constant element; the saved-file metadata and selected script therefore remain
part of the model definition.

LNU plant model
---------------

The linear neural unit uses the original regressor as its feature vector,

.. math::

   \boldsymbol{\phi}_{L}(k)=\boldsymbol{x}(k),
   \qquad
   \hat y(k)=\boldsymbol{w}^{\mathsf T}\boldsymbol{\phi}_{L}(k).

Partitioning the weight vector into the bias, output-memory and input-memory
parts gives

.. math::

   \hat y(k)=w_0+
   \sum_{i=1}^{n_y}w_{y,i}y(k-i)+
   \sum_{j=1}^{n_u}w_{u,j}u(k-n_{u,1}-j).

Thus the LNU is a finite-order ARX-like model that is linear in both its
parameters and regressors. It can represent offsets, local linear dynamics,
finite input delay and finite memory. It cannot directly represent products,
squares or operating-point-dependent gains unless these effects are encoded by
the input data or by additional regressors.

For :math:`n_x=1+n_y+n_u`, the LNU contains :math:`n_w=n_x` weights. The
recursive autonomous output part can be written using the companion state

.. math::

   \boldsymbol{y}_k=
   \begin{bmatrix}\hat y(k)&\hat y(k-1)&\cdots&\hat y(k-n_y+1)\end{bmatrix}^{\mathsf T},

.. math::

   \boldsymbol{y}_{k+1}=\boldsymbol{A}_y\boldsymbol{y}_k+
   \boldsymbol{b}_u(k),

where

.. math::

   \boldsymbol{A}_y=
   \begin{bmatrix}
   w_{y,1}&w_{y,2}&\cdots&w_{y,n_y}\\
   1&0&\cdots&0\\
   0&1&\ddots&\vdots\\
   \vdots&\ddots&\ddots&0
   \end{bmatrix}.

For fixed weights, :math:`\rho(\boldsymbol{A}_y)<1` is the usual discrete-time
local pole condition for the autonomous LNU model. During GD/NGD learning the
matrix varies with :math:`k`; its spectral radius is therefore a frozen-time
stability diagnostic, not a global proof for the complete adaptive loop.

QNU plant model
---------------

The quadratic neural unit applies all non-redundant second-order monomials to
the regressor. Let

.. math::

   \mathcal{P}=\{(i,j)\,|\,0\le i\le j<n_x\}.

The QNU feature vector and prediction are

.. math::

   \boldsymbol{\phi}_{Q}(k)
   =\left[x_i(k)x_j(k)\right]_{(i,j)\in\mathcal{P}},
   \qquad
   \hat y(k)=\boldsymbol{w}^{\mathsf T}\boldsymbol{\phi}_{Q}(k).

Because :math:`x_0=1`, this single upper-triangular basis contains the constant
term, all linear terms and all quadratic interactions. In scalar form,

.. math::

   \hat y(k)=
   w_{00}+
   \sum_{i=1}^{n_x-1}w_{0i}x_i(k)+
   \sum_{i=1}^{n_x-1}\sum_{j=i}^{n_x-1}w_{ij}x_i(k)x_j(k).

The number of trainable weights is

.. math::

   n_w=\frac{n_x(n_x+1)}{2}.

A QNU can represent quadratic static nonlinearities, cross-products between
past outputs and inputs, amplitude-dependent gains and a second-order local
Volterra-like approximation. Its parameter count grows quadratically with
regressor dimension, so collinearity, scaling and extrapolation become more
critical than for an LNU.

The exact feature derivative needed by recurrent controller learning and MPC is
straightforward. For one feature :math:`\phi_{ij}=x_i x_j`,

.. math::

   \frac{\partial\phi_{ij}}{\partial\boldsymbol{x}}
   =x_j\boldsymbol{e}_i+x_i\boldsymbol{e}_j,

with the diagonal case naturally giving
:math:`\partial x_i^2/\partial x_i=2x_i`. Consequently,

.. math::

   \frac{\partial\hat y}{\partial\boldsymbol{x}}
   =\boldsymbol{w}^{\mathsf T}
   \frac{\partial\boldsymbol{\phi}_{Q}}
   {\partial\boldsymbol{x}}.

This derivative propagates through delayed outputs and inputs and is the basis
of the exact local sensitivities used in controller training and prediction
optimization.

Requirements on identification trajectories
-------------------------------------------

The plant HONU can only be identified from trajectories that remain bounded
and operationally admissible. For an open-loop unstable plant, data acquisition
must therefore be performed under an independent stabilizing controller. The
training record must sufficiently excite the relevant dynamics while remaining
inside actuator, sensor and physical operating limits.

The learned mapping is data-supported rather than global. It is valid
primarily for amplitudes, rates, delays and operating conditions represented in
the training record. LNU provides a local linear dynamic approximation, while
QNU can capture moderate quadratic nonlinearities and interactions within the
same covered region. Neither model should be treated as a reliable extrapolator
for strongly nonlinear, discontinuous or previously unobserved regimes.

Identification problem
----------------------

For :math:`N` valid samples, stack the feature rows into

.. math::

   \boldsymbol{\Phi}=
   \begin{bmatrix}
   \boldsymbol{\phi}^{\mathsf T}(k_1)\\
   \vdots\\
   \boldsymbol{\phi}^{\mathsf T}(k_N)
   \end{bmatrix},
   \qquad
   \boldsymbol{y}=
   \begin{bmatrix}y(k_1)&\cdots&y(k_N)\end{bmatrix}^{\mathsf T}.

The one-step prediction error and least-squares objective are

.. math::

   e(k)=y(k)-\hat y(k),
   \qquad
   E(\boldsymbol{w})=\frac{1}{2}\sum_{k}e^2(k)
   =\frac{1}{2}\left\|\boldsymbol{y}-\boldsymbol{\Phi}\boldsymbol{w}\right\|_2^2.

Both LNU and QNU are nonlinear in their input variables but linear in their
weights. Therefore batch Ridge has a direct solution, while GD, NGD and L-M are
alternative numerical learning procedures for the same linear-in-parameters
identification problem. Their detailed derivations are given in
:doc:`learning_methods`.

Plant-model use and validation
------------------------------

A low one-step RMSE is necessary but not sufficient for recursive simulation or
control. The identified model must also be evaluated in free-run recursion,
under the intended reference range and with the same delay and normalization
used during training. The project therefore reports prediction error together
with local update-map and output-recursion spectral-radius diagnostics.

The plant HONU is trained from module-01 data, the controller is trained against
that fixed learned plant in module 03, and the final controller is validated
against the original physical ODE plant in module 04. For measured data, the
same distinction applies: controller training regulates the learned HONU
approximation, not an unobserved future physical experiment.
