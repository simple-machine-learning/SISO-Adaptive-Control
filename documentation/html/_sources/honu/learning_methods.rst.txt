HONU learning: Ridge, GD, NGD, and L-M
======================================

Learning objective and notation
-------------------------------

For either an LNU or QNU plant, let

.. math::

   \hat y(k)=\boldsymbol{w}^{\mathsf T}\boldsymbol{\phi}(k),
   \qquad
   e(k)=y(k)-\hat y(k).

The instantaneous and batch losses are

.. math::

   E_k=\frac{1}{2}e^2(k),
   \qquad
   E=\sum_{k=1}^{N}E_k
   =\frac{1}{2}\left\|\boldsymbol{e}\right\|_2^2.

Since

.. math::

   \frac{\partial E_k}{\partial\boldsymbol{w}}
   =-e(k)\boldsymbol{\phi}(k),

all implemented plant-learning methods differ primarily in how this gradient is
scaled, accumulated or regularized.

Batch least squares and Ridge
-----------------------------

Without regularization, the stationary condition is

.. math::

   \boldsymbol{\Phi}^{\mathsf T}\boldsymbol{\Phi}\boldsymbol{w}
   =\boldsymbol{\Phi}^{\mathsf T}\boldsymbol{y}.

Ridge identification minimizes

.. math::

   E_R(\boldsymbol{w})=
   \frac{1}{2}\left\|\boldsymbol{y}-\boldsymbol{\Phi}\boldsymbol{w}\right\|_2^2
   +\frac{\lambda}{2}\left\|\boldsymbol{L}\boldsymbol{w}\right\|_2^2,

where :math:`\boldsymbol{L}` is normally the identity except that the bias may
be excluded from regularization. The solution is

.. math::

   \boldsymbol{w}=
   \left(\boldsymbol{\Phi}^{\mathsf T}\boldsymbol{\Phi}
   +\lambda\boldsymbol{L}^{\mathsf T}\boldsymbol{L}\right)^{-1}
   \boldsymbol{\Phi}^{\mathsf T}\boldsymbol{y}.

In numerical implementation the corresponding linear system should be solved
directly rather than explicitly forming the matrix inverse. Ridge is the
preferred deterministic baseline because the HONU is linear in its weights.
Increasing :math:`\lambda` improves conditioning and reduces weight magnitude,
but increases bias. For a QNU, stronger regularization is often necessary due
to the large and strongly correlated polynomial basis.

Gradient descent
----------------

A sample-by-sample GD step follows directly from steepest descent:

.. math::

   \boldsymbol{w}(k+1)=\boldsymbol{w}(k)
   -\mu_w\frac{\partial E_k}{\partial\boldsymbol{w}}
   =\boldsymbol{w}(k)+\mu_w e(k)\boldsymbol{\phi}(k).

Substituting :math:`e(k)=y(k)-\boldsymbol{w}^{\mathsf T}(k)\boldsymbol{\phi}(k)`
gives the affine local weight dynamics

.. math::

   \boldsymbol{w}(k+1)=
   \underbrace{\left[\boldsymbol{I}-\mu_w
   \boldsymbol{\phi}(k)\boldsymbol{\phi}^{\mathsf T}(k)\right]}_{\boldsymbol{A}_w(k)}
   \boldsymbol{w}(k)
   +\mu_w\boldsymbol{\phi}(k)y(k).

The software monitors :math:`\rho(\boldsymbol{A}_w(k))` and, where available,
its induced norm. For a fixed regressor, a sufficient scalar step-size condition
for contraction in the excited direction is

.. math::

   0<\mu_w<\frac{2}{\left\|\boldsymbol{\phi}(k)\right\|_2^2}.

A single constant :math:`\mu_w` must accommodate the largest feature energy in
the data. This is particularly restrictive for QNU regressors because their
energy grows approximately with the fourth power of the original signal scale.

Normalized gradient descent
---------------------------

NGD removes most of the direct dependence on feature-vector magnitude:

.. math::

   \eta_w(k)=
   \frac{\mu_w}{\varepsilon+\left\|\boldsymbol{\phi}(k)\right\|_2^2},

