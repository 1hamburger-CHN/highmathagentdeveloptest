"""LangGraph Supervisor state graph for the Socratic Tutor system."""
import logging
from typing import Any

from langgraph.graph import END, StateGraph

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

_profile_builder = ProfileBuilderAgent(_router)
_diagnostician = DiagnosticianAgent(_router)
_socratic_coach = SocraticCoachAgent(_router)
_resource_generator = ResourceGeneratorAgent(_router, _retriever)
_assessor = AssessorAgent(_router)
_quality_gate = QualityGateAgent(_router)


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
        {"generate": "generate", "assess": "assess"},
    )
    workflow.add_edge("generate", "respond")
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
    # Decline/refusal → respond directly
    if getattr(state, "_respond_directly", False):
        return "respond"
    # Resource request → skip everything, go straight to generate
    if getattr(state, "_is_resource_request", False):
        return "generate"
    # Already have profile → diagnose → coach
    if state.profile and state.profile.get("knowledge_mastery"):
        return "diagnose"
    # Direct math question → skip both profile AND diagnose, straight to coach
    if getattr(state, "_is_direct_question", False):
        return "coach"
    return "build_profile"


def route_coach(state: TutorState) -> str:
    return "assess" if state.coach_confidence > 0.7 else "generate"


def route_quality(state: TutorState) -> str:
    return "regenerate" if state.quality_retries < 2 else "respond"


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
    is_resource_request = _is_resource_request(user_msg)

    # Out-of-domain direct question → redirect to generate (don't do Socratic coaching)
    if is_direct_question and not is_resource_request:
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

    return {
        "current_state": AgentState.PROFILE_CHECK,
        "_has_profile": has_profile,
        "_is_direct_question": is_direct_question,
        "_is_resource_request": is_resource_request,
        "_pending_out_of_domain_concept": "",
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


def _is_resource_request(text: str) -> bool:
    """Check if user is explicitly asking for a learning resource."""
    resource_keywords = [
        "生成", "帮我做", "帮我画", "帮我写", "帮我整理", "给我",
        "思维导图", "脑图", "导图", "知识图谱",
        "讲义", "课件", "教程", "笔记", "总结", "归纳",
        "练习题", "习题", "题目", "出题", "试卷",
        "阅读材料", "拓展", "资料",
        "介绍", "概述", "概览", "入门",
    ]
    return any(kw in text for kw in resource_keywords)


def _is_out_of_domain_confirmation(text: str) -> bool:
    """Detect user confirming they want out-of-domain content generated."""
    keywords = [
        "好的", "可以", "行", "没问题", "好", "嗯", "是", "对",
        "要", "需要", "搜", "搜索", "帮我搜", "帮我搜索",
        "帮我生成", "生成吧", "做吧", "搞", "ok", "yes", "yeah",
        "确认", "是的", "对的", "来吧", "搞起",
    ]
    return any(kw in text for kw in keywords)


def _is_out_of_domain_decline(text: str) -> bool:
    """Detect user declining out-of-domain generation."""
    keywords = [
        "不用", "不要", "算了", "不了", "取消", "换一个",
        "不需要", "不用了", "别", "no",
    ]
    return any(kw in text for kw in keywords)


def _extract_concept_from_question(text: str) -> str:
    """Extract the likely math concept from a question."""
    import re
    concept = re.sub(
        r"^(什么是|啥是|什么叫|什么是|解释一下|讲讲|请问|问一下|"
        r"怎么理解|如何理解|怎么证|证明一下|帮我|请|帮忙|给我)",
        "", text,
    )
    concept = re.sub(r"[?？。！!，,：:]+$", "", concept)
    return concept.strip()


async def build_profile_node(state: TutorState) -> dict[str, Any]:
    result = await _profile_builder.run(state)
    result["current_state"] = AgentState.BUILD_PROFILE
    # Strip messages — profile builder works silently in background
    result.pop("messages", None)
    return result


async def diagnose_node(state: TutorState) -> dict[str, Any]:
    result = await _diagnostician.run(state)
    result["current_state"] = AgentState.DIAGNOSE
    # Strip messages — diagnostician works silently in background
    result.pop("messages", None)
    return result


async def coach_node(state: TutorState) -> dict[str, Any]:
    result = await _socratic_coach.run(state)
    result["current_state"] = AgentState.COACH
    return result


async def generate_node(state: TutorState) -> dict[str, Any]:
    result = await _resource_generator.run(state)
    result["current_state"] = AgentState.GENERATE
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


def respond_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.RESPOND, "_safety_rejected": False}
