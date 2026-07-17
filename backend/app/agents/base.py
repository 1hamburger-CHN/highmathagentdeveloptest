import json
import logging
import re
import time
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import ModelRouter

logger = logging.getLogger("tutor")


def repair_latex_json(text: str) -> str:
    """Fix unescaped LaTeX backslashes inside JSON strings.

    Many LLMs output raw LaTeX (e.g. \\lim, \\frac, \\bar) inside JSON strings
    without escaping the backslash.  JSON requires \\\\, so we double single
    backslashes that start LaTeX command names while leaving JSON's own escapes
    (\\n, \\r, \\t, etc.) alone.

    Special handling for \\b: \\b is valid JSON (backspace U+0008), but when
    followed by letters (\\bar, \\beta, \\binom) it's actually LaTeX.
    We pre-escape these BEFORE json.loads corrupts them.
    """
    # First: fix \\b followed by a letter — must be LaTeX, not JSON backspace
    text = re.sub(r"(?<!\\)\\b(?=[a-zA-Z])", r"\\\\b", text)
    # Then: fix all other LaTeX commands (2+ letters after backslash)
    text = re.sub(r"(?<!\\)\\([a-zA-Z]{2,})", r"\\\\\1", text)
    return text


def _extract_json_braces(text: str) -> str:
    """Extract the outermost JSON object/array from text that may have surrounding prose."""
    # Find first { or [ and last } or ]
    start = None
    end = None
    for i, ch in enumerate(text):
        if ch in ("{", "[") and start is None:
            start = i
        if ch in ("}", "]"):
            end = i
    if start is not None and end is not None and start < end:
        return text[start : end + 1]
    return text


def _close_truncated_json(text: str) -> str:
    """Attempt to close a truncated JSON string by adding missing terminators."""
    # Count unclosed braces/brackets and close them
    stack: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()
    if not stack:
        return text
    # Close from innermost to outermost
    closing = "".join(reversed(stack))
    return text + closing


def safe_json_parse(text: str) -> Any:
    """Parse JSON with cascading fallback for common LLM output issues."""
    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Repair unescaped LaTeX backslashes
    try:
        repaired = repair_latex_json(text)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 3. Extract JSON from surrounding prose, then try again
    extracted = _extract_json_braces(text)
    if extracted != text:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            repaired = repair_latex_json(extracted)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    # 4. Try to close truncated JSON + LaTeX repair
    closed = _close_truncated_json(extracted)
    if closed != extracted:
        try:
            repaired = repair_latex_json(closed)
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(
        f"All parse strategies failed (raw {len(text)} chars)",
        text[:200],
        0,
    )


class BaseAgent:
    """Base agent with Spark LLM binding and common utilities."""

    def __init__(self, name: str, model_router: ModelRouter):
        self.name = name
        self.router = model_router

    @property
    def llm(self) -> Any:
        return self.router.get_model(self.name)

    def build_messages(self, system: str, user: str) -> list:
        return [SystemMessage(content=system), HumanMessage(content=user)]

    async def run(self, state: dict) -> dict:
        raise NotImplementedError

    async def generate(self, system: str, user: str) -> str:
        """Simple generate helper: system prompt + user input -> response text."""
        start = time.time()
        messages = self.build_messages(system, user)
        result = await self.llm.ainvoke(messages)
        elapsed = time.time() - start
        content = result.content
        if isinstance(content, list):
            content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        content = str(content)
        logger.info(f"Agent[{self.name}] generated {len(content)} chars in {elapsed:.1f}s")
        return content

    async def generate_stream(self, system: str, user: str):
        """Stream response tokens from system + user prompt."""
        messages = self.build_messages(system, user)
        token_count = 0
        async for token in self.llm.astream(messages):
            token_count += 1
            yield token
        logger.info(f"Agent[{self.name}] streamed {token_count} tokens")
