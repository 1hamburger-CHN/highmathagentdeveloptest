"""LangGraph Supervisor state graph for the Socratic Tutor system."""
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

# Shared model router (initialized once at graph build time)
_router = ModelRouter()

_profile_builder = ProfileBuilderAgent(_router)
_diagnostician = DiagnosticianAgent(_router)
_socratic_coach = SocraticCoachAgent(_router)
_resource_generator = ResourceGeneratorAgent(_router)
_assessor = AssessorAgent(_router)
_quality_gate = QualityGateAgent(_router)


def build_tutor_graph() -> StateGraph:
    workflow = StateGraph(TutorState)

    workflow.add_node("profile_check", profile_check_node)
    workflow.add_node("build_profile", build_profile_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("coach", coach_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("assess", assess_node)
    workflow.add_node("quality_gate", quality_gate_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("profile_check")

    workflow.add_conditional_edges(
        "profile_check",
        route_profile_check,
        {"build_profile": "build_profile", "diagnose": "diagnose"},
    )
    workflow.add_edge("build_profile", "diagnose")
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

def route_profile_check(state: TutorState) -> str:
    if state.profile and state.profile.get("knowledge_mastery"):
        return "diagnose"
    return "build_profile"


def route_coach(state: TutorState) -> str:
    return "assess" if state.coach_confidence > 0.7 else "generate"


def route_quality(state: TutorState) -> str:
    return "regenerate" if state.quality_retries < 2 else "respond"


# --- Nodes ---

def profile_check_node(state: TutorState) -> dict[str, Any]:
    has_profile = bool(state.profile and state.profile.get("knowledge_mastery"))
    return {"current_state": AgentState.PROFILE_CHECK, "_has_profile": has_profile}


async def build_profile_node(state: TutorState) -> dict[str, Any]:
    result = await _profile_builder.run(state)
    result["current_state"] = AgentState.BUILD_PROFILE
    return result


async def diagnose_node(state: TutorState) -> dict[str, Any]:
    result = await _diagnostician.run(state)
    result["current_state"] = AgentState.DIAGNOSE
    return result


async def coach_node(state: TutorState) -> dict[str, Any]:
    result = await _socratic_coach.run(state)
    result["current_state"] = AgentState.COACH
    return result


async def generate_node(state: TutorState) -> dict[str, Any]:
    result = await _resource_generator.run(state)
    result["current_state"] = AgentState.GENERATE
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
    return {"current_state": AgentState.RESPOND}
