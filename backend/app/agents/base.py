from langchain_core.language_models import BaseLLM

from app.core.llm import ModelRouter


class BaseAgent:
    """Base agent with Spark LLM binding and common utilities."""

    def __init__(self, name: str, model_router: ModelRouter):
        self.name = name
        self.router = model_router

    @property
    def llm(self) -> BaseLLM:
        return self.router.get_model(self.name)

    def build_prompt(self, system: str, user: str) -> list[dict]:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    async def run(self, state: dict) -> dict:
        raise NotImplementedError
