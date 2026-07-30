# Model documentation audit — 2026-07-28

All 38 simulated ODE plant documents were checked against `shared_plant_model.py` and the corresponding `plant_models/*.py` implementation.

Checks performed:

- controlled input/output interface key, meaning, and unit;
- availability of every documented algebraic signal in `algebraic_outputs()`;
- finite controlled output at the default initial state;
- mathematical notation in the input/output and variable tables;
- explicit distinction between absolute states and deviation outputs;
- source/provenance reference for every model.

Corrections:

- router output is now written explicitly as `Delta q = q - q_0`; the implementation has always returned `queue_deviation`, not absolute queue occupancy;
- malformed plain-text mathematical symbols such as `Deltaq`, `Deltatau`, `tauq`, `rin`, and `rhoCN` were replaced by proper mathematical notation;
- voice-coil input wording was aligned with the shared signal metadata;
- every model now contains a `Model provenance and references` section;
- delayed variants inherit the base-model reference and cite the Erlang/cascaded-lag delay approximation.

The references describe the principal physical or domain-modeling foundation. The software models are reduced-order educational benchmarks and are not claimed to be parameter-identical reproductions of the cited publications.
