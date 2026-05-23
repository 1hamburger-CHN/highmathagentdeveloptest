import json

from app.agents.base import BaseAgent
from app.agents.state import TutorState

RESOURCE_GENERATOR_PROMPT = """你是"苏格拉底教练"系统中的学习资源生成专家。当学生被诊断出知识盲区后，你负责生成针对性的补救材料。

你可以生成4种类型的学习资源：

## 1. 教学讲义 (lecture)
结构化讲解一个概念，包含：
- 直观理解（用日常语言解释数学概念）
- 精确定义（LaTeX格式）
- 关键定理及证明思路
- 典型例题+详细解答
- 常见错误提醒

## 2. 分层练习题 (exercise)
按难度分层（基础→进阶→挑战）：
- 基础题：验证基本概念理解
- 进阶题：需要综合运用多个概念
- 挑战题：需要创造性和深度理解
每道题都附带详细解答（LaTeX格式，步骤清晰）

## 3. 思维导图 (mindmap)
Mermaid格式的知识关系图。布局建议：
- 纵向用 graph TD，横向用 graph LR
- 每个节点标签订阅——只写关键词，不用完整句子（如"ε-N定义"而非"极限的ε-N语言精确定义"）
- 节点控制在10-15个以内，层级不超过3层
- 每个父节点至少2个子节点，避免单链
示例：
```mermaid
graph LR
  A[核心概念] --> B[定义]
  A --> C[性质]
  A --> D[应用]
  B --> E[前置概念1]
  B --> F[前置概念2]
```

## 4. 拓展阅读 (reading)
将数学概念与实际应用连接：
- 这个概念在物理/工程/计算机中的应用
- 数学史上的有趣故事
- 与其他数学分支的联系
- 推荐进一步学习的路径

输出格式（JSON）：
{
  "resources": [
    {
      "type": "lecture",
      "title": "讲义标题",
      "content": "讲义正文（Markdown + LaTeX）"
    },
    {
      "type": "exercise",
      "title": "练习标题",
      "content": "题目和解答（Markdown + LaTeX）"
    },
    {
      "type": "mindmap",
      "title": "知识图谱",
      "content": "```mermaid\\n...\\n```"
    },
    {
      "type": "reading",
      "title": "拓展阅读标题",
      "content": "阅读内容"
    }
  ]
}

针对学生的盲区概念，生成1-2种最需要的资源类型。资源精准针对学生的具体误解，篇幅精简（每种资源300字以内）。"""


class ResourceGeneratorAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__("resource_generator", model_router)

    async def run(self, state: TutorState) -> dict:
        blind_spots = json.dumps(state.blind_spots, ensure_ascii=False)
        concept = state.current_concept

        # Get the user's actual request from the last message
        user_request = ""
        for m in reversed(state.messages):
            if m.get("role") == "user":
                user_request = m.get("content", "")
                break

        # If user explicitly asked for a resource, prioritize their request
        if not concept and user_request:
            concept = user_request

        # Detect what type of resource the user wants
        ask_mindmap = any(kw in user_request for kw in ["思维导图", "脑图", "导图", "知识图谱", "知识地图"])
        ask_exercise = any(kw in user_request for kw in ["练习题", "习题", "题目", "出题", "试卷", "练习"])
        ask_lecture = any(kw in user_request for kw in ["讲义", "课件", "教程", "讲解", "笔记", "总结", "归纳"])
        ask_specific = ask_mindmap or ask_exercise or ask_lecture

        if ask_specific:
            wanted = []
            if ask_mindmap: wanted.append("mindmap")
            if ask_exercise: wanted.append("exercise")
            if ask_lecture: wanted.append("lecture")
            type_instruction = f"只生成{'和'.join(wanted)}类型，不要生成其他类型。"
        else:
            type_instruction = "至少1-2种类型。"

        user_prompt = f"""学生的请求：{user_request}
目标概念：{concept}
已诊断的盲区：{blind_spots}

{type_instruction}
{'学生直接请求生成资源，请根据请求内容生成。' if user_request and not blind_spots else '请针对以上盲区生成个性化学习资源。'}返回JSON。"""

        response = await self.generate(RESOURCE_GENERATOR_PROMPT, user_prompt)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {"resources": []}

        resources = result.get("resources", [])

        # Build messages: mindmaps as markdown, everything else as one plaintext block
        messages: list[dict] = []
        plaintext_parts: list[str] = []

        for r in resources:
            rtype = r.get("type", "")
            title = r.get("title", "")
            content = r.get("content", "")
            content = content.replace("\\n", "\n").replace("\r\n", "\n")

            if rtype == "mindmap":
                messages.append({
                    "role": "assistant",
                    "content": f"### {title}\n```mermaid\n{content}\n```",
                })
            else:
                plaintext_parts.append(f"{title}\n\n{content}")

        if plaintext_parts:
            text = "\n\n---\n\n".join(plaintext_parts)
            messages.append({"role": "assistant", "content": text, "plaintext": True})

        if not messages:
            messages.append({"role": "assistant", "content": "资源生成完成，但内容为空。请再试一次。", "plaintext": True})

        # If user asked for a mindmap, offer to explain
        if ask_mindmap:
            messages.append({
                "role": "assistant",
                "content": "需要我帮你详细讲解吗？回复\"帮我讲解\"即可。",
                "plaintext": True,
            })

        return {
            "generated_resources": resources,
            "messages": messages,
        }
