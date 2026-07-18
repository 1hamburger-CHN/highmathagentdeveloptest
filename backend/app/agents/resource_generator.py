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

**重要规则：如果用户已经明确指定了具体知识点和资源类型（如"帮我生成共形映射的思维导图"），直接生成，绝对不要追问。只有用户没指定概念或类型时才需要确认。**

**JSON中LaTeX反斜杠注意**：JSON字符串中反斜杠必须转义。`$\lim$` 要写成 `$\\lim$`，`$\frac{a}{b}$` 要写成 `$\\frac{a}{b}$`。"""


def _normalize_latex_delimiters(text: str) -> str:
    """Ensure LaTeX math has proper $ delimiters for KaTeX rendering.

    Strategy: split text into $...$ blocks and bare-text blocks.
    Only wrap bare-text blocks — never touch already-delimited content.
    """
    # Pre-process: convert \(...\) → $...$ and \[...\] → $$...$$
    # (Spark/DeepSeek often output LaTeX with these delimiters, KaTeX needs $)
    text = re.sub(r'\\\[', '$$', text)
    text = re.sub(r'\\\]', '$$', text)
    text = re.sub(r'\\\(', '$', text)
    text = re.sub(r'\\\)', '$', text)
    # Ensure $$ display math starts on its own line
    text = re.sub(r'([^\n])\$\$', r'\1\n$$', text)
    text = re.sub(r'\$\$([^\n])', r'$$\n\1', text)

    # Pre-process: wrap \begin{env}...\end{env} blocks in $$...$$
    # (must happen BEFORE individual command wrapping, which would break environments)
    text = re.sub(
        r'(\\begin\{[a-zA-Z*]+\}.*?\\end\{[a-zA-Z*]+\})',
        lambda m: f'$${m.group(1)}$$' if '$' not in m.group(1) else m.group(1),
        text,
        flags=re.DOTALL,
    )

    # Split into alternating segments: [bare, $math$, bare, $math$, ...]
    parts = re.split(r'(\$[^$]+\$|\$\$[^$]+\$\$)', text)

    result = []
    for part in parts:
        if not part:
            continue
        # Already-delimited math — leave as-is
        if part.startswith("$"):
            result.append(part)
            continue

        # Bare text: wrap unescaped LaTeX commands and math patterns
        processed = part
        # LaTeX commands with braces: \frac{...}{...}, \lim_{...}, \operatorname{...}
        # EXCLUDE \begin and \end — they're handled above as whole environments
        processed = re.sub(
            r'(\\[a-zA-Z]{2,}(?:\{[^{}]*\})+)',
            lambda m: m.group(0) if m.group(1).startswith(('\\begin', '\\end'))
            else f'${m.group(1)}$',
            processed,
        )
        # Bare LaTeX commands (exclude \begin and \end)
        processed = re.sub(
            r'(?<![$\\])(\\(?:to|neq|bar|infty|partial|quad|cdot|times|div|pm|mp|geq|leq|gg|ll|sim|approx|equiv|propto|perp|parallel|angle|triangle|forall|exists|nabla|in|notin|subset|supset|cup|cap|setminus|wedge|vee|oplus|otimes|circ|mapsto|implies|iff|ldots|cdots|vdots|ddots|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|mathbb|mathcal|mathfrak|mathrm|mathbf|mathit|mathsf|mathtt|operatorname|text|textbf|textit|overline|underline|hat|tilde|vec|dot|ddot|widehat|widetilde|prime|ell|hbar|imath|jmath|Re|Im|arg|det|dim|exp|gcd|hom|inf|ker|lg|lim|liminf|limsup|ln|log|max|min|Pr|sec|sin|arcsin|sinh|sup|tan|arctan|tanh|cos|arccos|cosh|cot|csc|coth|deg))(?![a-zA-Z{])',
            r'$\1$', processed,
        )
        # Superscript/subscript: x^2, z_0, e^{i\theta}, x_{n+1}
        processed = re.sub(
            r'(?<![$\\])([a-zA-Z0-9])([_^])(\{[^{}]*\}|[0-9a-zA-Z]+)',
            lambda m: f'${m.group(1)}{m.group(2)}{m.group(3)}$'
            if not re.search(r'[$\\]', m.group(0)) else m.group(0),
            processed,
        )
        result.append(processed)

    return "".join(result)


def _resource_type_label(rtype: str) -> str:
    """Map resource type slug to display label."""
    return {
        "intro": "介绍",
        "lecture": "讲义",
        "exercise": "练习题",
        "mindmap": "思维导图",
        "reading": "拓展阅读",
    }.get(rtype, "学习资源")


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

        # Strip resource type keywords from concept to get the actual topic
        # e.g. "共形映射的思维导图" → "共形映射", "留数定理练习题" → "留数定理"
        _resource_type_strip_patterns = [
            r"的?(思维导图|脑图|导图|知识图谱|知识地图)$",
            r"的?(练习题|习题|题目|试卷|练习)$",
            r"的?(讲义|课件|教程|笔记|总结|归纳)$",
            r"的?(阅读材料|拓展阅读|拓展|资料)$",
            r"的?(资源|材料)$",
            r"的?(介绍|概述|概览|入门)$",
        ]
        for pattern in _resource_type_strip_patterns:
            concept = re.sub(pattern, "", concept)
        # Also strip trailing 的/之 if they're now dangling
        concept = re.sub(r"的$|之$", "", concept)

        # --- Detect resource-type-only requests (no specific concept) ---
        _resource_type_keywords = [
            "练习题", "习题", "题目", "讲义", "课件", "教程", "笔记",
            "思维导图", "脑图", "导图", "知识图谱", "资源", "材料",
            "练习", "总结", "归纳", "阅读材料", "拓展阅读",
        ]
        _concept_is_resource_type = concept and any(kw in concept for kw in _resource_type_keywords)
        _concept_too_vague = not concept or len(concept) < 3

        if (_concept_is_resource_type or _concept_too_vague) and user_request:
            # If we have context from prior coaching, use it
            context_concept = state.current_concept
            if self.retriever and context_concept:
                context_concept = self.retriever.resolve_concept_name(context_concept)
            if context_concept and not _concept_is_resource_type:
                # Concept from prior coaching exists — use it directly
                concept = context_concept
                logger.info(f"Using prior coaching concept: '{concept}'")
            else:
                # No context — ask the user
                logger.info(f"Resource type request without specific concept: '{concept}'")
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": (
                            "好的！你想针对哪个知识点生成呢？比如：\n"
                            "- C-R 方程\n- 留数定理\n- 泰勒级数\n- 共形映射\n"
                            "告诉我具体概念，我来为你生成。"
                        ),
                    }],
                }

        # --- Domain validation (KB check → math check) ---
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

        # --- Enrich with knowledge base search results ---
        enrichment_parts = []
        sources: list[dict] = []
        if self.retriever and concept:
            # 1. Textbook
            try:
                tb = self.retriever.search_textbook(concept, top_k=2)
                if tb:
                    passages = [r.get("content", "")[:300] for r in tb]
                    enrichment_parts.append(
                        "【教材参考】（哈工大《复变函数与积分变换》教材）\n"
                        + "\n---\n".join(passages)
                    )
                    sources.append({"type": "textbook", "source": f"哈工大《复变函数与积分变换》教材 · {display_concept}", "concept": display_concept})
            except Exception as e:
                logger.warning(f"Textbook search failed: {e}")

            # 2. Handouts (only for lecture-type requests)
            try:
                if ask_lecture or ask_generic or not ask_specific:
                    ho = self.retriever.search_handouts(concept, top_k=2)
                    if ho:
                        passages = [r.get("content", "")[:300] for r in ho]
                        enrichment_parts.append(
                            "【讲义参考】（哈工大课堂讲义）\n"
                            + "\n---\n".join(passages)
                        )
                        sources.append({"type": "handouts", "source": f"哈工大复变课堂讲义 · {display_concept}", "concept": display_concept})
            except Exception as e:
                logger.warning(f"Handout search failed: {e}")

            # 3. Exercises (only for exercise requests)
            try:
                if ask_exercise:
                    ex = self.retriever.search_exercises(concept, top_k=3)
                    if ex:
                        passages = [r.get("content", "")[:300] for r in ex]
                        enrichment_parts.append(
                            "【习题参考】（薪火复变综合训练题库）\n"
                            + "\n---\n".join(passages)
                        )
                        sources.append({"type": "exercises", "source": f"薪火复变综合训练题库 · {display_concept}", "concept": display_concept})
            except Exception as e:
                logger.warning(f"Exercise search failed: {e}")

        enrichment_text = "\n\n".join(enrichment_parts) if enrichment_parts else ""
        if enrichment_text:
            enrichment_text = "\n\n" + enrichment_text
            logger.info(f"Enriched prompt with {len(enrichment_parts)} source(s) for '{concept}'")

        user_prompt = f"""学生的请求：{user_request}
