"""Textbook chunk schema for the HIT Complex Analysis textbook.

Each chunk represents a section of the OCR'd textbook with chapter/page metadata.
"""
from dataclasses import dataclass, field


@dataclass
class TextbookChunk:
    """A searchable chunk from the OCR'd textbook."""
    id: str                    # e.g. "tb-ch1-sec2-p12-0"
    chapter: int               # 1-8
    chapter_title: str         # e.g. "复数与复平面"
    section: str               # e.g. "1.2 复数的几何表示" or "" if unknown
    page: int                  # page number in the PDF
    content: str               # the actual text content
    chunk_index: int = 0       # index of this chunk within the page

    def to_searchable_text(self) -> str:
        """Render chunk as searchable text for embedding."""
        header = f"第{self.chapter}章 {self.chapter_title}"
        if self.section:
            header += f" — {self.section}"
        return f"{header}\n\n{self.content}"

    def to_metadata(self) -> dict:
        return {
            "source": "textbook",
            "chapter": self.chapter,
            "chapter_title": self.chapter_title,
            "section": self.section,
            "page": self.page,
            "chunk_index": self.chunk_index,
        }


# Textbook chapter mapping (from the preface OCR)
TEXTBOOK_CHAPTERS = {
    1: "复数与复平面",
    2: "解析函数",
    3: "复变函数的积分",
    4: "级数",
    5: "留数",
    6: "共形映射",
    7: "傅里叶变换",
    8: "拉普拉斯变换",
}

# Map textbook chapters to existing curriculum node IDs
CHAPTER_TO_NODE_MAP = {
    1: ["complex-1.1", "complex-1.2", "complex-1.3"],
    2: ["complex-2.1", "complex-2.2", "complex-2.3"],
    3: ["complex-4.1", "complex-4.2", "complex-4.3"],
    4: ["complex-5.1", "complex-5.2"],
    5: ["complex-6.1", "complex-6.2", "complex-6.3"],
    6: ["complex-7.1"],
    7: [],  # New: Fourier transform (not yet in curriculum)
    8: [],  # New: Laplace transform (not yet in curriculum)
}
