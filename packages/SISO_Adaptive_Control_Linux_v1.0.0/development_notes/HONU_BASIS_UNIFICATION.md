# HONU basis unification

The plant and controller HONU bases are now canonical and non-redundant in MRAC and MPC.

Plant LNU uses `x_aug = [x_0, x_1, ..., x_n]` with `x_0 = 1` and one weight per component.

Controller LNU uses `xi = [xi_0, xi_1, ..., xi_m]` with `xi_0 = 1` and one weight per component.

Plant QNU uses only products `x_i*x_j` for `0 <= i <= j <= n`. Since `x_0 = 1`, the terms `x_0*x_0` and `x_0*x_i` provide the bias and linear terms exactly once.

Controller QNU uses only products `xi_i*xi_j` for `0 <= i <= j <= m`. Since `xi_0 = 1`, the bias and linear terms are included exactly once.

No separate linear block is prepended to either QNU basis. Hence there are no duplicate `1`, `x_i`, or `xi_i` columns.

The canonical QNU weight count is `n_z*(n_z+1)/2`, where `n_z` includes the constant component.

Files trained with the previous redundant QNU layout or the previous unbiased LNU plant layout must not be reused. Run modules 02 and 03 again after this update.
