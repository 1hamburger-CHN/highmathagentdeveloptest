"""Template selector — rule-based matching + LLM parameter extraction."""

import logging

from app.agents.base import safe_json_parse
from app.animation.base import BaseManimTemplate
from app.animation.templates import ALL_TEMPLATES
from app.animation.schema import AnimationRequest

logger = logging.getLogger("tutor.animation")

PARAM_EXTRACTION_PROMPT = """Extract mathematical parameters for a complex analysis animation.

Concept: {concept_id}
Student's misconception: {wrong_model}
Correct understanding: {correct_model}

Template: {template_name}
Required params schema:
{param_schema}

Output ONLY a JSON object with the parameter values. No explanation, no markdown.
Example: {{"poles": ["i", "-i"], "inside_poles": ["i"], "contour_radius": 2.0}}"""


class TemplateSelector:
    """Two-step selection: concept_id lookup → LLM parameter extraction."""

    def __init__(self, model_router):
        self._router = model_router
        # Build concept_id → template lookup table (step 1 — O(1))
        self._lookup: dict[str, BaseManimTemplate] = {}
        for template_cls in ALL_TEMPLATES:
            template = template_cls()
            for cid in template.concept_ids:
                self._lookup[cid] = template

    def match(self, concept_id: str) -> BaseManimTemplate | None:
        """Step 1: Rule-based concept_id → template match. Returns None if no match."""
        return self._lookup.get(concept_id)

    async def extract_params(
        self, template: BaseManimTemplate, request: AnimationRequest,
    ) -> dict | None:
        """Step 2: LLM extracts template-specific params from diagnosis context.

        Returns the parsed param dict, or None if extraction/validation fails.
        """
        model = self._router.get_model("animation_selector")
        prompt = PARAM_EXTRACTION_PROMPT.format(
            concept_id=request.concept_id,
            wrong_model=request.wrong_model,
            correct_model=request.correct_model,
            template_name=template.template_name,
            param_schema=self._describe_params(template),
        )
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(2):
            try:
                response = await model.ainvoke(messages)
                params = safe_json_parse(response.content)
                if isinstance(params, dict) and template.validate(params):
                    return params
                logger.warning(
                    f"Param extraction attempt {attempt + 1} failed: "
                    f"validate={isinstance(params, dict) and template.validate(params)}"
                )
            except Exception as exc:
                logger.warning(f"Param extraction attempt {attempt + 1} error: {exc}")

        return None

    def _describe_params(self, template: BaseManimTemplate) -> str:
        """Build a human-readable param schema from the template's validate method."""
        # Use a representative set of keys from a sample call
        hints = {
            "ResidueTheorem": "poles: list[str] — all singularities (e.g. [\"i\", \"-i\"])\n"
                              "inside_poles: list[str] — poles inside the contour\n"
                              "contour_radius: float — radius of the circular contour",
            "ConformalMapping": "function: str — complex function (e.g. \"z**2\", \"exp(z)\")\n"
                                "domain: str — description of the domain region",
            "ContourIntegration": "contour: str — \"circle\" or \"semicircle\"\n"
                                   "integrand: str — the integrand function\n"
                                   "radius: float — contour radius",
            "CREquations": "function: str — complex function (e.g. \"z**2\", \"z**3\")\n"
                           "point: str — evaluation point (e.g. \"1+i\", \"0\")",
            "TaylorSeries": "function: str — analytic function (e.g. \"exp(z)\", \"sin(z)\")\n"
                           "terms: int — number of Taylor terms (default 5)",
            "LaurentSeries": "function: str — complex function (e.g. \"1/(z*(z-1))\", \"exp(1/z)\")\n"
                             "inner_radius: float — radius of inner exclusion circle (default 0.5)\n"
                             "outer_radius: float — radius of outer boundary circle (default 2.0)",
            "PoleClassification": "singularities: list[dict] — list of singularity objects, each with:\n"
                                  "  type: str — \"removable\" | \"pole\" | \"essential\"\n"
                                  "  point: str — location (e.g. \"0\")\n"
                                  "  label: str — description (e.g. \"极点: 1/z\")",
        }
        return hints.get(template.template_name, "params: dict — template-specific parameters")
