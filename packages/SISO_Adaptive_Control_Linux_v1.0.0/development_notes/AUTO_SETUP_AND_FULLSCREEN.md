# Automatic setup and full-screen graph

- The former `Apply setup` button was replaced by `Full screen`.
- Every setup combo box and spin box automatically writes the current values to `project_setup.py` after a short debounce interval.
- Modules 01-04 still save the setup immediately before launch, so the external script always receives the current GUI values.
- `Full screen` moves the active graph tab to a separate full-screen window. Press `Esc` or close that window to restore the graph to the main GUI.
