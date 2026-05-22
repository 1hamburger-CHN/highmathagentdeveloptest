class SafetyPipeline:
    """Content safety: blocks non-math topics, filters sensitive content."""

    MATH_KEYWORDS = [
        "极限", "导数", "积分", "连续", "函数", "数列", "收敛", "发散",
        "无穷小", "无穷大", "ε", "δ", "lim", "sin", "cos", "tan",
        "limit", "derivative", "integral", "continuity", "function",
    ]

    FALLBACK_RESPONSE = "让我们回到极限这个话题吧！你刚才提到的内容我不太确定如何回应，不如我们继续聊聊数学？"

    @classmethod
    def is_math_related(cls, text: str) -> bool:
        return any(kw in text for kw in cls.MATH_KEYWORDS)

    @classmethod
    def filter(cls, content: str) -> dict:
        """Returns {allowed: bool, content: str, reason: str}."""
        if not cls.is_math_related(content):
            return {"allowed": False, "content": cls.FALLBACK_RESPONSE, "reason": "non_math"}
        # TODO: add sensitive word filtering
        return {"allowed": True, "content": content, "reason": ""}
