import json

from app.agents.base import BaseAgent, safe_json_parse
from app.agents.state import TutorState

PROFILE_BUILDER_PROMPT = """你是"苏格拉底教练"系统中的学习画像构建专家。你的工作在后台静默进行——学生看不到你的消息，只有 Coach 会和学生对话。你只需要根据对话历史分析学生，更新画像数据。

## 评估维度
1. **知识掌握度**：学生对"极限与连续"相关概念的了解程度（0-1分）
2. **盲区图谱**：学生已经暴露的误解或知识缺口
3. **学习行为**：学生的回答风格（cautious谨慎/exploratory探索/impulsive冲动）和资源偏好（visual视觉/textual文本/interactive互动）

## 分析要点
- 从学生的用词判断基础水平（如能说出"ε-δ"说明有基础，只说"极限就是逼近"说明刚入门）
- 识别学生卡住或回避的概念
- 根据回答长度和质量推断学习风格
- next_message 不需要写给学生，留给 Coach 处理即可，但可以写一句分析摘要供内部参考

输出格式（JSON）：
{
  "knowledge_mastery": [{"concept_id": "...", "score": 0.0-1.0, "confidence": 0.0-1.0}],
  "blind_spots": [{"concept_id": "...", "error_type": "concept/calculation/symbol/logic/prerequisite"}],
  "behavior": {"response_style": "cautious/exploratory/impulsive", "resource_preference": "visual/textual/interactive"},
  "next_message": ""
}"""


class ProfileBuilderAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__("profile_builder", model_router)

    async def run(self, state: TutorState) -> dict:
        history = json.dumps(state.messages[-6:] if state.messages else [], ensure_ascii=False)
        existing = json.dumps(state.profile, ensure_ascii=False) if state.profile else "无"

        user_prompt = f"""当前对话历史：
{history}

已有画像数据：
{existing}

请根据对话进度，更新学习画像并生成下一条消息。返回JSON。"""

        response = await self.generate(PROFILE_BUILDER_PROMPT, user_prompt)
        try:
            result = safe_json_parse(response)
        except json.JSONDecodeError:
            result = {
                "knowledge_mastery": [],
                "blind_spots": [],
                "behavior": {"response_style": "cautious", "resource_preference": "visual"},
                "next_message": "你好！让我们先聊聊你的数学基础吧。你之前学过极限吗？",
            }

        return {
            "profile": {
                "knowledge_mastery": result.get("knowledge_mastery", []),
                "blind_spots": result.get("blind_spots", []),
                "behavior": result.get("behavior", {}),
            },
            "messages": [{"role": "assistant", "content": result.get("next_message", "")}],
        }
