import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.knowledge.embedder import BGEM3Embedder


class HybridRetriever:
    """Hybrid retrieval: dense (BGE-M3) + sparse (keyword fallback)."""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedder = BGEM3Embedder(settings.embedding_model)
        self.collection = self.client.get_or_create_collection(
            name="complex_analysis",
            embedding_function=self.embedder,
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            return self._format_results(results)
        except Exception:
            return self._keyword_fallback(query, top_k)

    def _keyword_fallback(self, query: str, top_k: int) -> list[dict]:
        """Keyword match fallback when ChromaDB is unavailable."""
        import jieba
        keywords = set(jieba.cut(query))
        all_docs = self.collection.get()
        if not all_docs["documents"]:
            return []
        scored = []
        for i, doc in enumerate(all_docs["documents"]):
            if doc is None:
                continue
            score = sum(1 for kw in keywords if kw in doc)
            if score > 0:
                scored.append({"id": all_docs["ids"][i], "content": doc, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _format_results(self, results: dict) -> list[dict]:
        formatted = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []
        for i, (id_, doc) in enumerate(zip(ids, docs)):
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            formatted.append({"id": id_, "content": doc, "score": score})
        return formatted

    # Class-level cache for known curriculum node titles
    _known_titles: list[str] | None = None

    @classmethod
    def _load_known_titles(cls) -> list[str]:
        if cls._known_titles is None:
            from pathlib import Path
            from app.knowledge.loader import load_curriculum
            curriculum_path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
            nodes = load_curriculum(str(curriculum_path))
            cls._known_titles = [node.title for node in nodes]
        return cls._known_titles

    def is_concept_in_domain(self, concept: str, threshold: float = 0.45) -> bool:
        """Check if a concept is within the complex analysis knowledge base.

        Uses keyword match against known titles first, then semantic search.
        """
        for title in self._load_known_titles():
            if concept in title or title in concept:
                return True
            # Significant character overlap
            overlap = set(title) & set(concept)
            if len(overlap) >= max(2, len(title) * 0.4):
                return True
        # Semantic search fallback
        results = self.search(concept, top_k=3)
        if not results:
            return False
        return any(r.get("score", 0) >= threshold for r in results)