.. math::

   \boldsymbol{w}(k+1)=\boldsymbol{w}(k)
   +\eta_w(k)e(k)\boldsymbol{\phi}(k).

Its local update matrix is

.. math::

   \boldsymbol{A}_w(k)=\boldsymbol{I}-\eta_w(k)
   \boldsymbol{\phi}(k)\boldsymbol{\phi}^{\mathsf T}(k).

The regularizing denominator :math:`\varepsilon>0` prevents division by zero
and limits the step when the regressor is very small. NGD improves scale
robustness but does not create persistent excitation, remove model bias or
prevent instability caused by recursive use of a poor plant model.

Epochs in GD and NGD
~~~~~~~~~~~~~~~~~~~~

One epoch traverses the complete valid training record once. At the end of an
epoch the learned weights are retained and the data are replayed. More epochs
can reduce training error, but the samples are not new information. Excessive
epochs may overfit a finite trajectory or drive the recursive model into a
region that has good one-step error but poor free-run behavior.

Levenberg--Marquardt
--------------------

For the residual vector

.. math::

   \boldsymbol{r}(\boldsymbol{w})=
   \boldsymbol{y}-\boldsymbol{\Phi}\boldsymbol{w},

its Jacobian is

.. math::

   \boldsymbol{J}=\frac{\partial\boldsymbol{r}}
   {\partial\boldsymbol{w}^{\mathsf T}}=-\boldsymbol{\Phi}.

The L-M increment solves

.. math::

   \left(\boldsymbol{J}^{\mathsf T}\boldsymbol{J}
   +\lambda_{LM}\boldsymbol{I}\right)\Delta\boldsymbol{w}
   =-\boldsymbol{J}^{\mathsf T}\boldsymbol{r}.

Hence, for the linear-in-weights HONU,

.. math::

   \Delta\boldsymbol{w}=
   \left(\boldsymbol{\Phi}^{\mathsf T}\boldsymbol{\Phi}
   +\lambda_{LM}\boldsymbol{I}\right)^{-1}
   \boldsymbol{\Phi}^{\mathsf T}
   \left(\boldsymbol{y}-\boldsymbol{\Phi}\boldsymbol{w}\right).

As :math:`\lambda_{LM}\rightarrow 0`, the step approaches Gauss--Newton. For
large :math:`\lambda_{LM}`, it becomes a small gradient-like step. The damping
is adjusted according to whether the trial step reduces the residual cost.
Unlike Ridge, L-M damping is an iteration-control parameter and does not
necessarily define the final regularized objective.

For a linear-in-weights static fit, direct Ridge is normally faster and clearer.
L-M is useful when a common damped least-squares framework, iteration traces or
sliding-window refits are required.

Plant-learning diagnostics
--------------------------

Plant identification reports should be interpreted jointly:

.. math::

   \operatorname{RMSE}=
   \sqrt{\frac{1}{N}\sum_{k=1}^{N}e^2(k)}

measures one-step fit; :math:`\rho(\boldsymbol{A}_w(k))` characterizes the local
learning update; and :math:`\rho(\boldsymbol{A}_y(k))` characterizes the frozen
recursive output model. These are different objects. A stable weight update
does not imply a stable recursive plant model, and a stable plant model does not
prove stability of the complete adaptive closed loop.

Controller learning differs from plant identification
------------------------------------------------------

Plant learning minimizes prediction error with respect to
:math:`\boldsymbol{w}`. MRAC controller learning instead minimizes the
closed-loop tracking error with respect to controller weights
:math:`\boldsymbol{v}` and the scalar gain :math:`r_0`. Its gradient must pass
through the controller, the delayed plant model and the recursive closed-loop
history. It is therefore a recurrent sensitivity calculation rather than a
one-step supervised HONU fit. The complete derivation is given in
:doc:`mrac_architecture`.

Use in MPC
----------

MPC contains two distinct numerical learning/optimization levels. First, the
HONU prediction model is identified by Ridge or L-M, either once or repeatedly
from a sliding window. Second, at every control sample, the future input
sequence is optimized by damped Gauss--Newton using the recursively propagated
HONU prediction Jacobian. Controller-sequence optimization is not plant-weight
learning; the distinction is developed in :doc:`honu_mpc`.
