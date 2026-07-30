# Configurable MLP architecture

The MPC GUI now exposes `MLP hidden` as a comma-separated list of positive hidden-layer widths.

Examples:

- `8`: one hidden layer with 8 neurons.
- `16,8`: two hidden layers with 16 and 8 neurons.
- `32,16,8`: three hidden layers.

The output layer is generated automatically:

- recursive MLP: one output neuron;
- direct multi-horizon MLP: `Np` output neurons.

The hidden-layer list is saved with the identified model and checked as part of frozen-model compatibility. Legacy models containing `mlp_hidden_1` and `mlp_hidden_2` remain loadable.
