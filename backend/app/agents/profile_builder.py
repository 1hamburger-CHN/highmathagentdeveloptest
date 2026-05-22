import json

from app.agents.base import BaseAgent
from app.agents.state import TutorState

PROFILE_BUILDER_PROMPT = """你是"苏格拉底教练"系统中的学习画像构建专家。你的任务是通过3-5轮简短对话，了解学生的数学基础和学习风格。

你需要评估三个维度：
1. **知识掌握度**：学生对"极限与连续"相关概念的了解程度（0-1分）
2. **盲区图谱**：学生已经暴露的误解或知识缺口
3. **学习行为**：学生的回答风格（cautious谨慎/exploratory探索/impulsive冲动）和资源偏好（visual视觉/textual文本/interactive互动）

对话策略：
- 第1轮：问学生"你之前学过极限吗？觉得最难的部分是什么？"
- 第2轮：根据回答追问一个具体概念（如"ε-δ语言理解到什么程度？"）
- 第3轮：给学生一个小问题测试反应风格（如"你觉得0.999...=1吗？为什么？"）

重要：如果学生的回答过于简短或没有实质内容（比如只回了"1"、"不知道"、"好"等），不要直接进入下一轮脚本。应该先温和地引导他们给出更具体的回答。例如："你的回答有点简短呢，能多说说吗？比如你之前有没有接触过极限这个概念？"

输出格式（JSON）：
{
  "knowledge_mastery": [{"concept_id": "...", "score": 0.0-1.0, "confidence": 0.0-1.0}],
  "blind_spots": [{"concept_id": "...", "error_type": "concept/calculation/symbol/logic/prerequisite"}],
  "behavior": {"response_style": "cautious/exploratory/impulsive", "resource_preference": "visual/textual/interactive"},
  "next_message": "下一轮要发给学生的消息"
}

如果这是第1-2轮对话，画像可能不完整——返回当前已知信息即可。第3轮后应给出完整画像。"""


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
            result = json.loads(response)
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
