class SafetyPipeline:
    """Four-layer safety: greetings OK → block injection → catch low-quality → require math relevance."""

    PROMPT_INJECTION_PATTERNS = [
        "ignore", "forget", "system prompt", "previous instructions",
        "忽略", "忘记", "之前", "系统提示",
        "do anything", "bypass", "jailbreak", "pretend",
    ]

    MATH_KEYWORDS = [
        "极限", "导数", "积分", "连续", "函数", "数列", "收敛", "发散",
        "无穷小", "无穷大", "ε", "δ", "lim", "sin", "cos", "tan",
        "limit", "derivative", "integral", "continuity", "function",
        "数学", "定义", "证明", "定理", "计算", "概念",
        "例子", "题目", "怎么做", "解释", "说明",
    ]

    GREETING_PATTERNS = [
        "你好", "您好", "嗨", "哈喽", "哈啰", "嘿",
        "hello", "hi", "hey", "早上好", "下午好", "晚上好",
        "有人在吗", "在吗", "老师好", "教练好",
    ]

    # Single CJK chars that work as conversation one-liners
    CONVERSATION_CHARS = set("嗯哦好对是不没有啊吧吗呢嗨嘿")

    GREETING_RESPONSE = (
        "你好！很高兴见到你。我是你的数学辅导助手，擅长帮助你理解**极限与连续**相关的概念。\n\n"
        "你可以直接问数学问题，比如：\n"
        "- 「极限是什么？」\n"
        "- 「帮我证明：lim(x→0) sin(x)/x = 1」\n"
        "- 「连续和可导有什么区别？」\n\n"
        "如果有听不懂的地方，随时告诉我，我会用更简单的方式再讲一遍。放轻松，我们一起慢慢来。"
    )

    FALLBACK_INJECTION = "抱歉，我无法处理这个请求。让我们回到极限这个话题吧！"
    FALLBACK_LOW_QUALITY = "你的输入太短了，我没法理解你的意思。能再说详细一点吗？比如你可以告诉我你之前有没有学过极限，或者直接问一个具体的数学问题。"
    FALLBACK_NON_MATH = "我目前专注于帮你学习极限与连续。你刚才说的我不太确定如何回应——要不试试问我一个数学问题？比如「极限是什么」「怎么理解ε-δ定义」？"

    @classmethod
    def has_injection_pattern(cls, text: str) -> bool:
        lower = text.lower()
        return any(pat.lower() in lower for pat in cls.PROMPT_INJECTION_PATTERNS)

    @classmethod
    def is_greeting(cls, text: str) -> bool:
        """Detect greetings and small talk that deserve a warm response."""
        stripped = text.strip().lower()
        return any(greet.lower() in stripped for greet in cls.GREETING_PATTERNS)

    @classmethod
    def is_low_quality(cls, text: str) -> bool:
        """Catch extremely short / meaningless input like '1', '?', 'ab'."""
        stripped = text.strip()
        if len(stripped) > 2:
            return False
        if len(stripped) == 1 and stripped in cls.CONVERSATION_CHARS:
            return False
        if stripped.isdigit():
            return True
        if all(c in '.,;:?!@#$%^&*()+-=/\\|`~<>[]{} \t' for c in stripped):
            return True
        if len(stripped) == 2 and stripped.isascii() and not stripped.isalpha():
            return True
        return False

    @classmethod
    def is_math_related(cls, text: str) -> bool:
        return any(kw.lower() in text.lower() for kw in cls.MATH_KEYWORDS)

    @classmethod
    def filter(cls, content: str) -> dict:
        """Returns {allowed: bool, content: str, reason: str}."""
        if cls.has_injection_pattern(content):
            return {"allowed": False, "content": cls.FALLBACK_INJECTION, "reason": "injection"}
        if cls.is_greeting(content):
            return {"allowed": False, "content": cls.GREETING_RESPONSE, "reason": "greeting"}
        if cls.is_low_quality(content):
            return {"allowed": False, "content": cls.FALLBACK_LOW_QUALITY, "reason": "low_quality"}
        if not cls.is_math_related(content):
            return {"allowed": False, "content": cls.FALLBACK_NON_MATH, "reason": "non_math"}
        return {"allowed": True, "content": content, "reason": ""}
