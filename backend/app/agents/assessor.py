import json

from app.agents.base import BaseAgent, safe_json_parse
from app.agents.state import TutorState

ASSESSOR_PROMPT = """你是"苏格拉底教练"系统中的评估专家。当学生完成一轮苏格拉底追问后，你负责评估他们的表现并识别错误模式。

## 评估维度

1. **正确性**：学生的回答在数学上是否正确
2. **深度**：理解是停留在表面还是触及本质
3. **错误模式**：将错误归类为：
   - concept（概念错误）— 根本性地理解错了某个数学概念
   - calculation（计算错误）— 概念对但算错了
   - symbol（符号错误）— 符号使用不准确
   - logic（逻辑错误）— 推理过程有漏洞
   - prerequisite（前置缺失）— 需要用到还没掌握的概念

## 学习路径建议

根据评估结果，建议下一步：
- 通过：进入下一个概念的学习
- 轻度问题：再追问1-2轮巩固
- 中度问题：推荐特定资源进行补救
- 严重问题：回溯到前置概念重新学习

输出格式（JSON）：
{
  "correct": true/false,
  "score": 0.0-1.0,
  "error_patterns": [
    {
      "type": "concept/calculation/symbol/logic/prerequisite",
      "description": "具体错误描述",
      "related_concept": "limit-1.3.3"
    }
  ],
  "recommendation": "pass/extra_coaching/remediate/backtrack",
  "summary": "评估总结"
}"""


class AssessorAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__("assessor", model_router)

    async def run(self, state: TutorState) -> dict:
        history = json.dumps(state.messages[-8:] if state.messages else [], ensure_ascii=False)

        user_prompt = f"""对话历史：
{history}

当前概念：{state.current_concept}
当前追问层级：L{state.coach_level}

请评估学生的表现。返回JSON。"""

        response = await self.generate(ASSESSOR_PROMPT, user_prompt)
        try:
            result = safe_json_parse(response)
        except json.JSONDecodeError:
            result = {"correct": True, "score": 0.5, "error_patterns": [], "recommendation": "pass", "summary": ""}

        return {"assessment_result": result}
