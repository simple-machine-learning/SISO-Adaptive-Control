# HONU MPC excitation range update

The separate `excitation amplitude` parameter was removed.

The initial identification excitation is now generated directly in the interval

    u_exc(k) in [u_min, u_max].

The GUI labels are `u min (exc.)` and `u max (exc.)`. These limits apply only while `k < excitation_index`. They are not passed as bounds to the MPC optimizer, so the subsequent MPC control action remains unrestricted.
