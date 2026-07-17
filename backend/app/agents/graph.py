"""LangGraph Supervisor state graph for the Socratic Tutor system."""
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.animation_generator import AnimationGeneratorAgent
from app.agents.assessor import AssessorAgent
from app.agents.diagnostician import DiagnosticianAgent
from app.agents.profile_builder import ProfileBuilderAgent
from app.agents.quality_gate import QualityGateAgent
from app.agents.resource_generator import ResourceGeneratorAgent
from app.agents.socratic_coach import SocraticCoachAgent
from app.agents.state import AgentState, TutorState
from app.core.llm import ModelRouter
from app.core.safety import SafetyPipeline
from app.knowledge.retriever import HybridRetriever

logger = logging.getLogger("tutor.graph")

# Shared model router (initialized once at graph build time)
_router = ModelRouter()
_retriever = HybridRetriever()

# Build valid concept ID set + alias reverse map
_valid_concept_ids: set[str] = set()
_alias_to_id: dict[str, str] = {}
_concept_id_to_title: dict[str, str] = {}
try:
    from pathlib import Path
    from app.knowledge.loader import load_curriculum
    _curriculum_path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
    _nodes = load_curriculum(str(_curriculum_path))
    for node in _nodes:
        _valid_concept_ids.add(node.id)
        _concept_id_to_title[node.id] = node.title
    # Build alias → ID map from retriever's aliases
    for alias, title in _retriever._concept_aliases.items():
        if title in _retriever._id_to_title.values():
            for nid, ntitle in _retriever._id_to_title.items():
                if ntitle == title:
                    _alias_to_id[alias] = nid
                    break
    # Also add title → ID
    for nid, ntitle in _retriever._id_to_title.items():
        _alias_to_id[ntitle] = nid
        # Lowercase
        _alias_to_id[ntitle.lower()] = nid
    # English variants from concept aliases (e.g. "residue_theorem" → complex-6.2)
    for alias, title in _retriever._concept_aliases.items():
        if "_" in alias or alias.isascii():
            for nid, ntitle in _retriever._id_to_title.items():
                if ntitle == title:
                    _alias_to_id[alias.lower()] = nid
                    _alias_to_id[alias.replace("_", " ").lower()] = nid
                    break
    logger.info(f"Built concept normalizer: {len(_valid_concept_ids)} IDs, {len(_alias_to_id)} aliases")
except Exception as e:
    logger.warning(f"Failed to build concept normalizer: {e}")


def _normalize_concept_id(raw: str) -> str | None:
    """Normalize an LLM-generated concept ID/name to a valid curriculum ID.

    Returns the normalized complex-* ID, or None if no match.
    """
    if not raw:
        return None
    raw = str(raw).strip()
    # 1. Already valid
    if raw in _valid_concept_ids:
        return raw
    # 2. Direct alias match
    if raw in _alias_to_id:
        return _alias_to_id[raw]
    # 3. Lowercase match
    if raw.lower() in _alias_to_id:
        return _alias_to_id[raw.lower()]
    # 4. Fuzzy: check if raw contains a known concept title
    for title, nid in _alias_to_id.items():
        if len(title) >= 3 and title in raw:
            return nid
    # 5. Try to match via retriever domain check
    try:
        if _retriever.is_concept_in_domain(raw):
            for nid in _valid_concept_ids:
                if _concept_id_to_title.get(nid, "") in raw:
                    return nid
    except Exception:
        pass
    # 6. Heuristic: LLM often outputs things like "residue-6.0.0" — try prefix match
    import re
    residue_match = re.match(r"residue[-_]?(\d)", raw, re.IGNORECASE)
    if residue_match:
        return "complex-6.2"  # 留数定理
    # More heuristics for common LLM patterns
    heuristic_map = {
        r"复数|complex[_ ]?number": "complex-1.1",
        r"解析|analytic|holomorphic": "complex-2.2",
        r"cauchy.*riemann|cr[_ ]?equation": "complex-2.2",
        r"cauchy.*(integral|formula)": "complex-4.3",
        r"cauchy.*goursat|cauchy.*theorem": "complex-4.2",
        r"contour|围道|路径积分": "complex-4.1",
        r"积分.*定义|复积分": "complex-4.1",
        r"taylor|泰勒": "complex-5.1",
        r"laurent|洛朗": "complex-5.2",
        r"residue|留数": "complex-6.2",
        r"singularity|奇点": "complex-6.1",
        r"conformal|共形|保角|保形": "complex-7.1",
        r"fourier|傅里叶|傅立叶": "complex-8.1",
        r"laplace|拉普拉斯|拉氏": "complex-8.2",
    }
    for pattern, nid in heuristic_map.items():
        if re.search(pattern, raw, re.IGNORECASE):
            return nid
    return None

