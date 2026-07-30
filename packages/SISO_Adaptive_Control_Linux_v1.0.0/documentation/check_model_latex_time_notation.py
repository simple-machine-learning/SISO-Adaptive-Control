#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent / 'models'
PATTERNS = {
    'time argument inside bold vector symbol': r'\\mathbf\{[^}]*\(t\)',
    'time argument inside transpose marker': r'\\mathsf\{T\(t\)\}',
    'time argument inside real-number symbol': r'\\mathbb\{R\(t\)\}',
    'time argument inside tau parameter subscript': r'\\tau_\{[^}]*\(t\)',
    'time argument inside beta parameter subscript': r'\\beta_\{[^}]*\(t\)',
    'time argument inside roman identifier': r'\\mathrm\{[^}]*\(t\)',
    'incorrect derivative form dot{x(t)}': r'\\dot\{[^}]*\(t\)\}',
    'duplicated time argument': r'[A-Za-z_]+\(t\)\(t\)',
    'literal escaped newline': r'\\n',
}

errors = []
pages = sorted(ROOT.glob('*.rst'))
for page in pages:
    text = page.read_text(encoding='utf-8')
    for label, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            line = text.count('\n', 0, match.start()) + 1
            errors.append(f'{page.name}:{line}: {label}: {match.group(0)}')
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != '.. math::':
            continue
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines) or not lines[cursor].startswith('   '):
            errors.append(f'{page.name}:{index + 1}: empty or unindented math block')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'OK: {len(pages)} model pages passed the LaTeX/time-notation risk audit.')
