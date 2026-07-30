# MPC 3.1 / 3.2 state consistency fix

- 3.1 Frozen HONU now validates the complete identification-dependent GUI configuration, not only plant, HONU type and embedding orders.
- Changes in sampling, delay, P-regulated plant mode, excitation, identification method, regularisation, PCA selection or seed invalidate the stored HONU and require a new identification.
- 3.1 loads only the HONU produced by step 2 and records `honu_source=loaded_identified_model`.
- 3.2 never loads the stored step-2 model. It starts from the current GUI configuration, builds a fresh PCA basis after the current initial-excitation window and retrains the HONU in each sliding window. Results record `honu_source=fresh_sliding_retraining`.
- Both MPC outputs now store the active model/HONU/sampling metadata for later verification.
