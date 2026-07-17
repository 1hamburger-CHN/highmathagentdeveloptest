import hashlib
import time

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.knowledge.embedder import BGEM3Embedder


class HybridRetriever:
    """Hybrid retrieval: dense (BGE-M3) + sparse (keyword fallback).

    Searches across both the curriculum knowledge base and the textbook.
    """

    def __init__(self):
        self._search_cache: dict = {}
        self._cache_ttl: int = 300  # 5 min
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embedder = BGEM3Embedder(settings.embedding_model)
        self.collection = self.client.get_or_create_collection(
            name="complex_analysis",
            embedding_function=self.embedder,
        )
        # Textbook collection — may not exist if not yet indexed
        try:
            self.textbook_collection = self.client.get_collection(
                name="textbook",
                embedding_function=self.embedder,
            )
        except Exception:
            self.textbook_collection = None
        # Handout collection (chapter lecture slides)
        try:
            self.handout_collection = self.client.get_collection(
                name="handouts",
                embedding_function=self.embedder,
            )
        except Exception:
            self.handout_collection = None
        # Exercise collection (practice problems)
        try:
            self.exercise_collection = self.client.get_collection(
                name="exercises",
                embedding_function=self.embedder,
            )
        except Exception:
            self.exercise_collection = None

    def _do_search(self, query: str, top_k: int = 5) -> list[dict]:
        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            return self._format_results(results)
        except Exception:
            return self._keyword_fallback(query, top_k)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        cache_key = hashlib.md5(f"{query}:{top_k}".encode()).hexdigest()
        now = time.time()
        if cache_key in self._search_cache:
            entry = self._search_cache[cache_key]
            if now - entry["ts"] < self._cache_ttl:
                return entry["results"]
        results = self._do_search(query, top_k)
        self._search_cache[cache_key] = {"results": results, "ts": now}
        # Prune old entries (>cache_ttl old)
        self._search_cache = {k: v for k, v in self._search_cache.items() if now - v["ts"] < self._cache_ttl}
        return results

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

    def search_textbook(self, query: str, top_k: int = 3) -> list[dict]:
        """Search the textbook collection for supplementary content."""
        if self.textbook_collection is None:
            return []
        try:
            results = self.textbook_collection.query(query_texts=[query], n_results=top_k)
            return self._format_results(results)
        except Exception:
            return []

    def search_handouts(self, query: str, top_k: int = 3) -> list[dict]:
        """Search chapter handouts (lecture slides)."""
        if self.handout_collection is None:
            return []
        try:
            results = self.handout_collection.query(query_texts=[query], n_results=top_k)
            return self._format_results(results)
        except Exception:
            return []

    def search_exercises(self, query: str, top_k: int = 3) -> list[dict]:
        """Search practice exercises (multiple choice, fill-in-the-blank)."""
        if self.exercise_collection is None:
            return []
        try:
            results = self.exercise_collection.query(query_texts=[query], n_results=top_k)
            return self._format_results(results)
        except Exception:
            return []

    def search_all(self, query: str, top_k: int = 3) -> dict[str, list[dict]]:
        """Search across all collections. Returns dict with keys: kb, textbook, handouts, exercises."""
        result = {"kb": self.search(query, top_k=top_k)}
        if self.textbook_collection:
            result["textbook"] = self.search_textbook(query, top_k=top_k)
        if self.handout_collection:
            result["handouts"] = self.search_handouts(query, top_k=top_k)
        if self.exercise_collection:
            result["exercises"] = self.search_exercises(query, top_k=top_k)
        return result

    # Class-level cache for known curriculum node titles and id→title map
    _known_titles: list[str] | None = None
    _id_to_title: dict[str, str] | None = None

    # Common abbreviation/synonym → curriculum title mapping
    # jieba + embedding matching fails on mixed-script abbreviations like "C-R方程"
    # Also handles English snake_case terms that LLMs output as concept identifiers
    # fmt: off
    _concept_aliases: dict[str, str] = {
        # ==================================================================
        # complex-1.1  复数定义与运算
        # ==================================================================
        "复数":                  "复数定义与运算",
        "复数运算":              "复数定义与运算",
        "complex_number":        "复数定义与运算",
        "complex_numbers":       "复数定义与运算",
        "complex":               "复数定义与运算",
        "虚数":                  "复数定义与运算",
        "imaginary_number":       "复数定义与运算",
        "复数的模":              "复数定义与运算",
        "共轭复数":              "复数定义与运算",
        "complex_conjugate":     "复数定义与运算",
        "modulus":               "复数定义与运算",

        # ==================================================================
        # complex-1.2  复数的几何表示与棣莫弗公式
        # ==================================================================
        "复平面":                "复数的几何表示与棣莫弗公式",
        "极坐标":                "复数的几何表示与棣莫弗公式",
        "辐角":                  "复数的几何表示与棣莫弗公式",
        "辐角主值":              "复数的几何表示与棣莫弗公式",
        "复数几何":              "复数的几何表示与棣莫弗公式",
        "complex_plane":         "复数的几何表示与棣莫弗公式",
        "de_moivre":             "复数的几何表示与棣莫弗公式",
        "De Moivre公式":         "复数的几何表示与棣莫弗公式",
        "棣莫弗公式":            "复数的几何表示与棣莫弗公式",
        "欧拉公式":              "复数的几何表示与棣莫弗公式",
        "euler_formula":         "复数的几何表示与棣莫弗公式",
        "euler":                 "复数的几何表示与棣莫弗公式",
        "argument":              "复数的几何表示与棣莫弗公式",
        "polar_form":            "复数的几何表示与棣莫弗公式",

        # ==================================================================
        # complex-1.3  复数的n次方根
        # ==================================================================
        "n次方根":               "复数的n次方根",
        "单位根":                "复数的n次方根",
        "n次根":                 "复数的n次方根",
        "nth_root":              "复数的n次方根",
        "roots_of_unity":        "复数的n次方根",
        "complex_root":          "复数的n次方根",
        "root_of_unity":         "复数的n次方根",

        # ==================================================================
        # complex-2.1  复变函数的极限与连续
        # ==================================================================
        "复极限":                "复变函数的极限与连续",
        "复连续":                "复变函数的极限与连续",
        "复变极限":              "复变函数的极限与连续",
        "complex_limit":         "复变函数的极限与连续",
        "complex_continuity":    "复变函数的极限与连续",
        "limit":                 "复变函数的极限与连续",
        "continuity":            "复变函数的极限与连续",

        # ==================================================================
        # complex-2.2  解析函数与Cauchy-Riemann方程
        # ==================================================================
        "解析函数":              "解析函数与Cauchy-Riemann方程",
        "解析":                  "解析函数与Cauchy-Riemann方程",
        "C-R方程":               "解析函数与Cauchy-Riemann方程",
        "CR方程":                "解析函数与Cauchy-Riemann方程",
        "C-R条件":               "解析函数与Cauchy-Riemann方程",
        "柯西-黎曼方程":         "解析函数与Cauchy-Riemann方程",
        "柯西黎曼方程":           "解析函数与Cauchy-Riemann方程",
        "柯西黎曼条件":           "解析函数与Cauchy-Riemann方程",
        "复可导":                "解析函数与Cauchy-Riemann方程",
        "复可微":                "解析函数与Cauchy-Riemann方程",
        "全纯函数":              "解析函数与Cauchy-Riemann方程",
        "analytic_function":     "解析函数与Cauchy-Riemann方程",
        "cauchy_riemann":        "解析函数与Cauchy-Riemann方程",
        "cauchy_riemann_equation": "解析函数与Cauchy-Riemann方程",
        "holomorphic":            "解析函数与Cauchy-Riemann方程",
        "analytic":              "解析函数与Cauchy-Riemann方程",
        "cauchy":                "解析函数与Cauchy-Riemann方程",
        "riemann":               "解析函数与Cauchy-Riemann方程",
        "complex_differentiable": "解析函数与Cauchy-Riemann方程",
        "differentiable":        "解析函数与Cauchy-Riemann方程",

        # ==================================================================
        # complex-2.3  调和函数与共轭调和函数
        # ==================================================================
        "调和函数":              "调和函数与共轭调和函数",
        "共轭调和":              "调和函数与共轭调和函数",
        "共轭调和函数":          "调和函数与共轭调和函数",
        "拉普拉斯方程":          "调和函数与共轭调和函数",
        "Laplace方程":           "调和函数与共轭调和函数",
        "harmonic_function":     "调和函数与共轭调和函数",
        "conjugate_harmonic":    "调和函数与共轭调和函数",
        "harmonic":              "调和函数与共轭调和函数",
        "laplace_equation":      "调和函数与共轭调和函数",

        # ==================================================================
        # complex-3.1  复指数函数与对数函数
        # ==================================================================
        "复指数":                "复指数函数与对数函数",
        "复指数函数":            "复指数函数与对数函数",
        "复对数":                "复指数函数与对数函数",
        "复对数函数":            "复指数函数与对数函数",
        "Ln函数":                "复指数函数与对数函数",
        "多值函数":              "复指数函数与对数函数",
        "分支":                  "复指数函数与对数函数",
        "complex_exponential":   "复指数函数与对数函数",
        "complex_logarithm":     "复指数函数与对数函数",
        "exponential":           "复指数函数与对数函数",
        "logarithm":             "复指数函数与对数函数",
        "branch_cut":            "复指数函数与对数函数",
        "branch_point":          "复指数函数与对数函数",
        "multi_valued":          "复指数函数与对数函数",

        # ==================================================================
        # complex-3.2  复幂函数与三角函数
        # ==================================================================
        "复幂":                  "复幂函数与三角函数",
        "复幂函数":              "复幂函数与三角函数",
        "复三角":                "复幂函数与三角函数",
        "复三角函数":            "复幂函数与三角函数",
        "complex_power":         "复幂函数与三角函数",
        "complex_trigonometric": "复幂函数与三角函数",
        "trigonometric":         "复幂函数与三角函数",
        "power":                 "复幂函数与三角函数",

        # ==================================================================
        # complex-4.1  复积分的定义与基本性质
        # ==================================================================
        "复积分":                "复积分的定义与基本性质",
        "围道积分":              "复积分的定义与基本性质",
        "ML估计":                "复积分的定义与基本性质",
        "模不等式":              "复积分的定义与基本性质",
        "积分模":                "复积分的定义与基本性质",
        "complex_integration":   "复积分的定义与基本性质",
        "complex_integral":      "复积分的定义与基本性质",
        "integration":           "复积分的定义与基本性质",
        "integral":              "复积分的定义与基本性质",
        "ml_inequality":         "复积分的定义与基本性质",
        "contour":               "复积分的定义与基本性质",

        # ==================================================================
        # complex-4.2  Cauchy-Goursat定理
        # ==================================================================
        "柯西定理":              "Cauchy-Goursat定理",
        "柯西-古萨定理":         "Cauchy-Goursat定理",
        "柯西积分定理":          "Cauchy-Goursat定理",
        "路径无关":              "Cauchy-Goursat定理",
        "积分路径无关":          "Cauchy-Goursat定理",
        "复合闭路定理":          "Cauchy-Goursat定理",
        "cauchy_goursat":        "Cauchy-Goursat定理",
        "cauchy_theorem":        "Cauchy-Goursat定理",
        "goursat":               "Cauchy-Goursat定理",
        "path_independence":     "Cauchy-Goursat定理",

        # ==================================================================
        # complex-4.3  Cauchy积分公式与高阶导数公式
        # ==================================================================
        "柯西积分公式":          "Cauchy积分公式与高阶导数公式",
        "高阶导数公式":          "Cauchy积分公式与高阶导数公式",
        "高阶导数":              "Cauchy积分公式与高阶导数公式",
        "Morera定理":            "Cauchy积分公式与高阶导数公式",
        "莫雷拉定理":            "Cauchy积分公式与高阶导数公式",
        "cauchy_integral_formula": "Cauchy积分公式与高阶导数公式",
        "higher_order_derivative": "Cauchy积分公式与高阶导数公式",
        "cauchy_derivative":     "Cauchy积分公式与高阶导数公式",
        "morera":                "Cauchy积分公式与高阶导数公式",

        # ==================================================================
        # complex-5.1  泰勒级数
        # ==================================================================
        "泰勒展开":              "泰勒级数",
        "泰勒":                  "泰勒级数",
        "幂级数":                "泰勒级数",
        "收敛半径":              "泰勒级数",
        "收敛圆":                "泰勒级数",
        "taylor_series":         "泰勒级数",
        "taylor":                "泰勒级数",
        "power_series":          "泰勒级数",
        "convergence_radius":    "泰勒级数",

        # ==================================================================
        # complex-5.2  洛朗级数
        # ==================================================================
        "洛朗展开":              "洛朗级数",
        "洛朗":                  "洛朗级数",
        "Laurent展开":           "洛朗级数",
        "laurent_series":        "洛朗级数",
        "laurent":               "洛朗级数",

        # ==================================================================
        # complex-6.1  孤立奇点分类
        # ==================================================================
        "奇点":                  "孤立奇点分类",
        "孤立奇点":              "孤立奇点分类",
        "可去奇点":              "孤立奇点分类",
        "极点":                  "孤立奇点分类",
        "本性奇点":              "孤立奇点分类",
        "m阶极点":               "孤立奇点分类",
        "奇点分类":              "孤立奇点分类",
        "singularity":           "孤立奇点分类",
        "isolated_singularity":  "孤立奇点分类",
        "essential_singularity": "孤立奇点分类",
        "removable_singularity": "孤立奇点分类",
        "pole":                  "孤立奇点分类",

        # ==================================================================
        # complex-6.2  留数与留数定理
        # ==================================================================
        "留数":                  "留数与留数定理",
        "留数定理":              "留数与留数定理",
        "留数计算":              "留数与留数定理",
        "residue":               "留数与留数定理",
        "residue_theorem":       "留数与留数定理",

        # ==================================================================
        # complex-6.3  留数在实积分中的应用
        # ==================================================================
        "留数应用":              "留数在实积分中的应用",
        "实积分":                "留数在实积分中的应用",
        "反常积分":              "留数在实积分中的应用",
        "有理函数积分":          "留数在实积分中的应用",
        "三角函数积分":          "留数在实积分中的应用",
        "上半平面围道":          "留数在实积分中的应用",
        "Jordan引理":            "留数在实积分中的应用",
        "contour_integration":   "留数在实积分中的应用",
        "real_integral":         "留数在实积分中的应用",
        "improper_integral":     "留数在实积分中的应用",
        "jordan_lemma":          "留数在实积分中的应用",

        # ==================================================================
        # complex-7.1  共形映射与分式线性变换
        # ==================================================================
        "共形映射":              "共形映射与分式线性变换",
        "保角映射":              "共形映射与分式线性变换",
        "保形映射":              "共形映射与分式线性变换",
        "分式线性变换":          "共形映射与分式线性变换",
        "莫比乌斯变换":          "共形映射与分式线性变换",
        "Mobius变换":            "共形映射与分式线性变换",
        "Möbius变换":            "共形映射与分式线性变换",
        "conformal_mapping":     "共形映射与分式线性变换",
        "mobius_transformation": "共形映射与分式线性变换",
        "mobius_transform":      "共形映射与分式线性变换",
        "linear_fractional":     "共形映射与分式线性变换",
        "conformal":             "共形映射与分式线性变换",
        "mobius":                "共形映射与分式线性变换",
        "angle_preserving":      "共形映射与分式线性变换",

        # ==================================================================
        # complex-8.1  傅里叶变换的基本概念与性质
        # ==================================================================
        "傅里叶变换":            "傅里叶变换的基本概念与性质",
        "傅里叶":                "傅里叶变换的基本概念与性质",
        "Fourier变换":           "傅里叶变换的基本概念与性质",
        "傅立叶变换":            "傅里叶变换的基本概念与性质",
        "频谱":                  "傅里叶变换的基本概念与性质",
        "频谱函数":              "傅里叶变换的基本概念与性质",
        "fourier_transform":     "傅里叶变换的基本概念与性质",
        "fourier":               "傅里叶变换的基本概念与性质",
        "FT":                    "傅里叶变换的基本概念与性质",

        # ==================================================================
        # complex-8.2  拉普拉斯变换及其应用
        # ==================================================================
        "拉普拉斯变换":          "拉普拉斯变换及其应用",
        "拉普拉斯":              "拉普拉斯变换及其应用",
        "Laplace变换":           "拉普拉斯变换及其应用",
        "拉氏变换":              "拉普拉斯变换及其应用",
        "s域分析":               "拉普拉斯变换及其应用",
        "传递函数":              "拉普拉斯变换及其应用",
        "laplace_transform":     "拉普拉斯变换及其应用",
        "laplace":               "拉普拉斯变换及其应用",
    }
    # fmt: on

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

        # Normalize snake_case English terms (e.g. "complex_number" → check each word alias)
        # LLMs often output these as concept identifiers; jieba can't tokenise them
        if "_" in concept and concept.isascii():
            if not alias_title:
                # Try underscore-replaced form as alias key first
                normalized = concept.replace("_", " ")
                alias_title = self._concept_aliases.get(normalized)
                if alias_title:
                    concept = alias_title
            if not alias_title:
                # Fallback: check each English word individually as an alias key
                words = [w for w in concept.replace("_", " ").lower().split() if len(w) > 1]
                for word in words:
                    word_alias = self._concept_aliases.get(word)
                    if word_alias:
                        concept = word_alias
                        break

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
