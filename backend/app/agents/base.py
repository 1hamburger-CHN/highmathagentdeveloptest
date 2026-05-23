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

    Many LLMs output raw LaTeX (e.g. \\lim, \\frac) inside JSON strings without
    escaping the backslash.  JSON requires \\\\, so we double single backslashes
    that start LaTeX command names (2+ letters) while leaving JSON's own escapes
    (\\n, \\r, \\t, etc.) alone.
    """
    return re.sub(r"(?<!\\)\\([a-zA-Z]{2,})", r"\\\\\1", text)


def safe_json_parse(text: str) -> Any:
    """Parse JSON with fallback repair for unescaped LaTeX backslashes."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_latex_json(text)
        return json.loads(repaired)


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
