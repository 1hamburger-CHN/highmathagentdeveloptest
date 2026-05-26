import json
import logging
import re

from app.agents.base import BaseAgent, safe_json_parse
from app.agents.state import TutorState

logger = logging.getLogger("tutor")

RESOURCE_GENERATOR_PROMPT = """你是"苏格拉底教练"系统中的学习资源生成专家。当学生被诊断出知识盲区后，你负责生成针对性的补救材料。

## 数学公式输出规范（最高优先级）
- **所有数学公式必须用 LaTeX 格式输出，绝对禁止用纯文本拼凑！**
- 行内公式使用 `$...$` 包裹，如 `$e^{i\theta} = \cos\theta + i\sin\theta$`
- 独立公式使用 `$$...$$` 包裹，如 `$$\oint_C f(z)\,dz = 2\pi i \sum \operatorname{Res}[f(z), z_k]$$`
- 常见错误对照（绝对禁止 → 必须使用）：
  - `f(z)=u+iv` → `$f(z)=u(x,y)+iv(x,y)$`
  - `|z|` → `$|z|$`
  - `C-R方程` → `$\frac{\partial u}{\partial x} = \frac{\partial v}{\partial y}$`
  - `z->z0` 或 `z→z0` → `$z \to z_0$`
  - `围道积分` → `$\oint_C f(z)dz$`
  - `e^z展开` → `$e^z = \sum_{n=0}^{\infty} \frac{z^n}{n!}$`
- **包括比喻和日常语言中提及数学符号时，也使用 LaTeX**
- **绝对不要在 LaTeX 外再出现纯文本拼凑的数学公式**
- **致命错误对照 — 用括号代替 $ 是最常见的错误：**
  - ❌ `(i^2 = -1)` → ✅ `$i^2 = -1$`
  - ❌ `(a + bi)` → ✅ `$a + bi$`
  - ❌ `乘以i相当于旋转90°` → ✅ `乘以 $i$ 相当于旋转 $90^\\circ$`
  - ❌ `Z_C = 1/(iωC)` → ✅ `$Z_C = \\frac{1}{i\\omega C}$`
- **宁可多用一个 $，不可漏掉一个 $。任何数学符号、变量、表达式都必须放在 $...$ 内**

你可以生成5种类型的学习资源：

## 1. 学科介绍 (intro)
当学生询问学科概况时生成。用通俗语言介绍这门学科：
- 这门学科研究什么（一句话核心问题）
- 主要章节和学习路线
- 与中学数学/其他数学分支的联系
- 实际应用场景
- 学习建议
篇幅300-500字，面向初学者，少用公式多用生活类比。

## 2. 教学讲义 (lecture)
结构化讲解一个概念，包含：
- 直观理解（用日常语言解释数学概念）
- 精确定义（LaTeX格式）
- 关键定理及证明思路
- 典型例题+详细解答
- 常见错误提醒

## 3. 分层练习题 (exercise)
按难度分层（基础→进阶→挑战）：
- 基础题：验证基本概念理解
- 进阶题：需要综合运用多个概念
- 挑战题：需要创造性和深度理解
每道题都附带详细解答（LaTeX格式，步骤清晰）

## 4. 思维导图 (mindmap)
Mermaid格式的知识关系图。布局建议：
- 纵向用 graph TD，横向用 graph LR
- 每个节点标签订阅——只写关键词，不用完整句子（如"ε-N定义"而非"极限的ε-N语言精确定义"）
- **节点标签禁止使用LaTeX（如 `$\\varepsilon$`），Mermaid无法渲染数学公式。必须使用纯Unicode文本（如"ε-N定义"、ε、δ）**
- **节点标签禁止包含方括号 `[` `]` 和圆括号 `(` `)`，这些字符会破坏Mermaid语法。用中文全角符号替代：〔、〕、（、）**
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

## 5. 拓展阅读 (reading)
将数学概念与实际应用连接：
- 这个概念在物理/工程/计算机中的应用
- 数学史上的有趣故事
- 与其他数学分支的联系
- 推荐进一步学习的路径

输出格式（JSON）：
{
  "resources": [
    {
      "type": "intro",
      "title": "学科介绍标题",
      "content": "介绍正文（Markdown，面向初学者，少用公式）"
    },
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

针对学生的盲区概念，生成1-2种最需要的资源类型。资源精准针对学生的具体误解，篇幅精简（每种资源300字以内）。

**JSON中LaTeX反斜杠注意**：JSON字符串中反斜杠必须转义。`$\lim$` 要写成 `$\\lim$`，`$\frac{a}{b}$` 要写成 `$\\frac{a}{b}$`。"""


