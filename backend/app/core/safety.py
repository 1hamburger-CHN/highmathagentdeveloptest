import random


class SafetyPipeline:
    """Four-layer safety: greetings OK → block injection → catch low-quality → require math relevance."""

    PROMPT_INJECTION_PATTERNS = [
        "ignore", "forget", "system prompt", "previous instructions",
        "忽略", "忘记", "之前", "系统提示",
        "do anything", "bypass", "jailbreak", "pretend",
    ]

    MATH_KEYWORDS = [
        "复数", "复变", "解析", "留数", "积分", "函数", "级数", "收敛",
        "奇点", "极点", "围道", "C-R", "Cauchy", "洛朗", "泰勒",
        "共形", "映射", "调和", "共轭", "模", "辐角", "棣莫弗",
        "residue", "analytic", "complex", "laurent",
        "数学", "定义", "证明", "定理", "计算", "概念",
        "例子", "题目", "怎么做", "解释", "说明",
        "等于", "等于几", "等于多少", "怎么算", "答案是", "是多少",
        "题", "练习", "出题", "试卷",
        "生成", "帮我", "给我", "做一下", "讲一下",
        # General math terms across domains
        "不等式", "等式", "方程", "公式", "定律", "引理", "猜想",
        "推论", "法则", "恒等式", "渐近", "展开", "变换", "反演",
        "概率", "统计", "矩阵", "向量", "几何", "代数", "拓扑",
        "数论", "微分", "导数", "极限", "集合", "测度", "环",
        "域", "群", "格", "模形式", "表示", "同调", "同伦",
        "微积分", "线性代数", "概率论", "数理统计", "泛函",
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
            "{hello}很高兴见到你！我是你的数学辅导助手，专门陪你攻克复变函数这块硬骨头！\n\n"
            "你可以随便问我，比如：\n"
            "- 「解析函数是什么？能帮我通俗地讲讲吗？」\n"
            "- 「C-R方程我完全看不懂，救命！」\n"
            "- 「留数定理到底怎么用？」\n\n"
            "有听不懂的地方随时打断我，让我换个讲法。放轻松，慢慢来！"
        ),
        (
            "{hello}欢迎来到数学世界！我是你的专属教练，主攻复变函数。\n\n"
            "不知道从哪开始？试试问：\n"
            "- 「Cauchy积分公式是什么意思？」\n"
            "- 「能不能举个复函数不可导的例子？」\n"
            "- 「C-R方程是什么鬼？」\n\n"
            "任何问题都可以，没有蠢问题！一起加油吧！"
        ),
        (
            "{hello}总算等到你了！我是你的数学陪练，专注复变函数这块～\n\n"
            "怎么玩都行：\n"
            "- 直接甩一个概念让我讲（比如『解析函数』）\n"
            "- 问个题目让我带你一起证\n"
            "- 或者说「我啥都不懂」让我从头带你\n\n"
            "我这儿不急不赶，随时等你开口！"
        ),
    ]

    LOW_QUALITY_RESPONSES = [
        "嗨！你发的消息有点短，我没太明白你的意思～ 不急，慢慢说，比如告诉我你之前有没有学过复数？",
        "嗯？我没太看懂你发的～ 要不试试多说一点？比如问『解析函数是啥』或者『留数定理怎么用』？",
        "你好呀！消息有点短哦，我没法理解你想说什么。试试看直接问个数学问题？",
        "哈喽～ 你发的这条有点短，我看不太懂。能再详细说说吗？没关系，随便聊！",
    ]

    NON_MATH_RESPONSES = [
        "嗨！我目前主要帮大家学习复变函数。要不试试问我一个数学问题？比如「复数是什么」「解析函数怎么判断」？",
        "你好呀！我这边专注数学辅导，尤其是复变函数。有什么相关的题或者概念想聊聊吗？",
        "哈喽～ 你说的这个我可能接不住，但如果你有复变函数相关的疑问，我很乐意帮忙！比如问个『C-R方程怎么验证』？",
        "嘿！我主要擅长的是复变函数这块的数学。换个相关问题试试？比如「帮我看看这道复积分题」～",
    ]

    INJECTION_RESPONSES = [
        "嗨！这个请求我没法处理哦。咱们还是回到复变函数这个话题上吧！",
        "你好呀！那个方向我不太能聊～ 不如试试数学？复数、解析、留数，随便问！",
    ]

    @classmethod
    def _pick(cls, pool):
        """Pick a random response from a pool. Supports {hello} placeholder."""
        text = random.choice(pool)
        if "{hello}" in text:
            text = text.replace("{hello}", random.choice(cls.HELLOS))
        return text

    RESOURCE_KEYWORDS = [
        "生成", "思维导图", "脑图", "导图", "知识图谱",
        "讲义", "课件", "教程", "笔记", "总结", "归纳",
        "练习题", "习题", "出题", "试卷", "题目",
        "阅读材料", "拓展", "资料", "帮我", "给我",
        "介绍", "概述", "概览", "入门",
    ]

    # Common vague-but-valid math conversation responses
    CONVERSATIONAL_RESPONSES = [
        "不知道", "不太懂", "不明白", "不会", "不懂",
        "还行", "差不多", "可能", "大概", "好像",
        "是的", "对的", "没错", "不对",
        "可以", "好的", "行", "没问题",
        "再讲一遍", "没听懂", "再说一次",
        "学过", "没学过", "没有", "了解", "不了解",
        "有点", "学过一点", "有点基础", "没基础",
    ]

    @classmethod
    def is_conversational(cls, text: str) -> bool:
        """Detect valid conversation continuations even if not math-related."""
        stripped = text.strip()
        if len(stripped) == 1 and stripped in cls.CONVERSATION_CHARS:
            return True
        return any(resp in stripped for resp in cls.CONVERSATIONAL_RESPONSES)

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
    def _assistant_asked_question(cls, assistant_msg: str) -> bool:
        """Check if the assistant's last message contains a question or prompt to the user."""
        if not assistant_msg:
            return False
        # Question marks
        if "？" in assistant_msg or "?" in assistant_msg:
            return True
        # Chinese question patterns
        question_patterns = [
            "吗", "呢", "试试", "你觉得", "能不能", "会不会",
            "再想想", "还有呢", "比如呢", "举个例子", "说说看",
            "你怎么理解", "你觉得呢", "怎么看",
        ]
        return any(p in assistant_msg for p in question_patterns)

    @classmethod
    def _is_answering_question(cls, user_msg: str, assistant_msg: str) -> bool:
        """Check if user's message is plausibly answering the assistant's question."""
        if not cls._assistant_asked_question(assistant_msg):
            return False
        # Short responses are almost always answers to questions
        if len(user_msg.strip()) <= 30:
            return True
        # The user is engaging with the topic — contains keywords from the question
        return True  # any non-trivial reply to a question counts

    @classmethod
    def filter(cls, content: str, assistant_msg: str = "") -> dict:
        """Returns {allowed: bool, content: str, reason: str}."""
        if cls.has_injection_pattern(content):
            return {"allowed": False, "content": cls._pick(cls.INJECTION_RESPONSES), "reason": "injection"}
        if cls.is_greeting(content):
            return {"allowed": False, "content": cls._pick(cls.GREETING_RESPONSES), "reason": "greeting"}
        if cls.is_low_quality(content):
            return {"allowed": False, "content": cls._pick(cls.LOW_QUALITY_RESPONSES), "reason": "low_quality"}
        # Allow conversational responses (single chars like 好/啊, vague answers like 不知道)
        if cls.is_conversational(content):
            return {"allowed": True, "content": content, "reason": "conversational"}
        # Resource generation requests (思维导图, 练习题, etc.) — always allowed
        if any(kw in content for kw in cls.RESOURCE_KEYWORDS):
            return {"allowed": True, "content": content, "reason": "resource_request"}
        # User is answering a question the assistant just asked — allow, don't redirect
        if cls._is_answering_question(content, assistant_msg):
            return {"allowed": True, "content": content, "reason": "answering_question"}
        if not cls.is_math_related(content):
            return {"allowed": False, "content": cls._pick(cls.NON_MATH_RESPONSES), "reason": "non_math"}
        return {"allowed": True, "content": content, "reason": ""}
