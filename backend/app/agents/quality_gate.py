import json

from app.agents.base import BaseAgent
from app.agents.state import TutorState
from app.services.math_service import MathService

QUALITY_GATE_PROMPT = """你是"苏格拉底教练"系统中的质量把关专家。你负责检查系统生成内容的质量和安全性。

## 检查项目

1. **数学正确性**：所有公式、定理、解答在数学上是否正确
2. **教学适当性**：内容的难度、深度是否适合当前学生
3. **内容安全**：内容是否聚焦于数学教学，不含与学习无关或不当信息
4. **格式完整性**：LaTeX语法是否正确，Markdown结构是否合理

输出格式（JSON）：
{
  "passed": true/false,
  "issues": [
    {
      "severity": "error/warning",
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "filtered_content": "如果内容有问题但可修复，返回修复后的内容；如果完全通过，返回原始内容"
}"""


class QualityGateAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__("quality_gate", model_router)

    async def run(self, state: TutorState) -> dict:
        # Collect content to check
        resources = json.dumps(state.generated_resources, ensure_ascii=False)
        last_messages = json.dumps(state.messages[-3:] if state.messages else [], ensure_ascii=False)

        # Quick SymPy check on any LaTeX in generated resources
        sympy_errors = []
        for r in state.generated_resources:
            content = r.get("content", "")
            if content:
                # Extract LaTeX expressions and verify
                latex_exprs = self._extract_latex(content)
                for expr in latex_exprs[:5]:  # Check first 5 expressions
                    result = MathService.verify_expression(expr)
                    if not result["valid"]:
                        sympy_errors.append({"expression": expr, "error": result["error"]})

        user_prompt = f"""待检查的生成资源：
{resources}

最近的对话消息：
{last_messages}

SymPy自动验证结果（如有错误需人工复核）：
{json.dumps(sympy_errors, ensure_ascii=False)}

请进行质量把关。返回JSON。"""

        response = await self.generate(QUALITY_GATE_PROMPT, user_prompt)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {"passed": True, "issues": [], "filtered_content": ""}

        passed = result.get("passed", True) and len(sympy_errors) == 0
        retries = state.quality_retries + (0 if passed else 1)

        return {
            "quality_retries": retries,
            "assessment_result": state.assessment_result,
        }

    @staticmethod
    def _extract_latex(text: str) -> list[str]:
        """Extract LaTeX math expressions from text."""
        import re
        exprs = []
        for match in re.finditer(r'\$\$?(.+?)\$\$?', text):
            exprs.append(match.group(1))
        return exprs
