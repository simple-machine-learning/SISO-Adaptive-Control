HONU MRAC architecture and recurrent controller learning
=========================================================

Architecture
------------

The implemented workflow is an indirect, model-based MRAC procedure. The
physical plant is first excited and identified by an LNU or QNU. The adaptive
controller is then trained in a closed loop containing this learned HONU plant.
Finally, the trained controller is evaluated against the original physical ODE
plant. The following signals are distinguished:

.. math::

   d(k) \;\text{: command},\qquad
   y_{\mathrm{ref}}(k) \;\text{: reference-model output},

.. math::

   y(k) \;\text{: HONU/physical plant output},\qquad
   e_r(k)=y(k)-y_{\mathrm{ref}}(k).

The controller contains an LNU or QNU adaptive block that produces
:math:`q(k)` and a separately adapted scalar gain :math:`r_0`:

.. math::

   u(k)=r_0\,[d(k)-q(k)].

This structure gives :math:`r_0` a direct influence on command gain and control
action, while :math:`q(k)` provides dynamic feedback compensation. The project
limits :math:`r_0` to the configured interval
:math:`[r_{0,min},r_{0,max}]` after each update. The control signal itself is
not generally saturated.

Application to stable or pre-stabilized plants
-----------------------------------------------

Controller training is performed against an identified HONU plant and therefore
inherits the validity limits of the identification data. The intended practical
use is a naturally stable plant or a plant already stabilized by an independent
feedback controller. For an open-loop unstable process, that stabilizing loop
must remain responsible for bounded and safe behaviour during data acquisition
and controller validation.

The MRAC layer can then improve reference tracking, transient behaviour or
disturbance rejection within the covered operating region. The present
implementation does not prove that the learned controller stabilizes an
arbitrary initially unstable nonlinear plant. Deployment outside the
data-supported range requires separate stability, constraint and safety
analysis.

Reference model
---------------

The reference model is the cascade of two stable first-order systems. Its
continuous-time transfer function is

.. math::

   G_{\mathrm{ref}}(s)
   =\frac{Y_{\mathrm{ref}}(s)}{D(s)}
   =\frac{e^{-n_{u,1}T_s s}}
   {(\tau_1 s+1)(\tau_2 s+1)},

where the command delay is derived from the identified plant-input delay,

.. math::

   n_{u,1}=\left\lfloor\frac{\tau_u}{T_s}\right\rfloor.

Thus :math:`d` is the command, :math:`y_{\mathrm{ref}}` is the output of the
reference model, and no additional reference-model state symbol is required in
the mathematical documentation. In the MRAC Python setup, the filter time
constants are ``Tau_1`` and ``Tau_2``. The separate variable ``tau_d`` denotes
the reference switching period and must not be interpreted as this transport
delay. The present Python training scripts implement
the two filters recursively and use a local scalar variable ``z`` for the
intermediate filter output. That local implementation variable is not the same
quantity as the PCA vector :math:`\boldsymbol{z}` used in HONU MPC.

Increasing :math:`\tau_1` or :math:`\tau_2` makes the demanded response slower
and generally reduces control effort. A reference model faster than the
identified or physical plant may demand trajectories that are unreachable or
outside the data-supported region of the HONU approximation.

Controller regressors
---------------------

For an LNU controller, the project uses a recurrent regressor composed of a
constant, recent plant outputs and recent reference errors,

.. math::

   \boldsymbol{\xi}(k)=
   \begin{bmatrix}
   1 & y(k) & \cdots & y(k-n_y+1) &
   e_r(k) & \cdots & e_r(k-n_e+1)
   \end{bmatrix}^{\mathsf T},

with :math:`n_e=n_y` in the current scripts. The controller output is

.. math::

   q(k)=\boldsymbol{v}^{\mathsf T}\boldsymbol{\xi}(k).

For a QNU controller,

.. math::

   q(k)=\boldsymbol{v}^{\mathsf T}
   \boldsymbol{\psi}(\boldsymbol{\xi}(k)),

where :math:`\boldsymbol{\psi}` contains all upper-triangular products
:math:`\xi_i\xi_j`, including constant and linear terms through
:math:`\xi_0=1`.

