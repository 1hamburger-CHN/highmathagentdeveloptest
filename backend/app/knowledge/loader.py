import yaml

from app.knowledge.schema import KnowledgeNode


def load_curriculum(path: str) -> list[KnowledgeNode]:
    """Load knowledge nodes from curriculum.yaml."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    nodes = []
    for item in raw.get("nodes", []):
        content = item.get("content", {})
        nodes.append(KnowledgeNode(
            id=item["id"],
            title=item["title"],
            definition=content.get("definition", ""),
            theorems=content.get("theorems", []),
            examples=content.get("examples", []),
            misconceptions=content.get("misconceptions", []),
            prerequisites=item.get("prerequisites", []),
            related=item.get("related", []),
            difficulty=item.get("difficulty", 1),
            bloom_level=item.get("bloom_level", 1),
        ))
    return nodes