class ResourceGeneratorAgent(BaseAgent):
    def __init__(self, model_router, retriever=None):
        super().__init__("resource_generator", model_router)
        self.retriever = retriever

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
            # Strip common "generate X" prefixes to get the actual topic
            concept = re.sub(r"^(帮我|请|帮忙|给我|来)?(生成|做|写|制作|创建)", "", user_request).strip()
            # Also strip trailing question words
            concept = re.sub(
                r"(是什么|是什么意思|什么意思|怎么理解|如何理解|怎么用|"
                r"怎么算|怎么证|怎么计算|怎么做|怎么求|是什么鬼|"
                r"的定义|的性质|的公式|的推导|的证明|能讲讲吗|能说说吗)$",
                "", concept,
            )
            if not concept or len(concept) < 2:
                concept = user_request

        # --- Domain validation (KB check → math check) ---
        logger.info(f"RG domain check: concept={concept!r} current_concept={state.current_concept!r}")
        allow_out_of_domain = getattr(state, "_allow_out_of_domain", False)
        # Resolve node IDs like "complex-2.2" to human-readable titles
        display_concept = concept
        if self.retriever:
            display_concept = self.retriever.resolve_concept_name(concept)
        if self.retriever and not allow_out_of_domain:
            if not self.retriever.is_concept_in_domain(concept):
                from app.core.safety import SafetyPipeline
                if not SafetyPipeline.is_math_related(display_concept):
                    logger.info(f"Non-math concept rejected: '{display_concept}'")
                    return {
                        "messages": [{
                            "role": "assistant",
                            "content": f"{display_concept} 不属于数学领域，请询问复变函数相关问题。",
                        }],
                    }
                logger.info(f"Out-of-domain math concept: '{display_concept}', asking for confirmation")
                return {
                    "_pending_out_of_domain_concept": display_concept,
                    "messages": [{
                        "role": "assistant",
                        "content": f"{display_concept} 不在当前复变函数知识范围内，需要我帮你搜索并生成相关内容吗？",
                    }],
                }
        # --- End domain validation ---

        # Detect what type of resource the user wants
        ask_intro = any(kw in user_request for kw in ["介绍", "概述", "概览", "是什么", "什么是", "入门"])
        ask_mindmap = any(kw in user_request for kw in ["思维导图", "脑图", "导图", "知识图谱", "知识地图"])
        ask_exercise = any(kw in user_request for kw in ["练习题", "习题", "题目", "出题", "试卷", "练习"])
        ask_lecture = any(kw in user_request for kw in ["讲义", "课件", "教程", "讲解", "笔记", "总结", "归纳"])
        ask_generic = any(kw in user_request for kw in ["生成", "做", "写", "制作", "创建"])
        # "生成X" with no specific type → default to lecture
        if not ask_intro and not ask_mindmap and not ask_exercise and not ask_lecture and ask_generic:
            ask_lecture = True
        ask_specific = ask_intro or ask_mindmap or ask_exercise or ask_lecture

        if ask_specific:
            wanted = []
            if ask_intro: wanted.append("intro")
            if ask_mindmap: wanted.append("mindmap")
            if ask_exercise: wanted.append("exercise")
            if ask_lecture: wanted.append("lecture")
            type_instruction = f"只生成{'和'.join(wanted)}类型，不要生成其他类型。"
        else:
            type_instruction = "至少1-2种类型。不要生成练习题（exercise）和思维导图（mindmap），练习题和思维导图需用户主动要求才生成。"

        user_prompt = f"""学生的请求：{user_request}
目标概念：{concept}
已诊断的盲区：{blind_spots}

{type_instruction}
{'学生直接请求生成资源，请根据请求内容生成。' if user_request and not blind_spots else '请针对以上盲区生成个性化学习资源。'}返回JSON。"""

        response = await self.generate(RESOURCE_GENERATOR_PROMPT, user_prompt)
        try:
            result = safe_json_parse(response)
        except json.JSONDecodeError as e:
            logger.warning(f"ResourceGenerator JSON parse failed: {e}, raw ({len(response)} chars): {response[:500]}")
            result = {"resources": []}

        resources = result.get("resources", [])

        # When user asked for specific types, discard anything else the LLM snuck in
        if ask_specific:
            resources = [r for r in resources if r.get("type") in wanted]

        # Build messages: mindmaps with mermaid fence, others as markdown
        messages: list[dict] = []
        md_parts: list[str] = []

        for r in resources:
            rtype = r.get("type", "")
            title = r.get("title", "")
            content = r.get("content", "")
            content = content.replace("\\n", "\n").replace("\r\n", "\n")
            # Strip markdown heading markers the LLM may have injected
            content = re.sub(r"^#{1,4}\s+", "", content, flags=re.MULTILINE)
            # Dedent — 4-space indent triggers code blocks in markdown, LLMs often indent content
            content = re.sub(r"^ {4}", "", content, flags=re.MULTILINE)

            if rtype == "mindmap":
                # Strip mermaid fences that the LLM may have included
                content = re.sub(r"^```mermaid\s*\n?", "", content, flags=re.MULTILINE)
                content = re.sub(r"\n?```\s*$", "", content)
                if ask_mindmap:
                    footer = "\n\n> 需要我帮你详细讲解吗？回复\"帮我讲解\"即可。"
                else:
                    footer = ""
                messages.append({
                    "role": "assistant",
                    "content": f"### {title}\n```mermaid\n{content}\n```\n\n{footer}",
                })
            elif rtype == "intro":
                md_parts.append(f"## {title}\n\n{content}")
            else:
                md_parts.append(f"### {title}\n\n{content}")

        if md_parts:
            text = "\n\n---\n\n".join(md_parts)
            messages.append({"role": "assistant", "content": text})

        if not messages:
            messages.append({"role": "assistant", "content": "资源生成完成，但内容为空。请再试一次。"})

        return {
            "generated_resources": resources,
            "messages": messages,
        }
