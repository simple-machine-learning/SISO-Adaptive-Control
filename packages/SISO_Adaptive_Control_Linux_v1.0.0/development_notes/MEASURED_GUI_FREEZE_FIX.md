# Measured-data GUI responsiveness fix

The measured-data file reader now parses MAT, text, CSV, NPY and NPZ files in a background Python thread. Qt widgets are updated only after the parsed payload is returned to the GUI thread.

Plot rendering is bounded to at most 6000 original curve points and 4000 resampling markers in the currently visible time range. The previous implementation generated resampling markers for the complete selected interval separately for every displayed channel, which could allocate millions of points and block the Qt event loop.

Selection sample counting now uses binary searches instead of scanning the complete time vector. Dataset export displays a busy cursor and prevents duplicate export requests.
