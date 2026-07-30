from pathlib import Path
root=Path(__file__).resolve().parent/'documentation'/'_build'/'html'/'models'
repls={
'vx':'v','Bm':'m','Fr':'F_r','Vc':'V','qp':'q_p','qout':'q_{\\mathrm{out}}','qnet':'q_{\\mathrm{net}}',
'nf':'f','Qc':'Q_c','xL':'x_L','xT':'x','vT':'v','yL':'y_L','Fd':'F','Fstop':'F_e',
'Th':'T_h','Tc':'T_c','QP':'Q_{P,h}','QJ':'Q_J','CCO_{2}':'C','QCO_{2}':'Q',
'Microbial biomass or model-specific mass state.':'Actual corrector-magnet field state after first-order actuator dynamics.',
'Position or displacement state specified by this mechanical model.':'Transverse beam-position state.',
'Carbon or concentration state defined by the equations.':'Allocated compute-capacity state after first-order provisioning dynamics.',
'Volumetric soil-moisture state.':'Payload sway-angle state.',
'Concentration state whose physical meaning is defined by the model title and equations.':'Dissolved-CO2 concentration state.',
'Plasma-insulin concentration.':'Light-intensity state following the imposed illumination profile.',
'Temperature state; the selected temperature is returned as the controlled output.':'Chip-temperature state.',
}
for p in root.glob('*.html'):
    t=p.read_text(encoding='utf-8')
    for a,b in repls.items():
        t=t.replace(a,b)
    old=('The first column gives the readable mathematical notation, the second gives the exact Python or SISO-interface name, and the third states the model-specific physical meaning. Thus the equations remain readable while every symbol can be traced back to the implementation.')
    new=('The first column gives the readable mathematical notation, the second gives the exact Python or SISO-interface name, and the third states the model-specific physical meaning. The table contains ODE states and algebraic signals reported by <code class="docutils literal notranslate"><span class="pre">algebraic_outputs()</span></code>. A reported signal need not be an independent state, but it must be explicitly defined by the equations, an auxiliary relation, or the implementation reference below.')
    t=t.replace(old,new)
    p.write_text(t,encoding='utf-8')

p=root/'network_router_fluid_queue.html'
if p.exists():
    t=p.read_text(encoding='utf-8')
    anchor='<p>The implementation enforces the queue bounds by setting $dot q=0$ if the unconstrained derivative would move $q$ below $0$ or above $q_{max}$.</p>'
    block='''<p>The controlled output and the additional reported signals are algebraic quantities derived from the state:</p>\n<div class="math notranslate nohighlight">\n\\[\\begin{aligned}\ny=\\Delta q&amp;=q-q_0, \\\\\nr_{\\mathrm{in}}&amp;=r, \\\\\nr_{\\mathrm{out}}&amp;=s(q), \\\\\n\\tau_q&amp;=\\frac{q}{\\max(r_{\\mathrm{out}},\\varepsilon)}.\n\\end{aligned}\\]\n</div>\n<p>Thus <span class="math notranslate nohighlight">\\(q\\)</span> is the physical queue state appearing in the ODE, while <span class="math notranslate nohighlight">\\(\\Delta q\\)</span> is the controlled deviation output.</p>'''
    if block not in t:
        t=t.replace(anchor,anchor+'\n'+block)
    p.write_text(t,encoding='utf-8')
print('patched html')
