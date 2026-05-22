import random


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
        "等于", "等于几", "等于多少", "怎么算", "答案是", "是多少",
    ]

    GREETING_PATTERNS = [
        "你好", "您好", "嗨", "哈喽", "哈啰", "嘿",
        "hello", "hi", "hey", "早上好", "下午好", "晚上好",
        "有人在吗", "在吗", "老师好", "教练好",
    ]

    # Single CJK chars that work as conversation one-liners
    CONVERSATION_CHARS = set("嗯哦好对是不没有啊吧吗呢嗨嘿")

    # --- Varied greeting pools ---

    HELLOS = [
        "嗨！", "你好呀！", "哈喽～", "嘿，你好！",
        "你好！欢迎欢迎！", "嗨嗨嗨！",
    ]

    GREETING_RESPONSES = [
        (
            "{hello}很高兴见到你！我是你的数学辅导助手，专门陪你攻克极限与连续这块硬骨头！\n\n"
            "你可以随便问我，比如：\n"
            "- 「极限是什么？能帮我通俗地讲讲吗？」\n"
            "- 「ε-δ定义我完全看不懂，救命！」\n"
            "- 「连续和可导到底有什么区别？」\n\n"
            "有听不懂的地方随时打断我，让我换个讲法。放轻松，慢慢来！"
        ),
        (
            "{hello}欢迎来到数学世界！我是你的专属教练，主攻极限与连续。\n\n"
            "不知道从哪开始？试试问：\n"
            "- 「极限的ε-δ定义是什么意思？」\n"
            "- 「能不能举个极限不存在的例子？」\n"
            "- 「夹逼定理是什么鬼？」\n\n"
            "任何问题都可以，没有蠢问题！一起加油吧！"
        ),
        (
            "{hello}总算等到你了！我是你的数学陪练，专注极限与连续这块～\n\n"
            "怎么玩都行：\n"
            "- 直接甩一个概念让我讲（比如『极限』）\n"
            "- 问个题目让我带你一起证\n"
            "- 或者说「我啥都不懂」让我从头带你\n\n"
            "我这儿不急不赶，随时等你开口！"
        ),
    ]

    LOW_QUALITY_RESPONSES = [
        "嗨！你发的消息有点短，我没太明白你的意思～ 不急，慢慢说，比如告诉我你之前有没有学过极限？",
        "嗯？我没太看懂你发的～ 要不试试多说一点？比如问『极限是啥』或者『怎么证明极限存在』？",
        "你好呀！消息有点短哦，我没法理解你想说什么。试试看直接问个数学问题？",
        "哈喽～ 你发的这条有点短，我看不太懂。能再详细说说吗？没关系，随便聊！",
    ]

    NON_MATH_RESPONSES = [
        "嗨！我目前主要帮大家学习极限与连续。要不试试问我一个数学问题？比如「极限是什么」「ε-δ怎么理解」？",
        "你好呀！我这边专注数学辅导，尤其是极限和连续。有什么相关的题或者概念想聊聊吗？",
        "哈喽～ 你说的这个我可能接不住，但如果你有极限相关的疑问，我很乐意帮忙！比如问个『连续和可导有什么区别』？",
        "嘿！我主要擅长的是极限与连续这块的数学。换个相关问题试试？比如「帮我看看这道极限题」～",
    ]

    INJECTION_RESPONSES = [
        "嗨！这个请求我没法处理哦。咱们还是回到极限这个话题上吧！",
        "你好呀！那个方向我不太能聊～ 不如试试数学？极限、连续，随便问！",
    ]

    @classmethod
    def _pick(cls, pool):
        """Pick a random response from a pool. Supports {hello} placeholder."""
        text = random.choice(pool)
        if "{hello}" in text:
            text = text.replace("{hello}", random.choice(cls.HELLOS))
        return text

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
        """Catch extremely short / meaningless input."""
        stripped = text.strip()
        if len(stripped) > 2:
            return False
        if len(stripped) == 1 and stripped in cls.CONVERSATION_CHARS:
            return False
        # Digits and negative numbers are valid math answers (e.g. "5", "-3")
        if stripped.lstrip("-").isdigit():
            return False
        # Pure punctuation / gibberish
        if all(c in '.,;:?!@#$%^&*()+-=/\\|`~<>[]{} \t' for c in stripped):
            return True
        if len(stripped) == 2 and stripped.isascii() and not stripped.isalpha():
            return True
        return False

    @classmethod
    def is_math_related(cls, text: str) -> bool:
        if any(kw.lower() in text.lower() for kw in cls.MATH_KEYWORDS):
            return True
        stripped = text.strip()
        has_digit = any(c.isdigit() for c in stripped)
        has_op = any(c in "+-*/=<>" for c in stripped)
        if has_digit and has_op:
            return True
        # Pure number (e.g. "5", "-3", "3.14") — valid math answer
        if has_digit:
            return True
        return False

    @classmethod
    def filter(cls, content: str) -> dict:
        """Returns {allowed: bool, content: str, reason: str}."""
        if cls.has_injection_pattern(content):
            return {"allowed": False, "content": cls._pick(cls.INJECTION_RESPONSES), "reason": "injection"}
        if cls.is_greeting(content):
            return {"allowed": False, "content": cls._pick(cls.GREETING_RESPONSES), "reason": "greeting"}
        if cls.is_low_quality(content):
            return {"allowed": False, "content": cls._pick(cls.LOW_QUALITY_RESPONSES), "reason": "low_quality"}
        if not cls.is_math_related(content):
            return {"allowed": False, "content": cls._pick(cls.NON_MATH_RESPONSES), "reason": "non_math"}
        return {"allowed": True, "content": content, "reason": ""}
