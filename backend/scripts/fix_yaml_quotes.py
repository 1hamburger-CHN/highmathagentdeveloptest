"""Fix curriculum.yaml: convert all inline YAML double-quoted values to
single-quoted, handling embedded Chinese quotes and trailing explanations.

Key insight: content like  - "term" — explanation
has the explanation OUTSIDE the YAML string, which is invalid.
The entire line content must be inside the string value.
"""
import re
import yaml

PATH = "data/seed/curriculum.yaml"

with open(PATH, "r", encoding="utf-8") as f:
    raw_text = f.read()


def fix_line(line: str) -> tuple[str, bool]:
    # Pattern A: key: "value"  — standard key-value with " at end
    m = re.match(r'^(\s+(?:-\s)?\w[\w\s-]*:\s)"(.+)"(\s*)$', line)
    if m:
        before, inner, after = m.groups()
        inner = inner.replace("'", "''")
        return f"{before}'{inner}'{after}", True

    # Pattern B: - "value" with " at very end
    m = re.match(r'^(\s+-\s)"(.+)"(\s*)$', line)
    if m:
        before, inner, after = m.groups()
        inner = inner.replace("'", "''")
        # Convert inner " pairs to Unicode curly quotes
        result = []
        quote_open = True
        for ch in inner:
            if ch == '"':
                result.append('“' if quote_open else '”')
                quote_open = not quote_open
            else:
                result.append(ch)
        inner = ''.join(result)
        return f"{before}'{inner}'{after}", True

    # Pattern C: - "value" rest  — Chinese quote with trailing explanation
    # The entire line after "- " should be the value
    m = re.match(r'^(\s+-\s)"(.+)"(\s+\S.*)$', line)
    if m:
        before, inner, after = m.groups()
        # Convert ALL " to Unicode curly quotes in the full content
        full = inner + after
        result = []
        quote_open = True
        for ch in full:
            if ch == '"':
                result.append('“' if quote_open else '”')
                quote_open = not quote_open
            else:
                result.append(ch)
        full = ''.join(result)
        full = full.replace("'", "''")
        return f"{before}'{full}'", True

    return line, False


lines = raw_text.splitlines(keepends=True)
fixed_lines = []
changes = 0

for line in lines:
    stripped = line.rstrip('\n\r')
    new_line, changed = fix_line(stripped)
    if changed:
        changes += 1
    fixed_lines.append(new_line + '\n')

fixed_text = ''.join(fixed_lines)

try:
    raw = yaml.safe_load(fixed_text)
    nodes = raw.get("nodes", [])
    print(f"OK: {len(nodes)} nodes parsed ({changes} lines fixed)")
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(fixed_text)
    print(f"Written to {PATH}")
    for n in nodes[:3]:
        print(f"  {n['id']}: {n['title']}")

except yaml.YAMLError as e:
    print(f"PARSE FAILED: {e}")
    all_lines = fixed_text.splitlines()
    # Find the error line
    for i in range(max(0, 27), min(len(all_lines), 35)):
        print(f"  L{i+1}: {all_lines[i][:200]}")
