SISO Adaptive Control
=====================

This is the unified documentation for the simulated-system and measured-system
variants of the SISO HONU software. Both variants use the same conceptual
workflow: obtain a sampled input-output record, identify an LNU, QNU or MLP plant prediction model, and use the
identified model in MRAC or MPC.

The simulated mode obtains the record from a selected physical ODE plant. The
measured mode imports an experimental file and maps selected channels to the
common interface ``t``, ``u``, ``y``. The distinction is therefore the data
source and plant execution, not the HONU learning and control principles.

Both modes are intended primarily for open-loop stable plants or plants that
are already stabilized by an independent feedback controller. During data
acquisition, all relevant input and output signals must remain bounded and
within a safe, data-supported operating region.

.. toctree::
   :maxdepth: 2
   :caption: Software modes

   software_overview
   measured_data
   scope_and_limitations

.. toctree::
   :maxdepth: 2
   :caption: Models and control

   models/index
   honu/index

Building the HTML documentation
-------------------------------

The application and documentation can be used on both Windows and Linux.
After activating the project virtual environment, use ``python -m pip`` so
that packages are installed for the same Python interpreter that runs the
software.

Windows
~~~~~~~

From the repository root, run:

.. code-block:: bat

   python -m pip install -r requirements.txt
   python launcher.py

To build the documentation:

.. code-block:: bat

   python -m pip install -r documentation\requirements.txt
   python -m sphinx -b html documentation documentation\_build\html

Open ``documentation\_build\html\index.html``.

Linux
~~~~~

From the repository root, run:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python launcher.py

To build the documentation:

.. code-block:: bash

   python -m pip install -r documentation/requirements.txt
   python -m sphinx -b html documentation documentation/_build/html

Open ``documentation/_build/html/index.html``.
