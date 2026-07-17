import pytest
from app.knowledge.retriever import HybridRetriever


class TestHybridRetriever:
    @pytest.fixture
    def retriever(self):
        return HybridRetriever()

    def test_search_returns_results(self, retriever):
        results = retriever.search("复数", top_k=3)
        assert len(results) >= 1

    def test_resolve_concept_name(self, retriever):
        assert retriever.resolve_concept_name("complex-1.1") == "复数定义与运算"
        assert retriever.resolve_concept_name("nonexistent") == "nonexistent"

    def test_is_concept_in_domain_exact(self, retriever):
        assert retriever.is_concept_in_domain("C-R方程") is True
        assert retriever.is_concept_in_domain("相对论") is False

    def test_all_curriculum_titles_in_domain(self, retriever):
        from pathlib import Path
        from app.knowledge.loader import load_curriculum
        curriculum_path = (
            Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
        )
        nodes = load_curriculum(str(curriculum_path))
        for node in nodes:
            assert retriever.is_concept_in_domain(node.title), f"'{node.title}' not in domain"
