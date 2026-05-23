import json

from app.agents.base import BaseAgent, safe_json_parse
from app.agents.state import TutorState

DIAGNOSTICIAN_PROMPT = """你是"苏格拉底教练"系统中的学习诊断专家。你的任务是通过对话分析，精准定位学生的知识盲区。

诊断方法：
1. **概念图谱分析**：根据学生的回答，判断他们对"极限与连续"知识树中各个节点的掌握程度
2. **错误模式识别**：将学生的错误归类为：
   - concept（概念理解错误）
   - calculation（计算错误）
   - symbol（符号使用错误）
   - logic（逻辑推理错误）
   - prerequisite（前置知识缺失）
3. **根因追溯**：当一个概念出错时，判断是当前概念没理解还是前置概念有漏洞

参考知识树结构（极限与连续）：
- 数列极限 (ε-N定义 → 收敛性质 → 四则运算 → 夹逼准则 → 单调有界)
- 函数极限 (ε-δ定义 → 左右极限 → 无穷小 → 无穷大 → 无穷小比较 → 运算法则)
- 两个重要极限 (sin x/x → (1+1/x)^x=e)
- 等价无穷小替换 (常用替换公式 → 加减法陷阱 → 泰勒展开基础)
- 连续性 (定义 → 间断点分类)
- 进阶 (洛必达法则 → 渐近线 → 极限存在性判别)

输出格式（JSON）：
{
  "blind_spots": [
    {
      "concept_id": "limit-1.3.3",
      "concept_name": "等价无穷小替换",
      "error_type": "concept",
      "confidence": 0.85,
      "evidence": "学生在加减法中也使用了等价无穷小替换",
      "root_concept": "limit-1.3.4"
    }
  ],
  "mastered_concepts": ["limit-1.1.1"],
  "current_level": "学生当前最适合的追问层级: L1/L2/L3",
  "summary": "一句话诊断总结"
}

如果学生回答正确且无明显盲区，blind_spots可为空数组。"""


class DiagnosticianAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__("diagnostician", model_router)

    async def run(self, state: TutorState) -> dict:
        history = json.dumps(state.messages[-10:] if state.messages else [], ensure_ascii=False)
        profile = json.dumps(state.profile, ensure_ascii=False) if state.profile else "无"

        user_prompt = f"""对话历史：
{history}

学生画像：
{profile}

当前关注概念：{state.current_concept or "未指定"}

请诊断学生的知识盲区。返回JSON。"""

        response = await self.generate(DIAGNOSTICIAN_PROMPT, user_prompt)
        try:
            result = safe_json_parse(response)
        except json.JSONDecodeError:
            result = {"blind_spots": [], "mastered_concepts": [], "current_level": "L1", "summary": "无法完成诊断"}

        return {
            "blind_spots": result.get("blind_spots", []),
            "current_concept": (
                result["blind_spots"][0]["concept_id"]
                if result.get("blind_spots")
                else state.current_concept
            ),
        }
