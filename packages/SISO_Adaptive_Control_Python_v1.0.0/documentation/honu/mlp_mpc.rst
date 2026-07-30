MLP in MPC
==========

Scope
-----

This chapter documents what the multilayer perceptron (MLP) backend does in
this software. It does not introduce general neural-network theory. In the
**HONU MPC** page, selecting ``MLP`` replaces the LNU/QNU plant predictor by a
nonlinear feed-forward prediction model. The physical plant, MPC objective,
input bounds, receding-horizon application of the first optimized move and the
frozen/sliding execution modes remain the same.

The implementation is primarily in:

* ``apps/simulated/HONU_MPC_runner.py`` for simulated plants,
* ``apps/measured/HONU_MPC_runner.py`` for measured-data operation,
* ``apps/simulated/HONU_MRAC_GUI_PySide6.py`` and
  ``apps/measured/HONU_MRAC_GUI_PySide6.py`` for GUI configuration,
* ``common/mlp_native.py`` and the native MLP backend, when present, for the
  accelerated recursive predictor and Jacobian.

Selection in the GUI
--------------------

Set **model** to ``MLP``. The GUI then changes the model-specific controls as
follows:

* **prediction** offers ``Recursive one-step`` and
  ``Direct multi-horizon + SLSQP``;
* **target** is fixed to ``Output increment``;
* **learning** offers ``Adam``, ``L-BFGS`` and ``Adam + L-BFGS``;
* **MLP hidden** accepts comma-separated positive hidden-layer widths, for
  example ``8`` or ``16,8``;
* **epochs** controls the number of optimizer epochs/iterations;
* **lambda** is the MLP L2 weight-regularization coefficient.

The MLP output width is automatic: one scalar in recursive mode and
:math:`N_p` values in direct multi-horizon mode.

Regressor and prediction target
-------------------------------

For recursive one-step identification, the raw regressor is

.. math::

   \boldsymbol{x}_k =
   \begin{bmatrix}
   y_k & \cdots & y_{k-n_y+1} &
   u_{k-n_{\tau_u}} & \cdots &
   u_{k-n_{\tau_u}-n_u+1}
   \end{bmatrix}^{\mathsf T}.

The MLP is trained on the output increment

.. math::

   \Delta y_{k+1}=y_{k+1}-y_k.

Its physical one-step prediction is therefore reconstructed as

.. math::

   \hat y_{k+1}=y_k+s_y\,f_{\boldsymbol{\theta}}(\boldsymbol{z}_k),

where :math:`f_{\boldsymbol{\theta}}` is the normalized MLP output,
:math:`s_y` is the stored target scale and :math:`\boldsymbol{z}_k` is the
preprocessed regressor.

In direct multi-horizon mode, one training sample contains the same history
block and the candidate future-input block required by the direct predictor.
The network is trained on

.. math::

   \begin{bmatrix}
   y_{k+1}-y_k & \cdots & y_{k+N_p}-y_k
   \end{bmatrix}^{\mathsf T},

and produces all :math:`N_p` future outputs in one forward pass:

.. math::

   \hat{\boldsymbol{y}}_{k+1:k+N_p}
   =y_k\boldsymbol{1}
   +s_y\,\boldsymbol{f}_{\boldsymbol{\theta}}(\boldsymbol{z}_k).

Preprocessing and PCA
---------------------

The MLP preprocessing differs from the HONU basis construction. The stored
output/input history coordinates are standardized first:

.. math::

   \boldsymbol{x}_{h,s}
   =\frac{\boldsymbol{x}_h-\boldsymbol{\mu}_h}
   {\boldsymbol{\sigma}_h}.

PCA directions are then obtained from the standardized history data and the
selected history representation is

.. math::

   \boldsymbol{z}_h
   =\boldsymbol{x}_{h,s}^{\mathsf T}\boldsymbol{P}.

