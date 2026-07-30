# HONU MPC PCA variability selection

The MPC GUI now provides `PCA retained variability [%]` for selecting the number of components in the one-time PCA/SVD basis computed from the centered initial HONU feature matrix.

The status log reports both:

- numerical rank of the centered initial feature matrix, based on the relative SVD tolerance;
- number of components selected by the cumulative variability criterion and the actually retained percentage.

The selected fixed projection is subsequently applied to uncentered HONU feature vectors. The constant feature `x_0 = 1` remains outside PCA and is added exactly once.
