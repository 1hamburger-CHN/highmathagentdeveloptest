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

## 课程概念ID表（必须使用这些ID，禁止编造）

| ID | 概念名 |
|----|--------|
| complex-1.1 | 复数定义与运算 |
| complex-1.2 | 几何表示与棣莫弗公式 |
| complex-1.3 | 复数的n次方根 |
| complex-2.1 | 复变函数的极限与连续 |
| complex-2.2 | C-R方程 |
| complex-2.3 | 调和函数 |
| complex-3.1 | 指数与对数函数 |
| complex-3.2 | 幂函数与三角函数 |
| complex-4.1 | 复积分定义与性质 |
| complex-4.2 | Cauchy-Goursat定理 |
| complex-4.3 | Cauchy积分与高阶导数 |
| complex-5.1 | 泰勒级数 |
| complex-5.2 | 洛朗级数 |
| complex-6.1 | 孤立奇点分类 |
| complex-6.2 | 留数与留数定理 |
| complex-6.3 | 留数在实积分中的应用 |
| complex-7.1 | 共形映射与Mobius变换 |

输出格式（JSON）：
{
  "blind_spots": [
    {
      "concept_id": "complex-2.2",
      "concept_name": "C-R方程",
      "error_type": "concept",
      "confidence": 0.85,
      "evidence": "学生混淆了偏导数的符号",
      "root_concept": "complex-2.1"
    }
  ],
  "mastered_concepts": ["complex-1.1"],
  "current_level": "学生当前最适合的追问层级: L1/L2/L3",
  "summary": "一句话诊断总结"
}

如果学生回答正确且无明显盲区，blind_spots可为空数组但mastered_concepts必须填写掌握的概念ID。"""


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

        # Determine current_concept: prefer blind spot → mastered → existing
        _diag_concept = state.current_concept
        if result.get("blind_spots"):
            _diag_concept = result["blind_spots"][0].get("concept_id", "") or _diag_concept
        elif result.get("mastered_concepts"):
            _diag_concept = result["mastered_concepts"][0] if result["mastered_concepts"] else _diag_concept

        return {
            "blind_spots": result.get("blind_spots", []),
            "current_concept": _diag_concept,
        }
