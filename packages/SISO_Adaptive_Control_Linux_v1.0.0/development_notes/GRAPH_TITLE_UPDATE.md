# Graph title update

All plots in simulated modules 01-04 now identify the active physical plant by
its user-visible model name. The mapping is centralized in
`shared_plant_model.py` as `PLANT_DISPLAY_NAMES`.

The first title line is the selected physical system. The second line describes
the MRAC workflow step, HONU plant/controller structure, learning method, and
relevant sampling or training parameters.
