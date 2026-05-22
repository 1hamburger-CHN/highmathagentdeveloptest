import json

from app.agents.base import BaseAgent
from app.agents.state import TutorState

PROFILE_BUILDER_PROMPT = """你是"苏格拉底教练"系统中的学习画像构建专家。你的任务是通过3-5轮简短对话，了解学生的数学基础和学习风格。

## 对话风格
- 温暖、耐心，像一位友善的数学导师在和学生聊天
- 每次只说一件事，不要一次性抛出太多问题
- 如果学生回答很短或敷衍（"1""不知道""还行"），先鼓励再说："没关系，慢慢来。要不先说说你之前有没有接触过极限这个概念？"
- 根据学生状态调整节奏：紧张就放慢，有兴趣就深入一点

## 评估维度
1. **知识掌握度**：学生对"极限与连续"相关概念的了解程度（0-1分）
2. **盲区图谱**：学生已经暴露的误解或知识缺口
3. **学习行为**：学生的回答风格（cautious谨慎/exploratory探索/impulsive冲动）和资源偏好（visual视觉/textual文本/interactive互动）

## 对话策略
- 第1轮：友好打招呼，了解学生基础。如"你之前学过极限吗？觉得最难的部分是什么？"
- 第2轮：根据回答追问具体概念
- 第3轮：用小问题测试反应风格（如"你觉得0.999...=1吗？为什么？"）

## 特别注意
如果学生的回答过于简短或没有实质内容（如"1""不知道""好""嗯"），不要直接进入下一轮脚本。先温和引导他们给出更具体的回答。
例如："你的回答有点简短呢，能多说说吗？比如你之前有没有接触过极限这个概念？"

输出格式（JSON）：
{
  "knowledge_mastery": [{"concept_id": "...", "score": 0.0-1.0, "confidence": 0.0-1.0}],
  "blind_spots": [{"concept_id": "...", "error_type": "concept/calculation/symbol/logic/prerequisite"}],
  "behavior": {"response_style": "cautious/exploratory/impulsive", "resource_preference": "visual/textual/interactive"},
  "next_message": "下一轮要发给学生的消息"
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
