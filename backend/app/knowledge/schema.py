from dataclasses import dataclass, field


@dataclass
class KnowledgeNode:
    id: str
    title: str
    definition: str = ""
    theorems: list[dict] = field(default_factory=list)  # [{statement, proof?}]
    examples: list[dict] = field(default_factory=list)  # [{question, solution}]
    misconceptions: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    difficulty: int = 1
    bloom_level: int = 1

    def to_chunk_text(self) -> str:
        """Render node as searchable text for embedding."""
        parts = [f"# {self.title}", ""]

        if self.definition:
            parts.append(self.definition)
            parts.append("")

        for t in self.theorems:
            stmt = t.get("statement", "")
            parts.append(f"定理: {stmt}")
            proof = t.get("proof", "")
            if proof:
                parts.append(f"证明: {proof}")

        if self.theorems:
            parts.append("")

        for e in self.examples:
            parts.append(f"例题: {e.get('question', '')}")
            parts.append(f"解答: {e.get('solution', '')}")
            parts.append("")

        for m in self.misconceptions:
            parts.append(f"[常见错误] {m}")

        return "\n".join(parts)
