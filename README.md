# Small-Data Machine Learning

## SISO Adaptive Control

A Python and Linux implementation of adaptive Single-Input Single-Output (SISO) control based on Higher-Order Neural Units (HONUs).

The repository contains

- Python implementation
- Linux implementation
- Complete documentation
- 38 benchmark dynamic systems
- Reproducible examples

If you use this software in research, education, or applications, please cite the accompanying publication and the software package using the information provided in CITATION.cff.

## License

Software is distributed under the Apache License 2.0.

Documentation is licensed under Creative Commons Attribution 4.0 (CC BY 4.0).

## Mission

**Learn and control from as little data as you can see on the screen.**

SISO Adaptive Control is a research and teaching environment for data-driven identification and control of simulated and measured **Single-Input Single-Output (SISO)** systems.

Plant dynamics are learned directly from input-output data and used for **Model Reference Adaptive Control (MRAC)** and **Model Predictive Control (MPC)**. Controller design does not require an analytical physics-based plant model, manual linearization, or explicit estimation of physical parameters.


Small-Data Machine Learning develops transparent and computationally accessible methods for learning useful system dynamics from short experimental records and applying them directly to prediction and control.

## Workflows

### Simulated Systems

The simulated workflow includes **38 physical ODE plant models** covering linear, nonlinear, delayed, mechanical, process, biological, biomedical, aerospace, energy, and network dynamics.

Users can generate experiments, identify plant dynamics, configure MRAC or MPC, evaluate disturbance rejection, compare prediction modes, and inspect stability-oriented diagnostics.

<details>
<summary><strong>Show all 38 plant models</strong></summary>

### Bioprocess and Biomedical

- Bioprocess: dissolved oxygen bioreactor
- Bioprocess: photobioreactor pH / CO2
- Bioprocess: Monod chemostat biomass
- Biomedical: nonlinear drug PK
- Biomedical: nonlinear drug PK-PD
- Biomedical: glucose-insulin model

### Thermal, IT, Network, and Wireless

- Thermal: asymmetric Peltier system
- IT: CPU thermal control by fan
- IT: cloud-server workload
- IT: cloud-server workload with delay
- Network: nonlinear router fluid queue
- Network: router fluid queue with delay
- Network: router fluid queue with large delay
- Wireless: transmit-power / SNR control

### Process and Mechanical

- Process: bidirectional-pump nonlinear tank
- Mechanical: two masses, viscous damping
- Mechanical: two masses, LuGre friction
- Mechanical: two masses, LuGre friction 2
- Mechanical: tuned mass vibration absorber
- Mechanical: voice-coil servo
- Mechanical: overhead crane payload sway
- Mechanical: overhead crane payload sway with delay

### Aerospace, Accelerator, and Power Systems

- Drone: quadrotor altitude
- Drone: quadrotor roll
- Accelerator: RF cavity amplitude
- Accelerator: RF cavity amplitude with delay
- Accelerator: transverse beam position
- Power grid: linear microgrid frequency
- Power grid: nonlinear BESS microgrid frequency
- Power grid: nonlinear BESS microgrid frequency with delay

### Soil Ecology

- Soil ecology: moisture-controlled respiration
- Soil ecology: moisture respiration with delay
- Soil ecology: microbial carbon respiration
- Soil ecology: carbon priming
- Soil ecology: carbon priming with delay
- Soil ecology: nitrogen transformations and N2O
- Soil ecology: denitrification controlled by aeration
- Soil ecology: microbial C-N stoichiometry

</details>

### Measured Systems

The measured workflow imports external SISO input-output data. Users can select training intervals, configure sampling, identify plant dynamics, and design MRAC or MPC without deriving physical equations.

## Implemented Methods

The software includes:

- **Linear Neural Unit (LNU)** and **Quadratic Neural Unit (QNU)** plant identification;
- LNU- and QNU-based MRAC plant and controller structures;
- LNU, QNU, and **Multilayer Perceptron (MLP)** predictive plant models for MPC;
- gradient descent, normalized gradient descent, ridge or batch learning, and Levenberg-Marquardt learning where supported;
- recursive one-step, rollout-trained, and direct multi-horizon prediction modes;
- frozen-model and sliding-retraining MPC;
- **Principal Component Analysis (PCA)**-based reduction where supported;
- spectral-radius-based diagnostics supporting local stability analysis of learning dynamics, recursively operated learned models, and selected frozen closed-loop representations.

The spectral-radius quantities are stability-oriented diagnostics. They are not general proofs of global nonlinear plant stability or closed-loop stability.

## Software Editions

### Pure Python Edition

`SISO_Adaptive_Control_Python_v1.0.0`

Portable reference edition for Windows and Linux, intended for teaching, research, algorithm inspection, and reproducible experiments.

### Linux Performance Edition

`SISO_Adaptive_Control_Linux_v1.0.0`

Linux edition with selected C++, Cython, and Numba performance improvements. The benefit depends on the workflow, model, compiler, and hardware; the entire software is not universally accelerated.

## Documentation

Comprehensive technical documentation is included with both editions. It covers the plant equations, LNU, QNU and MLP models, learning methods, MRAC, MPC, prediction modes, stability diagnostics, configuration, experiments, plots, and exported results.

## Installation

Extract the selected distribution and use its supplied installer or `requirements.txt`.

Typical Pure Python setup:

```bash
python -m pip install -r requirements.txt
python launcher.py
```

On Windows, use the supplied `.bat` scripts where available. The Linux edition includes separate build instructions for its native extensions.

## Citation

The repository includes `CITATION.cff`. Cite the software release and the relevant methodological publications listed there. After Zenodo assigns a DOI, use the DOI-based software citation.

## Author

**Ivo Bukovsky**

The software was upgraded, polished, tested, and documented with AI assistance. Scientific concepts, methodological decisions, release decisions, and final validation remain the responsibility of the author.

## Licensing

Copyright © 2026 **Ivo Bukovsky**.

Source code, scripts, configuration files, and software examples are licensed under the **Apache License 2.0**. See `LICENSE`.

Documentation, original figures, diagrams, screenshots, tutorials, and explanatory materials are licensed under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**, unless otherwise stated. See `LICENSE-DOCUMENTATION`.

Third-party libraries and dependencies remain subject to their respective licenses.

## Disclaimer

The software is provided **“as is”**, without warranties or conditions of any kind.

Users are responsible for validating numerical behavior, learned models, controller settings, timing, hardware interfaces, constraints, and all safety mechanisms before experimental, real-time, embedded, industrial, or safety-relevant use.

The software must not be relied upon as the sole safety layer of a physical control system.

---

