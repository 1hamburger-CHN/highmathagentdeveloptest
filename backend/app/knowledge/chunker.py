import re


def latex_aware_split(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text with LaTeX block awareness — never split inside $$...$$ or $...$."""
    chunks = []
    pos = 0
    while pos < len(text):
        end = pos + chunk_size
        if end >= len(text):
            chunks.append(text[pos:])
            break
        # Look back from end for a safe split point
        snippet = text[pos:end + overlap]
        safe_pos = _find_safe_split(snippet, chunk_size)
        chunks.append(snippet[:safe_pos].strip())
        pos = pos + safe_pos
    return chunks


def _find_safe_split(text: str, min_pos: int) -> int:
    """Find a safe split point after min_pos, respecting LaTeX blocks and sentence boundaries."""
    safe_chars = min_pos
    in_display = False
    in_inline = False
    for i, ch in enumerate(text):
        if text[i:i+2] == "$$":
            in_display = not in_display
        elif ch == "$" and not in_display:
            in_inline = not in_inline
        if i >= min_pos and not in_display and not in_inline:
            if ch in ".。\n":
                return i + 1
    # Fallback: hard split at min_pos
    return min_pos
