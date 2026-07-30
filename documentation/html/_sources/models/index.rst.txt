Plant models
============

Each page gives the physical differential equations, default parameters, input ``u``, controlled output ``y`` and the corresponding Python implementation. The contents below intentionally lists only model names.


Mathematical notation
---------------------

Throughout the model documentation, scalar quantities are written as italic lowercase symbols, vectors and one-dimensional arrays as bold lowercase symbols, and matrices or tensors as bold uppercase symbols. Thus :math:`x`, :math:`u`, and :math:`y` are scalars; :math:`\mathbf{x}` is a state vector; and :math:`\mathbf{A}` is a matrix. Individual vector components remain scalar, for example :math:`x_i`.

.. toctree::
   :maxdepth: 1
   :caption: Models

   accelerator_rf_cavity_amplitude
   accelerator_rf_cavity_amplitude_with_delay
   accelerator_beam_position
   glucose_insulin_bergman
   drug_infusion_pk
   drug_infusion_pkpd
   bioreactor_dissolved_oxygen
   chemostat_monod_biomass
   photobioreactor_ph_co2
   quadrotor_altitude
   quadrotor_roll
   cloud_server_workload
   cloud_server_workload_with_delay
   cpu_thermal_fan
   overhead_crane_payload_sway
   overhead_crane_payload_sway_with_delay
   mechanical_tuned_mass_damper
   voice_coil_servo
   two_mass_actuator_grounded_m2_lugre
   two_mass_actuator_grounded_m2_lugre2
   two_mass_actuator_grounded_m2_linear_viscous
   network_router_fluid_queue
   network_router_fluid_queue_with_delay
   network_router_fluid_queue_with_large_delay
   microgrid_frequency_linear
   microgrid_frequency_bess_nonlinear
   microgrid_frequency_bess_nonlinear_with_delay
   bidirectional_tank_level
   soil_carbon_priming
   soil_carbon_priming_with_delay
   soil_denitrification_aeration
   soil_microbe_cn_stoichiometry
   soil_microbe_carbon_respiration
   soil_moisture_respiration_with_delay
   soil_moisture_respiration
   soil_nitrogen_n2o
   peltier_thermal_asymmetric
   wireless_power_snr