``PCA mode = Rank`` retains all numerically independent history components.
``PCA mode = Variability`` retains the smallest number meeting the selected
cumulative variability. In direct multi-horizon mode, future candidate-input
coordinates are standardized separately and appended after the compressed
history coordinates; they are not included in the history PCA.

The fitted means, standard deviations, PCA matrix, retained rank and target
scale are stored with the identified model and reused during MPC prediction.

Implemented MLP architecture
----------------------------

The hidden layers use ``tanh`` activation and the output layer is linear. For
hidden widths :math:`h_1,\ldots,h_L`, the implemented map is

.. math::

   \boldsymbol{a}^{(1)}
   =\tanh\!\left(\boldsymbol{W}^{(1)}\boldsymbol{z}
   +\boldsymbol{b}^{(1)}\right),

.. math::

   \boldsymbol{a}^{(\ell)}
   =\tanh\!\left(\boldsymbol{W}^{(\ell)}
   \boldsymbol{a}^{(\ell-1)}+\boldsymbol{b}^{(\ell)}\right),

.. math::

   \boldsymbol{o}
   =\boldsymbol{W}^{(L+1)}\boldsymbol{a}^{(L)}
   +\boldsymbol{b}^{(L+1)}.

The output dimension is one for recursive identification and :math:`N_p` for
direct multi-horizon identification. Biases are included in every layer.

Training objective and optimizers
---------------------------------

The batch training objective is normalized mean-squared prediction error plus
L2 regularization of weight matrices:

.. math::

   \mathcal{L}(\boldsymbol{\theta})
   =\frac{1}{N}\sum_{i=1}^{N}
   \left\|\boldsymbol{o}_i-\boldsymbol{t}_i\right\|_2^2
   +\frac{\lambda}{2}\sum_{\ell}
   \left\|\boldsymbol{W}^{(\ell)}\right\|_{\mathrm{F}}^2.

Bias vectors are not included in the L2 term. The selectable optimizers are:

``Adam``
   Runs Adam for the selected number of epochs using the internal learning
   rate ``mlp_learning_rate``. The GUI currently supplies
   :math:`10^{-3}`.

``L-BFGS``
   Runs SciPy ``L-BFGS-B`` with the analytic batch gradient. **epochs** is
   used as the maximum iteration count.

``Adam + L-BFGS``
   Uses approximately half of **epochs** for Adam initialization and half for
   L-BFGS refinement. This is the GUI default when MLP is selected.

The training history stores physical-unit RMSE and the parameter vector after
each recorded optimizer step.

Recursive one-step mode
-----------------------

The scalar MLP is identified from one-step increments. During MPC, each
predicted output is inserted into the output-history part of the next
regressor. Consequently, the network is repeatedly evaluated over the
prediction horizon:

.. math::

   \hat y_{k+i+1|k}
   =\hat y_{k+i|k}
   +s_y f_{\boldsymbol{\theta}}
   \!\left(\boldsymbol{z}_{k+i|k}\right).

The software propagates the local input Jacobian through this recursion for
the MPC optimizer. Because model error is fed back into later regressors,
recursive validation is essential; a small one-step RMSE alone does not imply
a reliable long-horizon rollout.

The nonlinear local output-history diagnostic is the spectral radius of the
companion-form Jacobian whose first row is the MLP gradient with respect to
the :math:`n_y` output-history coordinates. It is reported as
:math:`\rho(A_y)`/local output spectral radius. It is a local diagnostic, not
a global stability guarantee.

On Linux builds that enforce native execution, recursive MLP prediction and
its Jacobian require the compiled MLP backend. The program deliberately does
not silently fall back to Python when that backend is required. The pure
Python Windows distribution uses its Python implementation.

Direct multi-horizon mode
-------------------------

The direct network has :math:`N_p` outputs and predicts the complete horizon
without feeding predicted outputs back into its own history. Candidate future
inputs are part of the direct model input, so each MPC objective evaluation
calls the network for the tested sequence.

