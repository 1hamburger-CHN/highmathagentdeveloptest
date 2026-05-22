from enum import Enum

from langchain_core.language_models import BaseLLM


class ModelTier(str, Enum):
    LITE = "spark_lite"
    PRO = "spark_pro"
    MAX = "spark_max"
    DEEPSEEK = "deepseek"


class ModelRouter:
    """Routes requests to Spark API tiers (Lite/Pro/Max) or DeepSeek fallback."""

    # Agent → default model tier mapping
    AGENT_TIER = {
        "orchestrator": ModelTier.LITE,
        "profile_builder": ModelTier.LITE,
        "diagnostician": ModelTier.MAX,
        "socratic_coach": ModelTier.MAX,
        "resource_generator": ModelTier.PRO,
        "assessor": ModelTier.MAX,
        "quality_gate": ModelTier.LITE,
    }

    def __init__(self):
        self._models: dict[ModelTier, BaseLLM] = {}

    def get_model(self, agent_name: str) -> BaseLLM:
        tier = self.AGENT_TIER.get(agent_name, ModelTier.LITE)
        if tier not in self._models:
            self._models[tier] = self._init_model(tier)
        return self._models[tier]

    def _init_model(self, tier: ModelTier) -> BaseLLM:
        # Placeholder: real Spark/DeepSeek LLM initialization
        from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
        return GenericFakeChatModel(messages=iter([f"[{tier.value}] placeholder response"]))

    async def stream(self, agent_name: str, messages: list[dict]):
        """Stream LLM response tokens."""
        llm = self.get_model(agent_name)
        async for chunk in llm.astream(messages):  # type: ignore
            yield chunk
