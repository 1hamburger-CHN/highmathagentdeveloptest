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

    # Class-level cache for known curriculum node titles and id→title map
    _known_titles: list[str] | None = None
    _id_to_title: dict[str, str] | None = None

    # Common abbreviation/synonym → curriculum title mapping
    # jieba + embedding matching fails on mixed-script abbreviations like "C-R方程"
    _concept_aliases: dict[str, str] = {
        "C-R方程": "解析函数与Cauchy-Riemann方程",
        "CR方程": "解析函数与Cauchy-Riemann方程",
        "柯西-黎曼方程": "解析函数与Cauchy-Riemann方程",
        "柯西黎曼方程": "解析函数与Cauchy-Riemann方程",
        "柯西积分公式": "Cauchy积分公式与高阶导数公式",
        "柯西定理": "Cauchy-Goursat定理",
        "柯西-古萨定理": "Cauchy-Goursat定理",
        "莫比乌斯变换": "共形映射与分式线性变换",
        "Mobius变换": "共形映射与分式线性变换",
        "棣莫弗公式": "复数的几何表示与棣莫弗公式",
        "De Moivre公式": "复数的几何表示与棣莫弗公式",
        "欧拉公式": "复数的几何表示与棣莫弗公式",
    }

    @classmethod
    def _load_curriculum_cache(cls):
        if cls._known_titles is None:
            from pathlib import Path
            from app.knowledge.loader import load_curriculum
            curriculum_path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
            nodes = load_curriculum(str(curriculum_path))
            cls._known_titles = [node.title for node in nodes]
            cls._id_to_title = {node.id: node.title for node in nodes}

    @classmethod
    def _load_known_titles(cls) -> list[str]:
        cls._load_curriculum_cache()
        return cls._known_titles

    @classmethod
    def resolve_concept_name(cls, concept: str) -> str:
        """Resolve a curriculum node ID to its title, or return the original."""
        cls._load_curriculum_cache()
        return cls._id_to_title.get(concept, concept)

    def is_concept_in_domain(self, concept: str, threshold: float = 0.35) -> bool:
        """Check if a concept is within the complex analysis knowledge base.

        Uses token-level matching against known titles first, then semantic search.
        """
        # Resolve node IDs (e.g. "complex-2.2") to titles BEFORE matching
        resolved = self.resolve_concept_name(concept)
        if resolved != concept:
            concept = resolved  # it was an ID — now use the title

        # Resolve common abbreviations/synonyms to curriculum titles
        alias_title = self._concept_aliases.get(concept)
        if alias_title:
            concept = alias_title

        import jieba
        concept_tokens = set(jieba.cut(concept))
        # Short queries (e.g. "C-R方程") often tokenise poorly — build bigrams for them
        if len(concept) <= 10:
            bigrams = {concept[i:i+2] for i in range(len(concept)-1)}
            concept_tokens |= bigrams
        for title in self._load_known_titles():
            # Direct substring match (handles exact containment)
            if concept in title or title in concept:
                return True
            # Token-level overlap — more robust than character overlap
            title_tokens = set(jieba.cut(title))
            common = concept_tokens & title_tokens
            if len(common) >= 2:
                return True
            # Single-token match is enough when concept is very short
            if len(concept) <= 10 and len(common) >= 1:
                return True
        # Semantic search fallback (lower threshold for short queries)
        sem_threshold = max(threshold - 0.10, 0.20) if len(concept) <= 10 else threshold
        results = self.search(concept, top_k=3)
        if not results:
            return False
        return any(r.get("score", 0) >= sem_threshold for r in results)
