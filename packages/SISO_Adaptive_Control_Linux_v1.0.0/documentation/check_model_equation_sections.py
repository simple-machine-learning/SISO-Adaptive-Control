#!/usr/bin/env python3
"""Validate separation of algebraic and differential model equations."""
from pathlib import Path
import re
import sys

MODELS = Path(__file__).resolve().parent / "models"


def section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:j if j >= 0 else None]


def normalized_equations(text: str) -> set[str]:
    equations: set[str] = set()
    for match in re.finditer(r"(?ms)^\\.\\. math::\\s*\\n\\s*\\n((?:   .*\\n?)+)", text):
        block = "\\n".join(
            line[3:] if line.startswith("   ") else line
            for line in match.group(1).splitlines()
        )
        block = re.sub(r"\\\\begin\\{aligned\\}|\\\\end\\{aligned\\}", "", block)
        for equation in re.split(r"\\\\\\\\|\\n\\s*\\n", block):
            equation = re.sub(r"\\s+", "", equation).strip(",.;")
            if equation:
                equations.add(equation)
    return equations


errors: list[str] = []
derivative_pattern = re.compile(
    r"\\\\dot\\s*(?:\\{|[A-Za-z])|"
    r"\\\\frac\\s*\\{(?:\\\\mathrm\\{d\\}|d)[^}]*\\}\\s*\\{(?:\\\\mathrm\\{d\\}t|dt)\\}|"
    r"\\b(?:d|D)[A-Za-z_{}]+/dt\\b"
)

for path in sorted(MODELS.glob("*.rst")):
    text = path.read_text(encoding="utf-8")
    auxiliary = section(text, "Static and auxiliary relations", "State equations")
    states = section(text, "State equations", "Output equation")

    if derivative_pattern.search(auxiliary):
        errors.append(f"{path.name}: time derivative found in Static and auxiliary relations")

    duplicates = normalized_equations(auxiliary) & normalized_equations(states)
    if duplicates:
        errors.append(
            f"{path.name}: equation duplicated between auxiliary and state sections: "
            + "; ".join(sorted(duplicates))
        )

if errors:
    print("Model-equation section audit failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"Model-equation section audit passed for {len(list(MODELS.glob('*.rst')))} pages.")
