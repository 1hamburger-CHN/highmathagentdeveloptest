from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langgraph.graph import StateGraph


class AgentState(str, Enum):
    INIT = "init"
    PROFILE_CHECK = "profile_check"
    BUILD_PROFILE = "build_profile"
    DIAGNOSE = "diagnose"
    COACH = "coach"
    GENERATE = "generate"
    ASSESS = "assess"
    QUALITY_GATE = "quality_gate"
    REGENERATE = "regenerate"
    RESPOND = "respond"


@dataclass
class TutorState:
    session_id: str = ""
    user_id: str = ""
    current_state: AgentState = AgentState.INIT
    messages: list[dict] = field(default_factory=list)
    profile: dict | None = None
    blind_spots: list[dict] = field(default_factory=list)
    current_concept: str = ""
    coach_level: int = 1  # L1/L2/L3
    coach_confidence: float = 0.5
    generated_resources: list[dict] = field(default_factory=list)
    assessment_result: dict | None = None
    quality_retries: int = 0
    error: str | None = None
