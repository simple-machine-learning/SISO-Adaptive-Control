# Module 04 full online adaptation

Module 04 now continues adaptation of all controller weights v and the scalar gain r_0.
The physical ODE plant supplies the regulation error. The identified HONU plant supplies recursive sensitivities dy/dv and dy/dr_0.
No saturation is applied to q or u in modules 03 and 04. Parameter projection is used only as estimator-windup protection.