目标概念：{concept}
已诊断的盲区：{blind_spots}
{enrichment_text}

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
            # Normalize LaTeX: wrap naked math expressions in $ delimiters
            content = _normalize_latex_delimiters(content)

            if rtype == "mindmap":
                # Strip mermaid fences that the LLM may have included
                content = re.sub(r"^```mermaid\s*\n?", "", content, flags=re.MULTILINE)
                content = re.sub(r"\n?```\s*$", "", content)
                if ask_mindmap:
                    footer = "\n\n> 需要我帮你详细讲解吗？回复\"帮我讲解\"即可。"
                else:
                    footer = ""
                messages.append({
                    "role": "resource",
                    "content": f"### {title}\n```mermaid\n{content}\n```\n\n{footer}",
                    "resourceType": "思维导图",
                    "title": title,
                })
            elif rtype == "intro":
                md_parts.append(f"## {title}\n\n{content}")
            else:
                md_parts.append(f"### {title}\n\n{content}")

        if md_parts:
            text = "\n\n---\n\n".join(md_parts)
            # Use the first resource's type as the badge label
            first_type = resources[0].get("type", "") if resources else ""
            first_title = resources[0].get("title", "") if resources else ""
            messages.append({
                "role": "resource",
                "content": text,
                "resourceType": _resource_type_label(first_type),
                "title": first_title,
            })

        if not messages:
            messages.append({"role": "assistant", "content": "资源生成完成，但内容为空。请再试一次。"})

        # Append source references to the last message
        if sources and messages:
            ref_lines = "\n\n---\n\n📚 **参考来源**\n" + "\n".join(f"- {s['source']}" for s in sources)
            messages[-1]["content"] += ref_lines

        # Persist to DB for resource center
        import hashlib
        uid = getattr(state, "user_id", "") or "anonymous"
        for r in resources:
            rtype = r.get("type", "")
            rtitle = r.get("title", "")
            rcontent = r.get("content", "")
            rid = hashlib.md5(f"{uid}:{r.get('type')}:{r.get('title')}".encode()).hexdigest()[:12]
            try:
                from app.models.db_models import save_resource
                save_resource(rid, uid, rtype, rtitle, rcontent, concept, json.dumps(sources, ensure_ascii=False))
            except Exception:
                pass

        return {
            "generated_resources": resources,
            "sources": sources,
            "messages": messages,
        }
