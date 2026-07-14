"""Load OCR'd textbook text and split into chapter-aware chunks."""
import re
from pathlib import Path

from app.knowledge.textbook_schema import TEXTBOOK_CHAPTERS, TextbookChunk


CHAPTER_PATTERNS = [
    re.compile(r"第\s*([一二三四五六七八])\s*章"),
    re.compile(r"第\s*(\d+)\s*章"),
]

_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}


def _detect_chapter(text: str) -> tuple[int, str]:
    for pat in CHAPTER_PATTERNS:
        m = pat.search(text)
        if m:
            num_str = m.group(1)
            num = _CN_NUM.get(num_str, int(num_str) if num_str.isdigit() else 0)
            if num:
                return num, TEXTBOOK_CHAPTERS.get(num, f"第{num}章")
    return 0, ""


def _clean_ocr_text(text: str) -> str:
    text = re.sub(r"(?<=[一-龥])\s+(?=[一-龥])", "", text)
    text = text.replace("玻漏", "疏漏")
    return text


def load_textbook(text_path: str) -> list[TextbookChunk]:
    with open(text_path, encoding="utf-8") as f:
        raw_text = f.read()

    pages: dict[int, str] = {}
    current_page = 0
    current_lines: list[str] = []

    for line in raw_text.split("\n"):
        stripped = line.strip()
        m = re.match(r"\[Page\s+(\d+)\]", stripped)
        if m:
            if current_page > 0 and current_lines:
                pages[current_page] = "\n".join(current_lines)
            current_page = int(m.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_page > 0 and current_lines:
        pages[current_page] = "\n".join(current_lines)

    print(f"Parsed {len(pages)} pages with text content")

    chunks: list[TextbookChunk] = []
    current_chapter = 0
    current_chapter_title = ""
    CHUNK_SIZE = 512
    OVERLAP = 64

    for page_num in sorted(pages.keys()):
        page_text = _clean_ocr_text(pages[page_num])
        if len(page_text.strip()) < 20:
            continue

        ch_num, ch_title = _detect_chapter(page_text)
        if ch_num > 0:
            current_chapter = ch_num
            current_chapter_title = ch_title

        pos = 0
        chunk_idx = 0
        while pos < len(page_text):
            end = min(pos + CHUNK_SIZE, len(page_text))
            chunk_text = page_text[pos:end].strip()
            if len(chunk_text) >= 30:
                chunk_id = f"tb-ch{current_chapter}-p{page_num}-{chunk_idx}"
                chunks.append(TextbookChunk(
                    id=chunk_id,
                    chapter=current_chapter or 0,
                    chapter_title=current_chapter_title,
                    section="",
                    page=page_num,
                    content=chunk_text,
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1
            pos += CHUNK_SIZE - OVERLAP

    print(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks
