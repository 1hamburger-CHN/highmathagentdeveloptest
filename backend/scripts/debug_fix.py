"""Debug: show how fix_line transforms problematic lines."""
import re

PATH = "data/seed/curriculum.yaml"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()


def fix_line(line: str) -> tuple[str, bool]:
    m = re.match(r'^(\s+(?:-\s)?(?:\w[\w\s-]*:\s)?)"(.+)"(\s*)$', line)
    if not m:
        return line, False

    before, inner, after = m.groups()

    # Convert inner ASCII " pairs to Unicode curly quotes
    result = []
    quote_open = True
    for ch in inner:
        if ch == '"':
            result.append('“' if quote_open else '”')
            quote_open = not quote_open
        else:
            result.append(ch)
    inner = ''.join(result)

    # Escape backslashes
    inner = inner.replace('\\', '\\\\')

    return f'{before}"{inner}"{after}', True


for i, line in enumerate(lines):
    stripped = line.rstrip('\n\r')
    fixed, changed = fix_line(stripped)
    if changed:
        print(f"--- Line {i+1} ---")
        print(f"ORIG: {stripped[:200]}")
        print(f"FIXD: {fixed[:200]}")
        print()
