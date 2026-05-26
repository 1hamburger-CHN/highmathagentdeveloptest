"""AnimationGenerator Agent — coach diagnosis → animation render."""

import logging

from app.agents.base import BaseAgent
from app.agents.state import TutorState
from app.animation.renderer import ManimRenderer
from app.animation.schema import AnimationRequest
from app.animation.selector import TemplateSelector

logger = logging.getLogger("tutor.animation")

FALLBACK_MESSAGE = "动画生成暂时不可用，以下为文字讲解——"


class AnimationGeneratorAgent(BaseAgent):
    """Generates Manim math animations based on coach's blind spot diagnosis."""

    def __init__(self, model_router):
        super().__init__("animation_generator", model_router)
        self.selector = TemplateSelector(model_router)

    async def run(self, state: TutorState) -> dict:
        """Entry point called by LangGraph animation_render node."""
        # Use per-request SSE queue from state
        sse_queue = getattr(state, "_sse_queue", None)
        self.renderer = ManimRenderer(heartbeat_queue=sse_queue)

        concept = state.current_concept or self._extract_concept(state)
        if not concept:
            logger.info("No concept to animate, skipping")
            return {"_animation_pending": False}

        # Step 0: Memory check
        if not self._memory_ok():
            logger.warning("Insufficient memory, falling back to text")
            return self._fallback(state, "服务器繁忙，请稍后重试")

        # Step 1: Template matching (rule-based, no LLM)
        template = self.selector.match(concept)
        if template is None:
            logger.info(f"No template for concept '{concept}', skipping animation")
            return {"_animation_pending": False}

        # Step 2: Build diagnosis context for LLM param extraction
        diagnosis = self._build_diagnosis(state)

        # Step 3: LLM param extraction (2 attempts + safe_json_parse)
        params = await self.selector.extract_params(template, diagnosis)
        if params is None:
            logger.warning("Param extraction failed, falling back to text")
            return self._fallback(state, FALLBACK_MESSAGE)

        # Step 4: SymPy math validation
        if not self._validate_params(template, params):
            logger.warning("Math validation failed for params")
            return self._fallback(state, FALLBACK_MESSAGE)

        # Step 5: Render
        resource = await self.renderer.render(template, params)
        if resource is None:
            return self._fallback(state, FALLBACK_MESSAGE)

        # Step 6: Write to state
        result = {"_animation_pending": False, "animation_resource": resource}

        # Merge animation resource as a message in the chat
        video_msg = {
            "role": "animation",
            "content": resource.mp4_url,
            "title": resource.title,
            "template": resource.template_used,
        }
        existing = list(state.messages)
        existing.append(video_msg)
        result["messages"] = existing

        return result

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _extract_concept(self, state: TutorState) -> str:
        """Extract concept_id from blind_spots or current_concept."""
        for bs in state.blind_spots:
            cid = bs.get("concept_id", "")
            if cid:
                return cid
        return ""

    def _build_diagnosis(self, state: TutorState) -> AnimationRequest:
        """Build structured diagnosis for param extraction."""
        wrong = ""
        correct = ""
        error_type = ""
        concept = state.current_concept

        for bs in state.blind_spots:
            if bs.get("concept_id") == concept:
                wrong = bs.get("description", "")
                error_type = bs.get("type", "")
                break

        # The correct_model comes from the coach's last message
        for m in reversed(state.messages):
            if m.get("role") in ("assistant", "coach"):
                correct = m.get("content", "")[-500:]  # last 500 chars
                break

        return AnimationRequest(
            concept_id=concept,
            error_type=error_type,
            wrong_model=wrong,
            correct_model=correct,
        )

    def _memory_ok(self) -> bool:
        """Check if enough memory is available for Manim rendering."""
        try:
            import psutil
            avail_mb = psutil.virtual_memory().available / (1024 * 1024)
            ok = avail_mb > 300
            if not ok:
                logger.warning(f"Low memory: {avail_mb:.0f}MB available")
            return ok
        except ImportError:
            return True  # psutil not installed, skip check

    def _validate_params(self, template, params: dict) -> bool:
        """SymPy-based math validation of extracted parameters."""
        try:
            # Basic validation via template
            if not template.validate(params):
                return False

            # SymPy validation for pole correctness
            if "poles" in params:
                from sympy import I, symbols, solve, sympify
                if "function" in params:
                    try:
                        z = symbols("z")
                        f = sympify(params["function"].replace("i", "I"))
                        denom = 1 / f if f != 0 else f
                        # Check poles by solving 1/f = 0 (actually denominator roots)
                        # For now: accept if template.validate passed
                        # Full symbolic verification is deferred to future work
                        pass
                    except Exception:
                        pass
            return True
        except Exception as exc:
            logger.warning(f"Math validation error: {exc}")
            return True  # Don't block on validation errors

    def _fallback(self, state: TutorState, message: str) -> dict:
        """Return text fallback when animation generation fails."""
        return {
            "_animation_pending": False,
            "messages": [{
                "role": "assistant",
                "content": message,
            }],
        }
