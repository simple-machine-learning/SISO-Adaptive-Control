# SISO Adaptive Control — Representative Results

This gallery contains representative MRAC and MPC results from selected simulated plants. The figures demonstrate achievable behavior and provide reproducible configuration references. They are not universal optimum settings.

Correct setup is problem-dependent and may require adjustment of sampling, training interval, input excitation, delayed-input and delayed-output orders, model structure, learning parameters, prediction horizon, penalties, constraints, and reference signal. A practical workflow is to reproduce the nearest example and then change one parameter group at a time.

The presented results are representative examples rather than fully optimized benchmark results. Some configurations may not have been tuned to their maximum achievable performance, and better results may be obtained through further adjustment of the model structure, sampling, training data, learning parameters, prediction horizon, penalties, constraints, and reference signal.

## General starting points

- **Linear Neural Unit (LNU):** preferred first baseline for approximately linear dynamics, narrow operating ranges, and short datasets.
- **Quadratic Neural Unit (QNU):** useful when curvature, asymmetry, nonlinear friction, state-dependent gain, or regressor interactions are important.
- **Multilayer Perceptron (MLP) in MPC:** offers more flexible nonlinear approximation but usually requires more data and more careful validation of recursive prediction.
- **Model Reference Adaptive Control (MRAC):** useful when online controller adaptation and a meaningful reference model are available.
- **Model Predictive Control (MPC):** useful when prediction, delays, future references, constraints, and explicit control penalties are important.

## Included examples

### Biomedical glucose-insulin model

**Class:** Slow nonlinear biomedical dynamics  
**Included methods:** MPC, MRAC

Shows MRAC and MPC examples for a slowly varying nonlinear system. Sampling and excitation should reflect the dominant physiological time scales.

### Biomedical nonlinear drug PK

**Class:** Nonlinear pharmacokinetic dynamics  
**Included methods:** MPC, MRAC

Shows an MRAC example using compact HONU structures. The operating range and training excitation are particularly important for nonlinear dose-response dynamics.

### IT cloud-server workload

**Class:** Dynamic workload and resource process  
**Included methods:** MPC

Shows MPC applied to workload regulation. The example is relevant to systems with measurable disturbances, delayed response, and actuator limitations.

### Mechanical overhead crane payload sway

**Class:** Lightly damped oscillatory mechanics  
**Included methods:** MPC, MRAC

Shows compact MRAC and MPC examples for payload-sway control. Reference shaping and conservative tuning help avoid exciting oscillatory modes.

### Mechanical overhead crane payload sway with delay

**Class:** Delayed oscillatory mechanical system  
**Included methods:** MPC

Shows MPC on payload sway with transport delay. It is a useful reference for combining oscillatory history with explicit prediction.

### Mechanical tuned mass vibration absorber

**Class:** Resonant vibration system  
**Included methods:** MPC, MRAC

Shows MRAC and MPC examples for a resonant mechanical plant. Sampling, delayed-output order, and control penalties strongly influence the result.

### Mechanical two masses LuGre friction 2

**Class:** Oscillatory mechanical system with nonlinear friction  
**Included methods:** MPC, MRAC

Shows MRAC and MPC behavior for coupled mechanics with friction. Longer histories, appropriate sampling, and conservative control action may be required.

### Mechanical voice-coil servo

**Class:** Fast electromechanical servo  
**Included methods:** MRAC

Shows MRAC on a fast servo plant. Use a sampling period consistent with actuator and sensor bandwidth and avoid excessive adaptation gains.

### Network router fluid queue with large delay

**Class:** Delayed nonlinear network process  
**Included methods:** MPC

Illustrates MPC on a system with substantial transport delay. Use it as a reference for selecting input/output history, prediction horizon, constraints, and conservative penalties.

### Power grid nonlinear BESS microgrid frequency with delay

**Class:** Delayed nonlinear power-system dynamics  
**Included methods:** MPC, MRAC

Shows MPC for frequency support with battery energy storage and delay. Prediction horizon, action constraints, and delay representation are central.

### Process bidirectional-pump nonlinear tank

**Class:** Asymmetric nonlinear process  
**Included methods:** MPC, MRAC

Compares several MRAC and MPC configurations on a nonlinear tank. The examples demonstrate that LNU can be an effective baseline while QNU may better capture curvature and asymmetric behavior.

### Soil carbon priming effect

**Class:** Slow nonlinear ecological dynamics  
**Included methods:** MRAC

Shows MRAC configurations for a nonlinear soil-carbon model. It is useful as a starting point for slow systems with interacting state-dependent effects.

### Thermal asymmetric Peltier system

**Class:** Slow asymmetric thermal process  
**Included methods:** MPC, MRAC

Shows MRAC and MPC on heating/cooling dynamics with different gains and time constants. Scaling, sampling, and direction-dependent behavior matter.
