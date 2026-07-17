from pathlib import Path
from app.knowledge.loader import load_curriculum


def test_loads_all_nodes():
    path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
    nodes = load_curriculum(str(path))
    assert len(nodes) == 19
    ids = [n.id for n in nodes]
    assert "complex-1.1" in ids
    assert "complex-7.1" in ids


def test_all_nodes_have_content():
    path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
    nodes = load_curriculum(str(path))
    for node in nodes:
        assert node.definition or node.theorems or node.examples, \
            f"{node.id} has no definition, theorems, or examples"
        assert node.title, f"{node.id} has no title"
