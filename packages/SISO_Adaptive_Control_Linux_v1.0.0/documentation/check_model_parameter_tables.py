#!/usr/bin/env python3
from __future__ import annotations
import ast, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODELS=ROOT/'documentation'/'models'
PYMODELS=ROOT/'apps'/'simulated'/'plant_models'

def fields_for(py: Path):
    tree=ast.parse(py.read_text(encoding='utf-8'), filename=str(py))
    imports={}
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module:
            for a in n.names:
                imports[a.asname or a.name]=(n.module,a.name)
    own=[]; bases=[]
    for n in tree.body:
        if isinstance(n,ast.ClassDef) and n.name=='PlantParams':
            bases=[]
            for b in n.bases:
                if isinstance(b,ast.Name): bases.append(('name',b.id))
                elif isinstance(b,ast.Attribute) and isinstance(b.value,ast.Name): bases.append(('attr',b.value.id,b.attr))
            for it in n.body:
                if isinstance(it,ast.AnnAssign) and isinstance(it.target,ast.Name) and it.target.id!='plant_model_name': own.append(it.target.id)
    inherited=[]
    for b in bases:
        if b[0]=='name' and b[1] in imports:
            mod,orig=imports[b[1]]
            if orig=='PlantParams':
                candidate=PYMODELS/(mod.split('.')[-1]+'.py')
                if candidate.exists(): inherited.extend(fields_for(candidate))
        elif b[0]=='attr' and b[2]=='PlantParams' and b[1] in imports:
            mod,orig=imports[b[1]]
            candidate=PYMODELS/(orig+'.py')
            if candidate.exists(): inherited.extend(fields_for(candidate))
    return list(dict.fromkeys(inherited+own))

errors=[]; checked=0
for rst in sorted(MODELS.glob('*.rst')):
    text=rst.read_text(encoding='utf-8')
    mm=re.search(r'Python model: ``plant_models\.([^`]+)``',text)
    if not mm: continue
    name=mm.group(1); py=PYMODELS/f'{name}.py'
    if not py.exists(): errors.append(f'{rst.name}: missing implementation'); continue
    checked+=1
    if r'\\n' in text: errors.append(f'{rst.name}: literal \\n found in equations')
    if '\nParameters\n' not in text: errors.append(f'{rst.name}: missing Parameters section'); continue
    sec=text.split('\nParameters\n',1)[1]
    if '\nNotation and variables\n' in sec: sec=sec.split('\nNotation and variables\n',1)[0]
    rows=re.findall(r'\* - :math:`([^`]+)`\s*\n\s*- ``([A-Za-z_][A-Za-z0-9_]*)``\s*\n\s*- ``([^`]+)``\s*\n\s*- ([^\n]+)',sec)
    names=[r[1] for r in rows]
    exp=fields_for(py)
    miss=[x for x in exp if x not in names]; extra=[x for x in names if x not in exp]
    dup=sorted({x for x in names if names.count(x)>1})
    if miss: errors.append(f'{rst.name}: missing fields {miss}')
    if extra: errors.append(f'{rst.name}: unknown fields {extra}')
    if dup: errors.append(f'{rst.name}: duplicate fields {dup}')
    for sym,n,default,meaning in rows:
        if not sym.strip() or not meaning.strip(): errors.append(f'{rst.name}: incomplete row {n}')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print(f'OK: {checked} model pages; all editable parameters, including inherited delayed-model parameters, have exactly one complete table row; no literal \\n remains.')
