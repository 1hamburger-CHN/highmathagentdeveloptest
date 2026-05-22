"""Orchestrator Agent — LangGraph Supervisor entry point."""
from app.agents.base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """Entry point for the tutoring pipeline. Delegates to the LangGraph graph."""

    def __init__(self, model_router):
        super().__init__("orchestrator", model_router)

    async def run(self, state: dict) -> dict:
        # The orchestrator itself is thin — the LangGraph handles routing.
        # This is the initial greeting / intent classification step.
        return state
