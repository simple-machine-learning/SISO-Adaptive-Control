# Module 04 online adaptation

Module 04 no longer replays a frozen controller only. It initializes the controller from module 03 and continues online adaptation of the direct controller bias weight v_0 associated with xi_0 = 1.

The physical ODE plant provides the actual regulation error. The identified HONU plant provides the local sign of the plant input gain. The dynamic controller weights and r_0 remain at their module-03 values, so online adaptation removes permanent offset without retuning the complete dynamic controller.

No clipping or saturation of q or u is applied in modules 03 or 04. The only projection introduced here is on the adaptive bias parameter v_0 around its module-03 initial value to prevent estimator windup.

The module-04 result file now also stores r_0, v_0, g_v_norm, and g_r_0. The GUI plots d, y_ref, y in the upper panel and the actual physical plant input u in a lower panel.
