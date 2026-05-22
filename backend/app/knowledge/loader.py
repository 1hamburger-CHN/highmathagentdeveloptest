import yaml

from app.knowledge.schema import KnowledgeNode


def load_curriculum(path: str) -> list[KnowledgeNode]:
    """Load knowledge nodes from curriculum.yaml."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    nodes = []
    for item in raw.get("nodes", []):
        nodes.append(KnowledgeNode(
            id=item["id"],
            title=item["title"],
            definition=item.get("definition", ""),
            theorems=item.get("theorems", []),
            examples=item.get("examples", []),
            common_errors=item.get("common_errors", []),
            prerequisites=item.get("prerequisites", []),
            related=item.get("related", []),
        ))
    return nodes
