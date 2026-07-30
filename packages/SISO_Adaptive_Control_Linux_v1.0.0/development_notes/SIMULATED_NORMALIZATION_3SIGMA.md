# Fixed normalization in the simulated branch

Module 01 saves the physical data in `data_uy.txt`, computes one fixed set of
training statistics, and saves it in `simulated_normalization.npz`.

The normalized variables are

    u_z = (u - mu_u) / (3 sigma_u)
    y_z = (y - mu_y) / (3 sigma_y)

The same statistics are reused without refitting in modules 02, 03, and 04.
Module 04 converts the normalized controller output back to physical input
before integrating the selected ODE plant, and converts the physical output
back to normalized coordinates for the controller and HONU histories.

`data_uy_normalized.txt` is written for inspection. The physical source record
remains unchanged and auditable. Reference limits `d_min` and `d_max` are in
normalized output coordinates.