For MLP direct multi-horizon control, the implemented optimizer is SciPy
``SLSQP`` with bounds ``u_min <= u <= u_max`` and at most ``opt_iter``
iterations. It minimizes the same tracking, input-increment,
second-increment and absolute-input penalties used elsewhere in MPC. This is
why the GUI labels this mode ``Direct multi-horizon + SLSQP``.

Direct prediction avoids recursive accumulation of output-prediction error,
but its output dimension and number of parameters grow with :math:`N_p`, and
a model trained for one horizon cannot be reused for a different horizon
without retraining.

Frozen and sliding-retraining operation
---------------------------------------

``MPC - Frozen Model``
   Identifies the MLP from the initial excitation record and keeps all MLP
   parameters and preprocessing fixed during the control run.

``MPC - Sliding Retraining``
   Rebuilds the MLP fit from the current sliding data window. The effective
   sample count is derived from ``window length [s]`` and ``dt MPC`` while
   respecting the history and horizon requirements. MLP weights and its
   stored preprocessing are updated by each fit.

Sliding MLP retraining is substantially more expensive than the closed-form
Ridge update used by LNU/QNU. Large networks, long windows, high epoch counts
and direct horizons can therefore make the GUI run noticeably slower.

MPC objective and applied action
--------------------------------

The MLP backend changes only the prediction map. The controller still
minimizes

.. math::

   J =
   Q\sum_{i=1}^{N_p}(\hat y_{k+i|k}-y_{\mathrm{ref},k+i})^2
   +R_{\Delta u}\sum_{i=0}^{N_p-1}(\Delta u_{k+i|k})^2
   +R_{\Delta^2u}\sum_{i=0}^{N_p-1}(\Delta^2u_{k+i|k})^2
   +R_u\sum_{i=0}^{N_p-1}u_{k+i|k}^2.

Only the first optimized input is applied. The remaining sequence is shifted
and used as the warm start for the next MPC sample.

Saved results and diagnostics
-----------------------------

The result files include, where applicable:

* ``training_epochs``, ``training_rmse`` and
  ``training_weight_history``;
* ``mlp_hidden_layers`` and the flattened parameter vector ``theta``;
* history means, standard deviations, PCA matrix, future-input scaling and
  ``mlp_target_scale``;
* ``prediction_mode``, ``prediction_target`` and ``mlp_optimizer``;
* local recursive spectral-radius data;
* direct predictions and errors by horizon, including direct RMSE and local
  sensitivity diagnostics;
* identification time and the complete identification configuration.

Practical interpretation of the controls
----------------------------------------

``n_y``, ``n_u``
   Set the output and delayed-input memory of the predictor. Larger values can
   represent slower dynamics but increase input dimension and data demand.

``MLP hidden``
   Sets hidden-layer widths. Increase only when validation indicates
   underfitting; unnecessary width increases optimization cost and variance.

``epochs``
   Sets the Adam/L-BFGS optimization budget for each fit. In sliding mode this
   cost is paid repeatedly.

``lambda``
   Sets L2 regularization of MLP weight matrices. Increasing it suppresses
   large weights but can underfit; decreasing it can improve fit while making
   the model more sensitive to limited or noisy data.

``PCA mode`` and ``PCA variability``
   Control compression of the standardized history coordinates. Excessive
   compression removes predictive information; retaining too many weak
   directions increases network size and conditioning burden.

``window length [s]``
   Sets the identification record for initial excitation and the retraining
   window in sliding operation. It must contain enough samples for the chosen
   memories and, in direct mode, the complete prediction horizon.

``Np``
   Sets both the MPC prediction horizon and the number of MLP outputs in
   direct mode. Changing it requires a new direct MLP fit.

Limitations specific to MLP MPC
-------------------------------

The MLP is an empirical local predictor. The software does not impose global
monotonicity, passivity or closed-loop stability constraints on the network.
Extrapolation outside the identification region can therefore be unreliable.
Input limits and soft MPC penalties do not replace plant-level safety logic.
Recursive mode can amplify small local model errors; direct mode avoids that
recursion but is horizon-specific and computationally heavier to train.
