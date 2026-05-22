from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.llm import ModelRouter


class BaseAgent:
    """Base agent with Spark LLM binding and common utilities."""

    def __init__(self, name: str, model_router: ModelRouter):
        self.name = name
        self.router = model_router

    @property
    def llm(self) -> BaseChatModel:
        return self.router.get_model(self.name)

    def build_messages(self, system: str, user: str) -> list:
        return [SystemMessage(content=system), HumanMessage(content=user)]

    async def run(self, state: dict) -> dict:
        raise NotImplementedError

    async def generate(self, system: str, user: str) -> str:
        """Simple generate helper: system prompt + user input -> response text."""
        messages = self.build_messages(system, user)
        result = await self.llm.ainvoke(messages)
        content = result.content
        if isinstance(content, list):
            return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        return str(content)

    async def generate_stream(self, system: str, user: str):
        """Stream response tokens from system + user prompt."""
        messages = self.build_messages(system, user)
        async for chunk in self.llm.astream(messages):
            yield chunk.content
