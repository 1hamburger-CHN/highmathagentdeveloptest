import json

from app.agents.base import BaseAgent, safe_json_parse
from app.agents.state import TutorState

DIAGNOSTICIAN_PROMPT = """你是"苏格拉底教练"系统中的学习诊断专家。你的任务是通过对话分析，精准定位学生的知识盲区。

诊断方法：
1. **概念图谱分析**：根据学生的回答，判断他们对"复变函数"知识树中各个节点的掌握程度
2. **错误模式识别**：将学生的错误归类为：
   - concept（概念理解错误）
   - calculation（计算错误）
   - symbol（符号使用错误）
   - logic（逻辑推理错误）
   - prerequisite（前置知识缺失）
3. **根因追溯**：当一个概念出错时，判断是当前概念没理解还是前置概念有漏洞

参考知识树结构（复变函数）：
- 复数与复平面 (复数运算 → 几何表示 → n次方根)
- 解析函数 (复极限 → C-R方程 → 调和函数)
- 初等复函数 (指数与对数 → 三角与幂函数)
- 复积分 (积分定义 → Cauchy-Goursat定理 → Cauchy积分公式)
- 级数展开 (泰勒级数 → 洛朗级数)
- 留数定理 (奇点分类 → 留数计算 → 实积分应用)
- 共形映射 (Möbius变换 → 保角性)

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

        kb_context = getattr(state, "_kb_context", {}) or {}
        kb_text = ""
        if kb_context:
            textbook = kb_context.get("textbook", [])
            handouts = kb_context.get("handouts", [])
            if textbook:
                kb_text += "\n## 教材参考（哈工大《复变函数与积分变换》）\n" + "\n---\n".join(textbook)
            if handouts:
                kb_text += "\n## 讲义参考（哈工大复变课堂讲义）\n" + "\n---\n".join(handouts)
            if kb_text:
                kb_text = "\n请确保你的诊断基于以上教材定义，保持数学严谨性。\n" + kb_text

        user_prompt = f"""对话历史：
{history}

学生画像：
{profile}

当前关注概念：{state.current_concept or "未指定"}
{kb_text}

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