Closed-loop training objective
------------------------------

At each sample, the controller minimizes

.. math::

   E_k=\frac{1}{2}e_r^2(k)
   =\frac{1}{2}[y(k)-y_{\mathrm{ref}}(k)]^2.

The reference model does not depend on the controller parameters. Therefore

.. math::

   \frac{\partial E_k}{\partial\boldsymbol{v}}
   =e_r(k)\frac{\partial y(k)}{\partial\boldsymbol{v}},
   \qquad
   \frac{\partial E_k}{\partial r_0}
   =e_r(k)\frac{\partial y(k)}{\partial r_0}.

Define the exact recurrent sensitivities

.. math::

   \boldsymbol{g}_v(k)=\frac{\partial y(k)}{\partial\boldsymbol{v}},
   \qquad
   g_{r_0}(k)=\frac{\partial y(k)}{\partial r_0}.

The GD updates are then

.. math::

   \Delta\boldsymbol{v}(k)
   =-\mu_v e_r(k)\boldsymbol{g}_v(k),

.. math::

   \Delta r_0(k)
   =-\mu_{r_0}e_r(k)g_{r_0}(k).

For NGD,

.. math::

   \eta_v(k)=\frac{\mu_v}
   {\varepsilon+\boldsymbol{g}_v^{\mathsf T}(k)\boldsymbol{g}_v(k)},
   \qquad
   \eta_{r_0}(k)=\frac{\mu_{r_0}}
   {\varepsilon+g_{r_0}^2(k)},

.. math::

   \Delta\boldsymbol{v}(k)=-\eta_v(k)e_r(k)\boldsymbol{g}_v(k),
   \qquad
   \Delta r_0(k)=-\eta_{r_0}(k)e_r(k)g_{r_0}(k).

The implemented update may additionally smooth increments,

.. math::

   \Delta\boldsymbol{v}_s(k)=
   \alpha_v\Delta\boldsymbol{v}(k)
   +(1-\alpha_v)\Delta\boldsymbol{v}_s(k-1),

.. math::

   \Delta r_{0,s}(k)=
   \alpha_{r_0}\Delta r_0(k)
   +(1-\alpha_{r_0})\Delta r_{0,s}(k-1),

when the selected controller script/configuration applies these factors.

Recurrent sensitivity derivation
--------------------------------

The central point is that the controller regressor contains past outputs and
errors, which themselves depend on previous controller parameters. The gradient
cannot be reduced to the direct derivative of the current HONU output.

For the LNU controller,

.. math::

   q(k-1)=\boldsymbol{v}^{\mathsf T}\boldsymbol{\xi}(k-1),

hence

.. math::

   \frac{\partial q(k-1)}{\partial\boldsymbol{v}}
   =\boldsymbol{\xi}(k-1)+
   \left(\frac{\partial\boldsymbol{\xi}(k-1)}
   {\partial\boldsymbol{v}^{\mathsf T}}\right)^{\mathsf T}
   \boldsymbol{v}.

Because

.. math::

   u(k-1)=r_0[d(k-1)-q(k-1)],

.. math::

   \frac{\partial u(k-1)}{\partial\boldsymbol{v}}
   =-r_0\frac{\partial q(k-1)}{\partial\boldsymbol{v}},

.. math::

   \frac{\partial u(k-1)}{\partial r_0}
   =d(k-1)-q(k-1)-r_0
   \frac{\partial q(k-1)}{\partial r_0}.

For an LNU plant,

.. math::

   y(k)=w_0+
   \sum_{i=1}^{n_y}w_{y,i}y(k-i)+
   \sum_{j=1}^{n_u}w_{u,j}u(k-n_{u,1}-j).

Differentiating yields the recurrent relations

.. math::

   \boldsymbol{g}_v(k)=
   \sum_{i=1}^{n_y}w_{y,i}\boldsymbol{g}_v(k-i)+
   \sum_{j=1}^{n_u}w_{u,j}
   \frac{\partial u(k-n_{u,1}-j)}{\partial\boldsymbol{v}},

