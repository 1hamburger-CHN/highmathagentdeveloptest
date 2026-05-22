"""Spark API and DeepSeek LLM integration.

Provides SparkChatModel and DeepSeekChatModel with a common interface
(ainvoke + astream) without depending on langchain BaseChatModel to
avoid Python 3.13 compatibility issues with langchain_protocol.
"""
import json
from enum import Enum

import httpx

from app.config import settings


class ModelTier(str, Enum):
    LITE = "spark_lite"
    PRO = "spark_pro"
    MAX = "spark_max"
    DEEPSEEK = "deepseek"


SPARK_MODEL_MAP = {
    ModelTier.LITE: "generalv3.5",
    ModelTier.PRO: "generalv3.5",
    ModelTier.MAX: "4.0Ultra",
}

DEEPSEEK_MODEL = "deepseek-chat"


class SparkChatModel:
    """科大讯飞 Spark HTTP API chat model."""

    def __init__(self, api_password: str, model: str, temperature: float = 0.5,
                 max_tokens: int = 4096, timeout: int = 30):
        self.api_password = api_password
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def ainvoke(self, messages: list) -> "Response":
        """Non-streaming call. Returns Response with .content."""
        payload = self._build_payload(messages, stream=False)
        headers = {"Authorization": f"Bearer {self.api_password}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(settings.spark_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return Response(data["choices"][0]["message"]["content"])

    async def astream(self, messages: list):
        """Async generator yielding token strings."""
        payload = self._build_payload(messages, stream=True)
        headers = {"Authorization": f"Bearer {self.api_password}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", settings.spark_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                parse_errors = 0
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                            parse_errors = 0
                        except (json.JSONDecodeError, KeyError, IndexError):
                            parse_errors += 1
                            if parse_errors > 10:
                                yield "[流式传输中断]"
                                break

    def _build_payload(self, messages: list, stream: bool) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
            "messages": [{"role": self._role(m), "content": self._text(m)} for m in messages],
        }

    @staticmethod
    def _role(msg) -> str:
        if hasattr(msg, 'type'):
            t = msg.type
            if t in ("system", "ai", "assistant"):
                return "assistant" if t == "ai" else t
        if isinstance(msg, dict):
            r = msg.get("role", "user")
            return "assistant" if r == "ai" else r
        return "user"

    @staticmethod
    def _text(msg) -> str:
        if hasattr(msg, 'content'):
            c = msg.content
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
            return str(c)
        if isinstance(msg, dict):
            return str(msg.get("content", ""))
        return str(msg)


class DeepSeekChatModel:
    """DeepSeek API chat model (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = DEEPSEEK_MODEL, temperature: float = 0.5,
                 max_tokens: int = 4096, timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def ainvoke(self, messages: list) -> "Response":
        payload = self._build_payload(messages, stream=False)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(settings.deepseek_api_base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return Response(data["choices"][0]["message"]["content"])

    async def astream(self, messages: list):
        payload = self._build_payload(messages, stream=True)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", settings.deepseek_api_base, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                parse_errors = 0
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                            parse_errors = 0
                        except (json.JSONDecodeError, KeyError, IndexError):
                            parse_errors += 1
                            if parse_errors > 10:
                                yield "[流式传输中断]"
                                break

    def _build_payload(self, messages: list, stream: bool) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
            "messages": [{"role": SparkChatModel._role(m), "content": SparkChatModel._text(m)} for m in messages],
        }


class Response:
    """Simple response wrapper with .content attribute for compatibility."""
    def __init__(self, content: str):
        self.content = content


class ModelRouter:
    """Routes requests to Spark API tiers or DeepSeek fallback."""

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
        self._models: dict[ModelTier, SparkChatModel | DeepSeekChatModel] = {}
        self._spark_available = bool(settings.spark_api_password)
        self._deepseek_available = bool(settings.deepseek_api_key)

    def get_model(self, agent_name: str):
        tier = self.AGENT_TIER.get(agent_name, ModelTier.LITE)
        if tier not in self._models:
            self._models[tier] = self._init_model(tier)
        return self._models[tier]

    def _init_model(self, tier: ModelTier):
        if tier == ModelTier.DEEPSEEK:
            return self._init_deepseek()
        return self._init_spark(tier)

    def _init_spark(self, tier: ModelTier):
        if not self._spark_available:
            if self._deepseek_available:
                return self._init_deepseek()
            return _FallbackModel(f"系统初始化中，请稍后再试")

        max_tok = 8192 if tier == ModelTier.MAX else 4096
        return SparkChatModel(
            api_password=settings.spark_api_password,
            model=SPARK_MODEL_MAP[tier],
            temperature=0.5,
            max_tokens=max_tok,
            timeout=settings.api_timeout,
        )

    def _init_deepseek(self):
        if not settings.deepseek_api_key:
            return _FallbackModel("系统初始化中，请稍后再试")
        return DeepSeekChatModel(
            api_key=settings.deepseek_api_key,
            temperature=0.5,
            max_tokens=4096,
            timeout=settings.api_timeout,
        )


class _FallbackModel:
    """Returns a fixed message when no API key is configured."""
    def __init__(self, message: str):
        self.message = message

    async def ainvoke(self, messages=None):
        return Response(self.message)

    async def astream(self, messages=None):
        yield self.message[:50]