# Build prerequisite map from curriculum for score propagation
_prerequisites: dict[str, list[str]] = {}
try:
    from pathlib import Path
    from app.knowledge.loader import load_curriculum
    _curriculum_path = Path(__file__).parent.parent.parent / "data" / "seed" / "curriculum.yaml"
    _nodes = load_curriculum(str(_curriculum_path))
    for node in _nodes:
        _prerequisites[node.id] = node.prerequisites or []
    logger.info(f"Loaded prerequisite map: {len(_prerequisites)} concepts")
except Exception:
    logger.warning("Failed to load prerequisite map, score propagation disabled")

_profile_builder = ProfileBuilderAgent(_router)
_diagnostician = DiagnosticianAgent(_router)
_socratic_coach = SocraticCoachAgent(_router)
_resource_generator = ResourceGeneratorAgent(_router, _retriever)
_assessor = AssessorAgent(_router)
_quality_gate = QualityGateAgent(_router)
_animation_generator = AnimationGeneratorAgent(_router)


def build_tutor_graph() -> StateGraph:
    workflow = StateGraph(TutorState)

    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("profile_check", profile_check_node)
    workflow.add_node("build_profile", build_profile_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("coach", coach_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("assess", assess_node)
    workflow.add_node("quality_gate", quality_gate_node)
    workflow.add_node("animation_render", animation_render_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("safety_check")

    workflow.add_conditional_edges(
        "safety_check",
        route_safety,
        {"reject": "respond", "pass": "profile_check"},
    )
    workflow.add_conditional_edges(
        "profile_check",
        route_profile_check,
        {"build_profile": "build_profile", "diagnose": "diagnose", "coach": "coach", "generate": "generate", "respond": "respond"},
    )
    workflow.add_edge("build_profile", "coach")
    workflow.add_edge("diagnose", "coach")
    workflow.add_conditional_edges(
        "coach",
        route_coach,
        {"generate": "generate", "assess": "assess", "animation_render": "animation_render", "respond": "respond"},
    )
    workflow.add_edge("generate", "respond")
    workflow.add_edge("animation_render", "generate")
    workflow.add_edge("assess", "quality_gate")
    workflow.add_conditional_edges(
        "quality_gate",
        route_quality,
        {"regenerate": "generate", "respond": "respond"},
    )
    workflow.add_edge("respond", END)

    return workflow.compile()


# --- Routing ---

def route_safety(state: TutorState) -> str:
    return "reject" if state._safety_rejected else "pass"


def route_profile_check(state: TutorState) -> str:
    if getattr(state, "_respond_directly", False):
        return "respond"
    if getattr(state, "_is_resource_request", False):
        return "generate"
    if getattr(state, "_animation_direct", False):
        return "coach"
    # Has profile (even if empty) → diagnose to start building it
    if state.profile:
        return "diagnose"
    # No profile yet → go straight to coach, don't block first response
    # Profile will be built incrementally via diagnostician on later turns
    return "coach"


def route_coach(state: TutorState) -> str:
    if getattr(state, "_animation_direct", False):
        return "animation_render"
    if getattr(state, "_animation_pending", False):
        return "animation_render"
    if state.coach_confidence > 0.5:
        return "assess"
    # Only generate resources when user explicitly requests them
    if getattr(state, "_is_resource_request", False):
        return "generate"
    return "respond"


def route_quality(state: TutorState) -> str:
    # Only regenerate if assessment actually failed (not on first pass)
    assessment = getattr(state, "assessment_result", None)
    if assessment and not assessment.get("correct", True):
        if state.quality_retries < 2:
            return "regenerate"
    return "respond"


# --- Nodes ---

def safety_check_node(state: TutorState) -> dict[str, Any]:
    user_msg = ""
    assistant_msg = ""
    for m in reversed(state.messages):
        role = m.get("role", "")
        if role == "user" and not user_msg:
            user_msg = m.get("content", "")
        elif role in ("assistant", "coach") and not assistant_msg:
            assistant_msg = m.get("content", "")
        if user_msg and assistant_msg:
            break

    # Image analysis context: the assistant message carries validated math content.
    # Don't reject based on the user's short text alone — the image already
    # proves this is a legitimate math conversation.
    if "图片分析结果" in assistant_msg:
        logger.info(f"Safety check: image analysis context detected, bypassing filter")
        return {"_safety_rejected": False}

    result = SafetyPipeline.filter(user_msg, assistant_msg)
    logger.info(f"Safety check: msg={user_msg!r} allowed={result['allowed']} reason={result['reason']}")
    if not result["allowed"]:
        return {
            "_safety_rejected": True,
            "messages": [{"role": "assistant", "content": result["content"]}],
        }
    return {"_safety_rejected": False}


def profile_check_node(state: TutorState) -> dict[str, Any]:
    has_profile = bool(state.profile and state.profile.get("knowledge_mastery"))
    user_msg = ""
    for m in reversed(state.messages):
        if m.get("role") == "user":
            user_msg = m.get("content", "").strip()
            break

    # --- Out-of-domain confirmation handling ---
    pending = getattr(state, "_pending_out_of_domain_concept", "")
    if pending:
        if _is_out_of_domain_confirmation(user_msg):
            return {
                "current_state": AgentState.PROFILE_CHECK,
                "_has_profile": has_profile,
                "_is_resource_request": True,
                "_is_direct_question": False,
                "_allow_out_of_domain": True,
                "current_concept": pending,
                "_pending_out_of_domain_concept": "",
            }
        elif _is_out_of_domain_decline(user_msg):
            return {
                "current_state": AgentState.PROFILE_CHECK,
                "_has_profile": has_profile,
                "_is_resource_request": False,
                "_is_direct_question": False,
                "_pending_out_of_domain_concept": "",
                "_respond_directly": True,
                "messages": [{"role": "assistant", "content": "好的，有其他复变函数的问题可以随时问我。"}],
            }
        else:
            logger.info(f"Clearing pending out-of-domain concept '{pending}' — unrelated message")
            # Fall through to normal detection (pending implicitly cleared)

    is_direct_question = _is_direct_math_question(user_msg)
    is_resource_request = _is_resource_request(user_msg, bool(state.messages))
    is_animation_request = _is_animation_request(user_msg)

    # Manual animation request → skip coaching, go straight to animation
    if is_animation_request:
        concept = _extract_concept_from_question(user_msg)
        concept = _clean_animation_concept(concept)
        if concept and len(concept) >= 2:
            # Resolve concept name to curriculum node ID (e.g. "留数定理" → "complex-6.2")
            resolved_id = _retriever.resolve_concept_name(concept)
            alias_title = _retriever._concept_aliases.get(concept)
            if alias_title:
                # Reverse lookup: find node ID for this title
                for nid, ntitle in _retriever._id_to_title.items():
                    if ntitle == alias_title:
                        resolved_id = nid
                        break
            logger.info(f"Animation: '{concept}' → resolved to '{resolved_id}'")
            return {
                "current_state": AgentState.PROFILE_CHECK,
                "_has_profile": has_profile,
                "_is_direct_question": False,
                "_is_resource_request": False,
                "_animation_pending": True,
                "_animation_direct": True,
                "current_concept": resolved_id,
                "blind_spots": [{"concept_id": resolved_id, "type": "concept", "description": f"用户请求{concept}动画演示"}],
            }

    # Out-of-domain direct question → redirect to generate (don't do Socratic coaching)
    # Only check if this looks like a NEW question, not a response to the coach
    if is_direct_question and not is_resource_request and _looks_like_new_question(user_msg, bool(state.messages)):
        concept = _extract_concept_from_question(user_msg)
        if concept and len(concept) >= 2 and not _retriever.is_concept_in_domain(concept):
            from app.core.safety import SafetyPipeline
            if SafetyPipeline.is_math_related(concept):
                logger.info(f"Out-of-domain math question: '{concept}', redirect to generate")
                return {
                    "current_state": AgentState.PROFILE_CHECK,
                    "_has_profile": has_profile,
                    "_is_resource_request": True,
                    "_is_direct_question": False,
                    "current_concept": concept,
                    "_pending_out_of_domain_concept": "",
                }

    # Init minimal profile on first visit so later turns can diagnose
    if not has_profile:
        init_profile = {
            "knowledge_mastery": [],
            "blind_spots": [],
            "behavior": {"response_style": "cautious", "resource_preference": "visual"},
        }
    else:
        init_profile = None

    return {
        "current_state": AgentState.PROFILE_CHECK,
        "_has_profile": has_profile or init_profile is not None,
        "_is_direct_question": is_direct_question,
        "_is_resource_request": is_resource_request,
        "_pending_out_of_domain_concept": "",
        **({"profile": init_profile} if init_profile else {}),
    }


def _is_direct_math_question(text: str) -> bool:
    """Check if this is a concrete math question that can skip profile building."""
    indicators = [
        "等于", "多少", "怎么算", "什么是", "是什么", "什么意思",
        "帮我", "怎么证", "证明", "求", "计算", "解",
        "?", "？", "+", "-", "*", "/", "=",
    ]
    score = sum(1 for ind in indicators if ind in text)
    # Long messages or messages with math indicators are likely direct questions
    return len(text) > 4 or score >= 1


def _looks_like_new_question(text: str, has_history: bool = False) -> bool:
    """Check if this message is asking a NEW question vs responding to the coach.

    If there's conversation history, it's almost certainly a response to the coach.
    Out-of-domain detection should only apply to the FIRST message in a session.
    """
    # With existing conversation, always treat as a response
    if has_history:
        return False
    # First message: check if it looks like a domain-specific question
    # Short ambiguous first messages are allowed through
    return len(text) > 15


def _is_animation_request(text: str) -> bool:
    """Check if user is explicitly requesting an animation."""
    import re
    animation_patterns = [
        r"生成.*动画", r"做.*动画", r"画.*动画", r"制作.*动画",
        r"动画.*演示", r"可视化.*演示",
        r"动画.*生成", r"来个.*动画",
    ]
    for pat in animation_patterns:
        if re.search(pat, text):
            return True
    return False


def _clean_animation_concept(concept: str) -> str:
    """Strip animation-related words from extracted concept."""
    import re
    # Remove animation words from both ends
    concept = re.sub(r"^(帮我|请|帮忙|给我|来)?\s*(生成|做|画|制作|创建)\s*", "", concept)
    concept = re.sub(r"\s*(的?\s*(动画|可视化|演示|视频))\s*$", "", concept)
    return concept.strip()


def _is_resource_request(text: str, has_history: bool = False) -> bool:
    """Check if user is explicitly asking for a learning resource.

    When there's conversation history, only match explicit creation requests
    to avoid false positives from normal math discussion.
    """
    # Conversational phrases that are NOT resource requests
    _conversational = ["给我一个例子", "给我看例子", "能给我看看", "给我看看"]
    if any(kw in text for kw in _conversational):
        return False

    # Explicit creation verbs — always trigger resource generation
    _creation_verbs = ["生成", "做", "写", "制作", "创建", "帮我生成", "给我生成", "给我做"]
    if any(kw in text for kw in _creation_verbs):
        return True

    # Without conversation history, descriptive keywords also trigger
    # (user is starting fresh and asking for materials)
    if not has_history:
        _intro_keywords = [
            "思维导图", "脑图", "导图", "知识图谱",
            "讲义", "课件", "教程", "笔记", "总结", "归纳",
            "练习题", "习题", "题目", "出题", "试卷",
            "阅读材料", "拓展", "资料",
            "介绍", "概述", "概览", "入门",
        ]
        if any(kw in text for kw in _intro_keywords):
            return True

    return False


def _is_out_of_domain_confirmation(text: str) -> bool:
    """Detect user confirming they want out-of-domain content generated.

    Must be a SHORT confirmation message, not a detailed math response
    that accidentally contains a keyword substring.
    """
    # Not a confirmation if it's a long, detailed message
    if len(text) > 12:
        return False
    keywords = [
        "好的", "可以", "行", "没问题", "嗯", "是",
        "要", "需要", "搜一下", "搜索一下", "帮我搜",
        "帮我生成", "生成吧", "做吧", "ok", "yes",
        "确认", "是的", "来吧",
    ]
    return any(kw in text for kw in keywords)


def _is_out_of_domain_decline(text: str) -> bool:
    """Detect user declining out-of-domain generation."""
    if len(text) > 10:
        return False
    keywords = ["不用", "不要", "算了", "不了", "取消", "不需要", "别"]
    return any(kw in text for kw in keywords)


def _extract_concept_from_question(text: str) -> str:
    """Extract the likely math concept from a question."""
    import re
    concept = re.sub(
        r"^(什么是|啥是|什么叫|什么是|解释一下|讲讲|请问|问一下|"
        r"怎么理解|如何理解|怎么证|证明一下|帮我|请|帮忙|给我|"
        r"你能|能|可以|能不能|可不可以|说一下|说说)",
        "", text,
    )
    # Strip trailing punctuation AND question words
    concept = re.sub(r"[?？。！!，,：:]+$", "", concept)
    concept = re.sub(
        r"(是什么|是什么意思|什么意思|怎么理解|如何理解|怎么用|"
        r"怎么算|怎么证|怎么计算|怎么做|怎么求|是什么鬼|"
        r"的定义|的性质|的公式|的推导|的证明|能讲讲吗|能说说吗)$",
        "", concept,
    )
    return concept.strip()


async def build_profile_node(state: TutorState) -> dict[str, Any]:
    result = await _profile_builder.run(state)
    result["current_state"] = AgentState.BUILD_PROFILE
    # Strip messages — profile builder works silently in background
    result.pop("messages", None)
    return result


async def diagnose_node(state: TutorState) -> dict[str, Any]:
    # === KB enrichment ===
    concept = state.current_concept
    kb_context = {}
    if concept:
        try:
            kb_results = _retriever.search_all(concept, top_k=2)
            kb_context = {
                "textbook": [r.get("content", "")[:300] for r in kb_results.get("textbook", [])],
                "handouts": [r.get("content", "")[:300] for r in kb_results.get("handouts", [])],
            }
        except Exception:
            pass
    state._kb_context = kb_context
    # === end KB enrichment ===

    result = await _diagnostician.run(state)
    result["current_state"] = AgentState.DIAGNOSE
    result.pop("messages", None)

    # Merge diagnosis into profile so frontend progress bar updates
    profile = dict(state.profile) if state.profile else {}
    existing_mastery = {m["concept_id"]: m for m in profile.get("knowledge_mastery", [])}
    mastered = result.get("mastered_concepts", []) or []
    blind = result.get("blind_spots", []) or []

    # Update mastery: mark diagnosed concepts with scores
    for cid in mastered:
        normalized = _normalize_concept_id(cid)
        if normalized is None:
            logger.warning(f"Diagnostician returned unknown concept ID: '{cid}', skipped")
            continue
        if normalized not in existing_mastery:
            existing_mastery[normalized] = {"concept_id": normalized, "score": 0.7, "confidence": 0.6}
        else:
            existing_mastery[normalized]["score"] = max(existing_mastery[normalized].get("score", 0), 0.7)

    # Mark concepts with blind spots at lower scores
    for bs in blind:
        cid = bs.get("concept_id", "")
        if not cid:
            continue
        normalized = _normalize_concept_id(cid)
        if normalized is None:
            logger.warning(f"Diagnostician returned unknown blind spot ID: '{cid}', skipped")
            continue
        if normalized not in existing_mastery:
            existing_mastery[normalized] = {"concept_id": normalized, "score": 0.2, "confidence": 0.5}

    # Propagate inferred scores to prerequisites
    # If student proves mastery of a concept, its prerequisites likely known
    for cid in list(existing_mastery.keys()):
        score = existing_mastery[cid].get("score", 0)
        if score >= 0.5:
            prereqs = _prerequisites.get(cid, [])
            for prereq_id in prereqs:
                inferred_score = 0.35 if score >= 0.7 else 0.25
                inferred_conf = 0.25
                if prereq_id not in existing_mastery:
                    existing_mastery[prereq_id] = {
                        "concept_id": prereq_id, "score": inferred_score, "confidence": inferred_conf,
                    }
                    logger.info(f"Profile inferred: {prereq_id} → {inferred_score:.2f} (prereq of {cid})")
                elif existing_mastery[prereq_id].get("score", 0) < inferred_score:
                    existing_mastery[prereq_id]["score"] = inferred_score
                    existing_mastery[prereq_id]["confidence"] = max(
                        existing_mastery[prereq_id].get("confidence", 0), inferred_conf,
                    )

    profile["knowledge_mastery"] = list(existing_mastery.values())
    profile["blind_spots"] = blind
    result["profile"] = profile

    return result


async def coach_node(state: TutorState) -> dict[str, Any]:
    # Direct animation request — skip coach, just pass through to animation_render
    if getattr(state, "_animation_direct", False):
        return {
            "current_state": AgentState.COACH,
            "_animation_pending": True,
        }

    # === KB enrichment ===
    concept = state.current_concept
    kb_context = {}
    if concept:
        try:
            kb_results = _retriever.search_all(concept, top_k=2)
            kb_context = {
                "textbook": [r.get("content", "")[:300] for r in kb_results.get("textbook", [])],
                "handouts": [r.get("content", "")[:300] for r in kb_results.get("handouts", [])],
            }
        except Exception:
            pass
    state._kb_context = kb_context
    # === end KB enrichment ===

    result = await _socratic_coach.run(state)
    result["current_state"] = AgentState.COACH

    # --- Progressive profile update from coaching ---
    confidence = result.get("coach_confidence", state.coach_confidence)
    concept = state.current_concept

    # Normalize concept: LLM may output non-standard IDs
    coach_target = result.get("current_concept", "")
    raw_concept = concept or coach_target or ""
    normalized_concept = _normalize_concept_id(raw_concept)
    if normalized_concept:
        concept = normalized_concept

    if concept and concept.startswith("complex-"):
        profile = dict(state.profile) if state.profile else {}
        existing_mastery = {m["concept_id"]: m for m in profile.get("knowledge_mastery", [])}

        # Map coach_confidence to progressive score (0.1–0.9)
        # Coach confidence reflects the student's current understanding level
        progressive_score = max(0.1, min(0.9, confidence))

        if concept not in existing_mastery:
            existing_mastery[concept] = {
                "concept_id": concept, "score": progressive_score, "confidence": 0.5
            }
        else:
            # Only update if new score is higher (progress is monotonic upward)
            existing_mastery[concept]["score"] = max(
                existing_mastery[concept].get("score", 0), progressive_score
            )
            existing_mastery[concept]["confidence"] = max(
                existing_mastery[concept].get("confidence", 0), 0.5
            )

        profile["knowledge_mastery"] = list(existing_mastery.values())
        result["profile"] = profile
        logger.info(
            f"Profile updated: {concept} → score={existing_mastery[concept]['score']:.2f} "
            f"(coach confidence={confidence:.2f})"
        )

    # Trigger animation when student is struggling with a diagnosed concept
    has_blind_spot = bool(state.blind_spots and any(
        bs.get("concept_id", "").startswith("complex-") for bs in state.blind_spots
    ))
    if confidence < 0.3 and has_blind_spot:
        result["_animation_pending"] = True
        logger.info(f"Animation triggered: confidence={confidence:.2f}")

    return result


async def generate_node(state: TutorState) -> dict[str, Any]:
    result = await _resource_generator.run(state)
    result["current_state"] = AgentState.GENERATE
    # Preserve pending out-of-domain concept for multi-turn confirmation flow
    if "_pending_out_of_domain_concept" not in result:
        result["_pending_out_of_domain_concept"] = ""
    return result


async def assess_node(state: TutorState) -> dict[str, Any]:
    result = await _assessor.run(state)
    result["current_state"] = AgentState.ASSESS
    return result


async def quality_gate_node(state: TutorState) -> dict[str, Any]:
    result = await _quality_gate.run(state)
    result["current_state"] = AgentState.QUALITY_GATE
    return result


async def animation_render_node(state: TutorState) -> dict[str, Any]:
    result = await _animation_generator.run(state)
    result["current_state"] = AgentState.GENERATE  # sequence → generate next
    return result


def respond_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.RESPOND, "_safety_rejected": False}
