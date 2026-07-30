# HONU MPC PCA component selection

The MPC GUI provides two PCA component-selection modes.

- `Rank`: uses all components belonging to the automatic numerical rank of the centered initial HONU feature matrix. The tolerance follows the default `numpy.linalg.matrix_rank` convention.
- `Variability`: uses the minimum number of components reaching the selected retained variability percentage, while never exceeding the numerical rank.

The status log reports the original feature count, numerical rank, selected mode, number of components actually used, and retained variability when applicable.
