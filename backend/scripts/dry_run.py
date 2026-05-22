"""Dry run: show which YAML lines need quote fixing."""
import re

PATH = "data/seed/curriculum.yaml"
with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

count = 0
for i, line in enumerate(lines, 1):
    # Find double-quoted strings containing backslash
    matches = re.findall(r'"([^"]*\\[^"]*)"', line)
    if matches:
        count += len(matches)
        for m in matches:
            display = m[:120] + "..." if len(m) > 120 else m
            print(f"  Line {i}: [{display}]")

print(f"\nTotal: {count} strings to fix")
