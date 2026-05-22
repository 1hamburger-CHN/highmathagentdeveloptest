"""Nuclear option: global backslash escape, parse, unescape."""
import yaml

with open("data/seed/curriculum.yaml", "r", encoding="utf-8") as f:
    raw_text = f.read()

# Escape ALL backslashes globally
safe_text = raw_text.replace("\\", "\\\\")
raw = yaml.safe_load(safe_text)


def unescape(obj):
    if isinstance(obj, dict):
        return {k: unescape(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [unescape(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace("\\\\", "\\")
    return obj


raw = unescape(raw)
nodes = raw.get("nodes", [])
print(f"OK: Loaded {len(nodes)} nodes")
for n in nodes[:3]:
    c = n.get("content", {})
    defn = c.get("definition", "")[:80] if c.get("definition") else "(none)"
    print(f"  {n['id']}: {n['title']}")
    print(f"    definition preview: {defn}...")

# Test chunk_text generation
from app.knowledge.schema import KnowledgeNode

node0 = KnowledgeNode(
    id=nodes[0]["id"],
    title=nodes[0]["title"],
    definition=nodes[0]["content"].get("definition", ""),
    theorems=nodes[0]["content"].get("theorems", []),
    examples=nodes[0]["content"].get("examples", []),
    misconceptions=nodes[0]["content"].get("misconceptions", []),
    prerequisites=nodes[0].get("prerequisites", []),
    related=nodes[0].get("related", []),
)
chunk = node0.to_chunk_text()
print(f"\nFirst node chunk_text: {len(chunk)} chars")
print(chunk[:300])