.. math::

   g_{r_0}(k)=
   \sum_{i=1}^{n_y}w_{y,i}g_{r_0}(k-i)+
   \sum_{j=1}^{n_u}w_{u,j}
   \frac{\partial u(k-n_{u,1}-j)}{\partial r_0}.

The sensitivities are initialized to zero and propagated sample by sample
through the complete closed-loop history. This is a real-time recurrent
learning form specialized to a compact polynomial controller and plant model.

For a QNU plant, the scalar plant equation is replaced by

.. math::

   y(k)=\boldsymbol{w}^{\mathsf T}
   \boldsymbol{\phi}_{Q}(\boldsymbol{x}(k)),

and the chain rule gives

.. math::

   \boldsymbol{g}_v(k)=
   \frac{\partial y(k)}{\partial\boldsymbol{x}^{\mathsf T}(k)}
   \frac{\partial\boldsymbol{x}(k)}
   {\partial\boldsymbol{v}^{\mathsf T}},

.. math::

   g_{r_0}(k)=
   \frac{\partial y(k)}{\partial\boldsymbol{x}^{\mathsf T}(k)}
   \frac{\partial\boldsymbol{x}(k)}{\partial r_0}.

For a QNU controller, the direct derivative becomes

.. math::

   \frac{\partial q}{\partial\boldsymbol{v}}
   =\boldsymbol{\psi}(\boldsymbol{\xi})+
   \boldsymbol{v}^{\mathsf T}
   \frac{\partial\boldsymbol{\psi}}
   {\partial\boldsymbol{\xi}^{\mathsf T}}
   \frac{\partial\boldsymbol{\xi}}
   {\partial\boldsymbol{v}^{\mathsf T}}.

Thus all four combinations LNU--LNU, LNU--QNU, QNU--LNU and QNU--QNU use the
same chain-rule structure; only the plant and controller feature Jacobians
change.

Epoch training
--------------

Each epoch restarts the simulated HONU closed-loop state histories from the
same initial condition and replays the same complete reference record. The
controller parameters :math:`\boldsymbol{v}` and :math:`r_0` are retained
between epochs. This separates repeated optimization of the controller from an
uncontrolled continuation of plant-state history.

The resulting controller is therefore optimized for the learned HONU plant and
the chosen training reference distribution. It is not trained directly on the
physical ODE during module 03. Module 04 is an out-of-model validation and can
expose approximation error, unreachable references and control actions outside
the identification domain.

Local learning and closed-loop diagnostics
------------------------------------------

Linearizing the instantaneous controller update gives

.. math::

   \boldsymbol{A}_v(k)=\boldsymbol{I}-\eta_v(k)
   \boldsymbol{g}_v(k)\boldsymbol{g}_v^{\mathsf T}(k),

.. math::

   A_{r_0}(k)=1-\eta_{r_0}(k)g_{r_0}^2(k).

The project monitors :math:`\rho(\boldsymbol{A}_v(k))` and
:math:`|A_{r_0}(k)|` as local adaptation diagnostics. For the LNU--LNU case it
also constructs a frozen closed-loop companion matrix :math:`\boldsymbol{M}(k)`
from the current plant and controller coefficients and reports
:math:`\rho(\boldsymbol{M}(k))`.

These indicators are physically meaningful: values below one correspond to
stable frozen linear update or closed-loop maps. They remain conditional on the
identified model, the current operating point and frozen parameters. They do
not prove global nonlinear stability of the complete time-varying adaptive
system.

What is learned
---------------

Module 02 learns the plant weights :math:`\boldsymbol{w}` from input-output
data. Module 03 keeps :math:`\boldsymbol{w}` fixed and learns the controller
weights :math:`\boldsymbol{v}` and direct gain :math:`r_0` by minimizing
model-reference tracking error through recurrent closed-loop sensitivities.
Module 04 does not continue controller learning; it tests the saved controller
on the physical ODE plant. HONU MPC uses a different procedure described in
:doc:`honu_mpc`: it learns or refits prediction-model weights and optimizes a
future control sequence rather than adapting :math:`\boldsymbol{v}` and
:math:`r_0`.
