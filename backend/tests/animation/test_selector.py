"""Tests for TemplateSelector."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.animation.selector import TemplateSelector
from app.animation.schema import AnimationRequest
from app.animation.templates import ALL_TEMPLATES


class TestTemplateSelector:
    def test_match_exact_concept_id(self):
        selector = TemplateSelector(MagicMock())
        # complex-6.2 is unique to ResidueTheorem (complex-6.1 is also claimed by PoleClassification)
        template = selector.match("complex-6.2")
        assert template is not None
        assert template.template_name == "ResidueTheorem"

    def test_match_unknown_concept_id(self):
        selector = TemplateSelector(MagicMock())
        template = selector.match("nonexistent-id")
        assert template is None

    def test_all_template_concept_ids_registered(self):
        selector = TemplateSelector(MagicMock())
        for template_cls in ALL_TEMPLATES:
            template = template_cls()
            for cid in template.concept_ids:
                matched = selector.match(cid)
                assert matched is not None, f"concept_id {cid} not registered for {template.template_name}"

    @pytest.mark.asyncio
    async def test_extract_params_success(self):
        router = MagicMock()
        model = AsyncMock()
        model.ainvoke.return_value = MagicMock(
            content='{"poles": ["i"], "inside_poles": ["i"], "contour_radius": 2.0}'
        )
        router.get_model.return_value = model

        selector = TemplateSelector(router)
        template = selector.match("complex-6.2")
        request = AnimationRequest(concept_id="complex-6.2", wrong_model="test")

        params = await selector.extract_params(template, request)
        assert params is not None
        assert params["poles"] == ["i"]

    @pytest.mark.asyncio
    async def test_extract_params_invalid_json_fallback(self):
        router = MagicMock()
        model = AsyncMock()
        # First attempt returns invalid JSON, second returns valid
        model.ainvoke.side_effect = [
            MagicMock(content='not json at all {broken'),
            MagicMock(content='{"function": "z**2"}'),
        ]
        router.get_model.return_value = model

        selector = TemplateSelector(router)
        template = selector.match("complex-7.1")  # ConformalMapping
        request = AnimationRequest(concept_id="complex-7.1")

        params = await selector.extract_params(template, request)
        assert params is not None
        assert params["function"] == "z**2"

    def test_new_templates_registered(self):
        from app.animation.templates import ALL_TEMPLATES
        template_names = {t().template_name for t in ALL_TEMPLATES}
        expected = {"CREquations", "TaylorSeries", "LaurentSeries", "PoleClassification",
                    "ResidueTheorem", "ConformalMapping", "ContourIntegration"}
        missing = expected - template_names
        assert not missing, f"Missing templates: {missing}"
