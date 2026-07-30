Measured-data input and processing
==================================

Purpose of the measured-data page
---------------------------------

The measured-data page loads an experimental record and lets the user select
one time channel, one plant-input channel ``u`` and one plant-output channel
``y``. The selected interval is checked, optionally downsampled to the chosen
sampling period ``dt``, plotted, and saved in the common data representation
used by both MRAC and MPC.

The application does not infer the physical meaning of the signals. Channel
selection, units, sign conventions, offsets and the interpretation of the
input-output relationship remain the user's responsibility.

Supported file formats
----------------------

Text tables
~~~~~~~~~~~

The extensions ``.txt``, ``.csv`` and ``.dat`` are accepted. The file must
contain named numeric columns. Column names may be supplied either in the
first row or in a leading commented header, for example:

.. code-block:: text

   # time input output
   0.00  0.10  1.24
   0.01  0.12  1.27

Comma-separated, semicolon-separated, tab-separated and whitespace-separated
numeric tables are supported where the format can be detected unambiguously.
The GUI exposes all numeric columns and the user assigns the time, ``u`` and
``y`` roles.

MATLAB files
~~~~~~~~~~~~

The extension ``.mat`` is accepted in two forms.

* MATLAB v7.3 HDF5 measurement exports are read from their stored time axes,
  channels, paths, descriptions and units.
* Ordinary pre-v7.3 MAT files are read through SciPy. One-dimensional numeric
  arrays are exposed as channels, and a time vector named ``t``, ``time`` or
  ``timestamp`` must be present.

For v7.3 files the reader preserves available signal names and units. Missing
units are not fabricated except for a few conservative names recognized by
the supplied experiment reader.

NumPy files
~~~~~~~~~~~

The low-level importer accepts ``.npy`` and ``.npz`` data. An ``.npz`` file
must contain arrays named ``t``, ``u`` and ``y``. An ``.npy`` array must be a
two-dimensional numeric table with at least three columns ordered as ``t``,
``u`` and ``y``.

Input requirements
------------------

.. warning::

   Do not collect open-loop training data from an unstable physical plant.
   Use an independent stabilizing controller and verify that all selected
   signals remain bounded before HONU identification.

The selected signals must satisfy the following conditions.

* ``t``, ``u`` and ``y`` must have equal length.
* At least three finite selected samples are required for saving.
* The selected time values must be strictly increasing.
* Duplicate or non-finite rows are rejected or removed by the applicable
  import path.
* The requested ``dt`` must be positive and must not be smaller than the
  effective sampling interval of the selected record.
* The record must contain bounded trajectories from a naturally stable or
  independently pre-stabilized experiment.
* The amplitudes and dynamics in the record must cover the operating region in
  which the learned MRAC or MPC controller will be used.

The median time increment is used as the measured sampling estimate
``dt_raw``. A visibly irregular time axis should be treated as a data-quality
issue; the software does not perform general asynchronous-data reconstruction.

Selection and downsampling
--------------------------

The user can select a time interval and choose a working sampling period
``dt``. If ``dt`` equals the measured sampling period, the samples are retained.
If ``dt`` is larger, the record is downsampled on a uniform grid. Each new grid
point takes the nearest original sample of ``u`` and ``y``. Thus the operation
is sample selection, not interpolation or anti-alias filtering.

The measured-data variant intentionally prohibits upsampling to a smaller
``dt`` because that would create artificial temporal resolution not present in
the experiment.

Saved common dataset
--------------------

The selected record is stored as ``data_uy.txt`` with columns

.. math::

   \begin{bmatrix} t_k & u_k & y_k \end{bmatrix}.

This file is the shared plant dataset for both the MRAC and MPC menus. Switching
between MRAC and MPC therefore does not require loading the same source file
again unless the user intentionally replaces or changes the selected dataset.

The associated run metadata record stores the source filename, number of
samples, raw and selected sampling periods, and selected time limits.

Normalization
-------------

The application computes mean and standard-deviation normalization separately
for the selected input and output:

.. math::

   u_{z,k}=\frac{u_k-\mu_u}{\sigma_u}, \qquad
   y_{z,k}=\frac{y_k-\mu_y}{\sigma_y}.

The normalized record is saved as ``data/data_uy_normalized.txt`` and the
normalization parameters are saved in ``data/simulated_normalization.npz``.
This filename is retained only because it is referenced by the existing MRAC
and MPC implementation; its contents are normalization statistics computed
from the imported measured record.

What happens after saving
-------------------------

After the selected dataset has been saved, the workflow consists of three
main operations:

#. Load and save measured data.
#. Identify an LNU or QNU HONU plant from the selected ``u`` and ``y`` record.
#. Train the MRAC controller on the identified HONU plant, or configure and run
   HONU MPC using the same identified-data basis.

The MRAC controller-training response already evaluates the controller in
closed loop with the trained HONU plant. Consequently, the measured MRAC menu
does not contain a separate fourth workflow button for testing the controller
against a separate executable process model.

Interpretation limitation
-------------------------

The software learns a discrete-time input-output approximation of the selected
record. It does not reconstruct unmeasured physical states, establish
causality, compensate unknown sensor dynamics, or prove that the dataset is
persistently exciting. Good one-step identification accuracy does not by
itself guarantee reliable multi-step prediction or stable closed-loop control.
A HONU model trained only on bounded trajectories should not be expected to
predict reliably far outside the amplitude, rate and dynamic range contained
in those trajectories. For data collected under an existing PID or other
stabilizing controller, the identified input-output dynamics may describe the
pre-stabilized closed loop rather than the uncontrolled plant. In such a
workflow, MRAC or MPC is used primarily to improve performance within that
bounded regime, not to establish stabilization from an initially unsafe
open-loop condition.
