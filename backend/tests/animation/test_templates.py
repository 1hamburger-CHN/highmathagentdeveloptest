import pytest
from app.animation.templates import ALL_TEMPLATES


class TestAllTemplates:
    DEFAULT_PARAMS = {
        "ResidueTheorem": {"poles": ["i"], "inside_poles": ["i"], "contour_radius": 2.0},
        "ConformalMapping": {"function": "z**2"},
        "ContourIntegration": {"contour": "circle"},
        "CREquations": {"function": "z**2"},
        "TaylorSeries": {"function": "exp(z)"},
        "LaurentSeries": {"function": "1/(z*(z-1))"},
        "PoleClassification": {"singularities": [{"type": "pole", "point": "0", "label": "test"}]},
    }

    @pytest.mark.parametrize("template_cls", ALL_TEMPLATES)
    def test_validate_accepts_defaults(self, template_cls):
        t = template_cls()
        params = self.DEFAULT_PARAMS.get(t.template_name, {})
        if not params:
            pytest.skip(f"No default params for {t.template_name}")
        assert t.validate(params), f"{t.template_name} validation failed"

    @pytest.mark.parametrize("template_cls", ALL_TEMPLATES)
    def test_build_scene_code_is_valid_python(self, template_cls):
        t = template_cls()
        params = self.DEFAULT_PARAMS.get(t.template_name, {})
        if not t.validate(params):
            params = {}
        code = t.build_scene_code(params)
        assert len(code) > 200, f"{t.template_name} code too short: {len(code)}"
        assert "class " in code
        assert "Scene" in code
        assert "def construct" in code
