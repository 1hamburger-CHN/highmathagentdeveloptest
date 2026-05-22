from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState, TutorState


def build_tutor_graph() -> StateGraph:
    """Build the LangGraph Supervisor state graph."""
    workflow = StateGraph(TutorState)

    # Nodes — each agent is a node
    workflow.add_node("profile_check", profile_check_node)
    workflow.add_node("build_profile", build_profile_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("coach", coach_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("assess", assess_node)
    workflow.add_node("quality_gate", quality_gate_node)
    workflow.add_node("respond", respond_node)

    # Entry
    workflow.set_entry_point("profile_check")

    # Edges — state machine transitions
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
    workflow.add_edge("generate", "coach")
    workflow.add_edge("assess", "quality_gate")
    workflow.add_conditional_edges(
        "quality_gate",
        route_quality,
        {"regenerate": "generate", "respond": "respond"},
    )
    workflow.add_edge("respond", END)

    return workflow.compile()


# --- Node implementations (stubs) ---

def profile_check_node(state: TutorState) -> dict[str, Any]:
    has_profile = state.profile is not None
    return {"current_state": AgentState.PROFILE_CHECK, "profile": state.profile}


def route_profile_check(state: TutorState) -> str:
    return "diagnose" if state.profile else "build_profile"


def build_profile_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.BUILD_PROFILE}


def diagnose_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.DIAGNOSE}


def coach_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.COACH}


def route_coach(state: TutorState) -> str:
    return "assess" if state.coach_confidence > 0.7 else "generate"


def generate_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.GENERATE}


def assess_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.ASSESS}


def quality_gate_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.QUALITY_GATE}


def route_quality(state: TutorState) -> str:
    if state.quality_retries < 2:
        return "respond"
    return "respond"


def respond_node(state: TutorState) -> dict[str, Any]:
    return {"current_state": AgentState.RESPOND}
