import json
from enum import Enum
from typing import Any, AsyncIterator, Iterator

import httpx
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.config import settings


class ModelTier(str, Enum):
    LITE = "spark_lite"
    PRO = "spark_pro"
    MAX = "spark_max"
    DEEPSEEK = "deepseek"


# Spark model name mapping: internal tier -> API model parameter
SPARK_MODEL_MAP = {
    ModelTier.LITE: "lite",
    ModelTier.PRO: "generalv3",
    ModelTier.MAX: "generalv3.5",
}

# DeepSeek model
DEEPSEEK_MODEL = "deepseek-chat"


class SparkChatModel(BaseChatModel):
    """LangChain-compatible chat model for 科大讯飞 Spark HTTP API."""

    api_password: str
    model: str  # lite / generalv3 / generalv3.5
    temperature: float = 0.5
    max_tokens: int = 4096
    timeout: int = 30

    @property
    def _llm_type(self) -> str:
        return f"spark-{self.model}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._build_payload(messages, stream=False)
        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(settings.spark_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        message = AIMessageChunk(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._build_payload(messages, stream=False)
        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(settings.spark_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        message = AIMessageChunk(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        payload = self._build_payload(messages, stream=True)
        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", settings.spark_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
                                if run_manager:
                                    run_manager.on_llm_new_token(delta, chunk=chunk)
                                yield chunk
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        payload = self._build_payload(messages, stream=True)
        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", settings.spark_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
                                if run_manager:
                                    await run_manager.on_llm_new_token(delta, chunk=chunk)
                                yield chunk
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    def _build_payload(self, messages: list[BaseMessage], stream: bool) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
            "messages": [
                {"role": self._map_role(m), "content": self._get_content(m)}
                for m in messages
            ],
        }

    @staticmethod
    def _map_role(msg: BaseMessage) -> str:
        if msg.type == "system":
            return "system"
        if msg.type == "ai" or msg.type == "assistant":
            return "assistant"
        return "user"

    @staticmethod
    def _get_content(msg: BaseMessage) -> str:
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content)


class DeepSeekChatModel(BaseChatModel):
    """LangChain-compatible chat model for DeepSeek API (OpenAI-compatible)."""

    api_key: str
    model: str = DEEPSEEK_MODEL
    temperature: float = 0.5
    max_tokens: int = 4096
    timeout: int = 30

    @property
    def _llm_type(self) -> str:
        return "deepseek-chat"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = self._build_payload(messages, stream=False)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(settings.deepseek_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessageChunk(content=content))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        payload = self._build_payload(messages, stream=False)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(settings.deepseek_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessageChunk(content=content))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._build_payload(messages, stream=True)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", settings.deepseek_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
                                if run_manager:
                                    run_manager.on_llm_new_token(delta, chunk=chunk)
                                yield chunk
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        payload = self._build_payload(messages, stream=True)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", settings.deepseek_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
                                if run_manager:
                                    await run_manager.on_llm_new_token(delta, chunk=chunk)
                                yield chunk
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    def _build_payload(self, messages: list[BaseMessage], stream: bool) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
            "messages": [
                {"role": SparkChatModel._map_role(m), "content": SparkChatModel._get_content(m)}
                for m in messages
            ],
        }


class ModelRouter:
    """Routes requests to Spark API tiers (Lite/Pro/Max) or DeepSeek fallback."""

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
        self._models: dict[ModelTier, BaseChatModel] = {}
        self._spark_available = bool(settings.spark_api_password)
        self._deepseek_available = bool(settings.deepseek_api_key)

    def get_model(self, agent_name: str) -> BaseChatModel:
        tier = self.AGENT_TIER.get(agent_name, ModelTier.LITE)
        if tier not in self._models:
            self._models[tier] = self._init_model(tier)
        return self._models[tier]

    def _init_model(self, tier: ModelTier) -> BaseChatModel:
        if tier == ModelTier.DEEPSEEK:
            return self._init_deepseek()
        return self._init_spark(tier)

    def _init_spark(self, tier: ModelTier) -> BaseChatModel:
        if not self._spark_available:
            if self._deepseek_available:
                return self._init_deepseek()
            return self._fallback_model(tier)

        return SparkChatModel(
            api_password=settings.spark_api_password,
            model=SPARK_MODEL_MAP[tier],
            temperature=0.5,
            max_tokens=4096,
            timeout=settings.api_timeout,
        )

    def _init_deepseek(self) -> BaseChatModel:
        if not self._deepseek_api_key:
            from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
            return GenericFakeChatModel(messages=iter(["DeepSeek API key not configured."]))

        return DeepSeekChatModel(
            api_key=settings.deepseek_api_key,
            temperature=0.5,
            max_tokens=4096,
            timeout=settings.api_timeout,
        )

    def _fallback_model(self, tier: ModelTier) -> BaseChatModel:
        from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
        return GenericFakeChatModel(messages=iter([f"[{tier.value}] API key not configured. Set SPARK_API_PASSWORD in .env"]))

    async def stream(self, agent_name: str, messages: list[dict]):
        """Stream LLM response tokens via SSE."""
        llm = self.get_model(agent_name)
        langchain_messages = [
            type("_Msg", (), {"type": m.get("role", "user"), "content": m.get("content", "")})
            for m in messages
        ]
        async for chunk in llm._astream(langchain_messages):
            yield chunk
