# Levenberg-Marquardt plant identification

The simulated branch now supports Batch/Ridge, LM, GD, and NGD for LNU and QNU plant identification. LM reuses the fixed 3-sigma normalization from module 01. The GUI parameter `epochs` is interpreted as LM iterations and `lambda` as the initial damping coefficient when LM is selected. The resulting model files are `plant_LNU_lm.txt` and `plant_QNU_lm.txt`; controller training automatically loads the selected LM model through `plant_training_method = "lm"`.
