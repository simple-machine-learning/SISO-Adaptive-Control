# Configuration and state consistency fix

This revision prevents stale data and models from being reused after changing the physical model, HONU architecture, sampling period, or P-regulated black-box mode.

MRAC now applies model-specific embedding orders and P-regulator settings, clears LNU/QNU parameter caches when the physical model changes, validates the identity of module-01 data before modules 02-04, and checks normalization compatibility before controller training.

MPC Frozen HONU now loads the model created by Identify HONU Plant instead of retraining it. Identification files carry configuration identity metadata and are rejected when they do not match the active plant model, HONU type, n_y, or n_u.
