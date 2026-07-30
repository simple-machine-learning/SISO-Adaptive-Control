from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'documentation' / 'models'

repls = {
'accelerator_beam_position.rst': {
':math:`vx`': ':math:`v`',
':math:`Bm`': ':math:`m`',
':math:`Fr`': ':math:`F_r`',
'     - Microbial biomass or model-specific mass state.': '     - Actual corrector-magnet field state after first-order actuator dynamics.',
},
'accelerator_rf_cavity_amplitude.rst': {
':math:`Vc`': ':math:`V`',
},
'accelerator_rf_cavity_amplitude_with_delay.rst': {
':math:`Vc`': ':math:`V`', ':math:`Ib`': ':math:`P_b`', ':math:`Ld`': ':math:`k_dV^3`',
},
'bidirectional_tank_level.rst': {
':math:`qp`': ':math:`q_p`', ':math:`qout`': ':math:`q_{\\mathrm{out}}`', ':math:`qnet`': ':math:`q_{\\mathrm{net}}`',
},
'cloud_server_workload.rst': {
':math:`\\mu`': ':math:`s(x,c)`',
'     - Position or displacement state specified by this mechanical model.': '     - Pending-workload or backlog state.',
'     - Carbon or concentration state defined by the equations.': '     - Allocated compute-capacity state after first-order provisioning dynamics.',
},
'cloud_server_workload_with_delay.rst': {':math:`\\mu`': ':math:`s(x,c)`'},
'cpu_thermal_fan.rst': {
':math:`nf`': ':math:`f`', ':math:`Qc`': ':math:`Q_c`', ':math:`fan`': ':math:`f`',
'     - Temperature state; the selected temperature is returned as the controlled output.': '     - Chip-temperature state.',
},
'overhead_crane_payload_sway.rst': {
':math:`xL`': ':math:`x_L`', ':math:`xT`': ':math:`x`', ':math:`vT`': ':math:`v`',
':math:`yL`': ':math:`y_L`', ':math:`Fd`': ':math:`F`', ':math:`Fstop`': ':math:`F_e`', ':math:`force`': ':math:`F`',
'     - Position or displacement state specified by this mechanical model.': '     - Trolley-position state.',
'     - Volumetric soil-moisture state.': '     - Payload sway-angle state.',
},
'overhead_crane_payload_sway_with_delay.rst': {
':math:`xL`': ':math:`x_L`', ':math:`xT`': ':math:`x`', ':math:`vT`': ':math:`v`',
':math:`yL`': ':math:`y_L`', ':math:`Fd`': ':math:`F`', ':math:`Fstop`': ':math:`F_e`',
},
'peltier_thermal_asymmetric.rst': {
':math:`Th`': ':math:`T_h`', ':math:`Tc`': ':math:`T_c`', ':math:`QP`': ':math:`Q_{P,h}`', ':math:`QJ`': ':math:`Q_J`',
},
'photobioreactor_ph_co2.rst': {
':math:`CCO_{2}`': ':math:`C`', ':math:`QCO_{2}`': ':math:`Q`',
'     - Concentration state whose physical meaning is defined by the model title and equations.': '     - Dissolved-CO2 concentration state.',
'     - Plasma-insulin concentration.': '     - Light-intensity state following the imposed illumination profile.',
},
'quadrotor_altitude.rst': {
'     - Temperature state; the selected temperature is returned as the controlled output.': '     - Altitude state.',
'     - Microbial biomass or model-specific mass state.': '     - Vehicle-mass state.',
},
'soil_denitrification_aeration.rst': {
'     - Carbon or concentration state defined by the equations.': '     - Available-carbon concentration state.',
},
}

for name, mapping in repls.items():
    p = DOCS / name
    if not p.exists():
        continue
    text = p.read_text(encoding='utf-8')
    for old, new in mapping.items():
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

# Router: explicitly connect every symbol in the tables to the equations.
for name in ['network_router_fluid_queue.rst','network_router_fluid_queue_with_delay.rst','network_router_fluid_queue_with_large_delay.rst']:
    p = DOCS / name
    if not p.exists():
        continue
    text = p.read_text(encoding='utf-8')
    text = text.replace(':math:`r_{\\\\mathrm{in}}`', ':math:`r_{\\mathrm{in}}`')
    text = text.replace(':math:`r_{\\\\mathrm{out}}`', ':math:`r_{\\mathrm{out}}`')
    text = text.replace(':math:`\\\\tau_q`', ':math:`\\tau_q`')
    if name == 'network_router_fluid_queue.rst':
        marker = 'The implementation enforces the queue bounds by setting $\\dot q=0$ if the unconstrained derivative would move $q$ below $0$ or above $q_{\\max}$.\n'
        addition = '''\nThe controlled output and the additional reported signals are algebraic quantities derived from the state:\n\n.. math::\n\n   \\begin{aligned}\n   y=\\Delta q&=q-q_0, \\\\\n   r_{\\mathrm{in}}&=r, \\\\\n   r_{\\mathrm{out}}&=s(q), \\\\\n   \\tau_q&=\\frac{q}{\\max(r_{\\mathrm{out}},\\varepsilon)}.\n   \\end{aligned}\n\nThus $q$ is the physical queue state appearing in the ODE, while $\\Delta q$ is the controlled deviation output.\n'''
        if addition.strip() not in text:
            text = text.replace(marker, marker + addition)
    p.write_text(text, encoding='utf-8')

# Clarify the scope of the notation tables in every model document.
old = ('The first column gives the readable mathematical notation, the second gives the exact Python or SISO-interface name, '
       'and the third states the model-specific physical meaning. Thus the equations remain readable while every symbol can be traced back to the implementation.')
new = ('The first column gives the readable mathematical notation, the second gives the exact Python or SISO-interface name, '
       'and the third states the model-specific physical meaning. The table contains ODE states and algebraic signals reported by '
       '``algebraic_outputs()``. A reported signal need not be an independent state, but it must be explicitly defined by the equations, '
       'an auxiliary relation, or the implementation reference below.')
for p in DOCS.glob('*.rst'):
    text = p.read_text(encoding='utf-8')
    text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

print('patched', len(list(DOCS.glob('*.rst'))), 'model documents')
