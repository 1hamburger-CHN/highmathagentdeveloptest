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
        for i, (id_, doc) in enumerate(zip(ids, docs)):
            formatted.append({"id": id_, "content": doc, "score": 1.0})
        return formatted
