from app.agents.base import BaseAgent


class ResourceGeneratorAgent(BaseAgent):
    """Unified resource generation — lecture notes, exercises, mind maps, reading."""

    def __init__(self, model_router):
        super().__init__("resource_generator", model_router)

    async def run(self, state: dict) -> dict:
        return state
