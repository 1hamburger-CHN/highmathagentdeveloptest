class SafetyPipeline:
    """Content safety: blocks non-math topics, filters prompt injection."""

    MATH_KEYWORDS = [
        "极限", "导数", "积分", "连续", "函数", "数列", "收敛", "发散",
        "无穷小", "无穷大", "ε", "δ", "lim", "sin", "cos", "tan",
        "limit", "derivative", "integral", "continuity", "function",
    ]

    PROMPT_INJECTION_PATTERNS = [
        "ignore", "forget", "system prompt", "previous instructions",
        "忽略", "忘记", "之前", "系统提示", "你是", "你现在",
        "do anything", "bypass", "jailbreak", "pretend",
    ]

    FALLBACK_RESPONSE = "让我们回到极限这个话题吧！你刚才提到的内容我不太确定如何回应，不如我们继续聊聊数学？"

    @classmethod
    def is_math_related(cls, text: str) -> bool:
        return any(kw.lower() in text.lower() for kw in cls.MATH_KEYWORDS)

    @classmethod
    def has_injection_pattern(cls, text: str) -> bool:
        """Detect common prompt injection attempts."""
        lower = text.lower()
        return any(pat.lower() in lower for pat in cls.PROMPT_INJECTION_PATTERNS)

    @classmethod
    def filter(cls, content: str) -> dict:
        """Returns {allowed: bool, content: str, reason: str}."""
        if cls.has_injection_pattern(content):
            return {"allowed": False, "content": cls.FALLBACK_RESPONSE, "reason": "injection"}
        if not cls.is_math_related(content):
            return {"allowed": False, "content": cls.FALLBACK_RESPONSE, "reason": "non_math"}
        return {"allowed": True, "content": content, "reason": ""}
