"""Debug YAML preprocessing — test the escape/unescape approach."""
import re
import yaml

with open("data/seed/curriculum.yaml", "r", encoding="utf-8") as f:
    raw_text = f.read()

print(f"Original file: {len(raw_text)} chars, {len(raw_text.splitlines())} lines")


def escape_backslashes(m):
    inner = m.group(1)
    return '"' + inner.replace("\\", "\\\\") + '"'


safe_text = re.sub(r'"([^"]*)"', escape_backslashes, raw_text)

try:
    raw = yaml.safe_load(safe_text)
    print(f"YAML parsed OK. Top keys: {list(raw.keys())}")
    nodes = raw.get("nodes", [])
    print(f"Nodes: {len(nodes)}")
    for n in nodes[:3]:
        print(f"  {n['id']}: {n['title']}")
except Exception as e:
    print(f"Error: {e}")
    # Show context around error location
    lines = safe_text.splitlines()
    for i in range(max(0, 26), min(len(lines), 35)):
        line_text = lines[i][:150]
        print(f"  L{i+1}: {line_text}")
