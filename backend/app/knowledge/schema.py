from dataclasses import dataclass, field


@dataclass
class KnowledgeNode:
    id: str
    title: str
    definition: str  # LaTeX
    theorems: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)  # [{question, solution}]
    common_errors: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)

    def to_chunk_text(self) -> str:
        parts = [f"# {self.title}", self.definition]
        for t in self.theorems:
            parts.append(t)
        for e in self.examples:
            parts.append(f"Q: {e['question']}\nA: {e['solution']}")
        for err in self.common_errors:
            parts.append(f"[常见错误] {err}")
        return "\n\n".join(parts)
