#!/usr/bin/env python3
from pathlib import Path
import ast,re,sys
ROOT=Path(__file__).resolve().parents[1]; MODELS=ROOT/'documentation/models'; PYMODELS=ROOT/'apps/simulated/plant_models'
def canon(s): return re.sub(r'[{}\\\s]','',s)
def fields(py):
 tree=ast.parse(py.read_text(encoding='utf-8')); out=[]
 for n in tree.body:
  if isinstance(n,ast.ClassDef) and n.name=='PlantParams':
   for x in n.body:
    if isinstance(x,ast.AnnAssign) and isinstance(x.target,ast.Name) and x.target.id!='plant_model_name': out.append(x.target.id)
 return out
def blocks(eq):return re.findall(r'(?ms)^\.\. math::\s*\n\s*\n((?:   .*\n?)+)',eq)
def lhs(block):
 out=[]
 for raw in block.splitlines():
  line=raw.strip()
  if ':math:`' in line: continue
  if '&=' in line:a=line.split('&=',1)[0]
  elif '=' in line:a=line.split('=',1)[0]
  else:continue
  a=a.strip().rstrip('\\,;'); a=re.sub(r'^\\dot\s*\{?([^{}]+)\}?$',r'\1',a); a=re.sub(r'^\\ddot\s*\{?([^{}]+)\}?$',r'\1',a)
  if a and len(a)<60 and not any(x in a for x in ['\\begin','\\end','\\text','\\in']): out.append(canon(a))
 return out
errs=[]; checked=0
for p in sorted(MODELS.glob('*.rst')):
 t=p.read_text(encoding='utf-8'); checked+=1
 # units in any list-table cell
 in_table=False
 for n,line in enumerate(t.splitlines(),1):
  if line.startswith('.. list-table::'): in_table=True
  elif in_table and line and not line.startswith(' ') and not line.startswith(':'): in_table=False
  if in_table and (line.strip()=='- Unit' or re.search(r'\[[A-Za-z°/%][^\]]*\]\s*$',line)):
   errs.append(f'{p.name}:{n}: unit remains in table')
 listed={canon(x) for x in re.findall(r':math:`([^`]+)`',t)}
 if 'Model equations' in t:
  eq=t.split('Model equations',1)[1].split('Parameter implementation',1)[0]
  miss=[]
  for b in blocks(eq):
   for x in lhs(b):
    if x not in listed and x not in {'mathbfx','T'}: miss.append(x)
  if miss: errs.append(f'{p.name}: equation-defined symbols absent from tables: {sorted(set(miss))}')
 mm=re.search(r'Python model: ``plant_models\.([^`]+)``',t)
 if mm:
  py=PYMODELS/(mm.group(1)+'.py')
  if py.exists() and '\nParameters\n' in t:
   sec=t.split('\nParameters\n',1)[1].split('\nNotation and variables\n',1)[0]
   names=set(re.findall(r'\n\s*- ``([A-Za-z_][A-Za-z0-9_]*)``',sec))
   miss=[x for x in fields(py) if x not in names]
   if miss: errs.append(f'{p.name}: PlantParams fields absent from parameter table: {miss}')
if errs:
 print('\n'.join(errs));sys.exit(1)
print(f'OK: {checked} model pages; no table units, all equation-defined symbols are tabulated, and all local PlantParams fields are documented.')
