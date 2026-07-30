from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parent/'models'
BAD=(
 'State, output, or auxiliary quantity defined explicitly',
 'corresponding model equation',
 'Equation-defined quantity',
 'State variable appearing in the model state vector',
)
issues=[]
for p in sorted(ROOT.glob('*.rst')):
    t=p.read_text(encoding='utf-8')
    for phrase in BAD:
        if phrase in t: issues.append(f'{p.name}: generic description: {phrase}')
    if '\\n' in t: issues.append(f'{p.name}: literal \\n escape')
    for m in re.finditer(r':math:`([^`]*)`',t):
        s=m.group(1)
        if s.count('{')!=s.count('}'): issues.append(f'{p.name}: unbalanced inline math: {s}')
        if '\\\\' in s: issues.append(f'{p.name}: doubled backslash in inline math: {s}')
        if re.search(r'\\mathrm(?!\{)',s): issues.append(f'{p.name}: malformed \\mathrm: {s}')
    lines=t.splitlines()
    for i,line in enumerate(lines):
        if line.strip()=='.. math::':
            j=i+1; buf=[]
            while j<len(lines) and (not lines[j].strip() or lines[j].startswith('   ')):
                if lines[j].startswith('   '): buf.append(lines[j].strip())
                j+=1
            s=' '.join(buf)
            if s.count('{')!=s.count('}'): issues.append(f'{p.name}:{i+1}: unbalanced block math')
            if re.search(r'\\mathrm(?!\{)',s): issues.append(f'{p.name}:{i+1}: malformed \\mathrm')
    # No units in list-table cells.
    in_table=False
    for i,line in enumerate(lines):
        if line.startswith('.. list-table::'): in_table=True
        elif in_table and line and not line.startswith(' ') and not line.startswith('..'): in_table=False
        if in_table and re.match(r'\s+- ',line) and re.search(r'\[[^\]]+\]\.?$',line):
            issues.append(f'{p.name}:{i+1}: bracketed unit in table cell')
if issues:
    print('\n'.join(issues)); sys.exit(1)
print(f'OK: {len(list(ROOT.glob("*.rst")))} model pages; no generic descriptions, malformed inline/block LaTeX, literal escapes, or units in tables.')
