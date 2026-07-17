"""Tests for MathService — SymPy expression validation."""
import pytest
from app.services.math_service import MathService


class TestMathService:
    def test_verify_valid_latex_expression(self):
        result = MathService.verify_expression("x^2 + 2x + 1")
        assert result["valid"] is True
        assert result["error"] is None
        assert result["simplified"] is not None

    def test_verify_invalid_latex_expression(self):
        # Use a truly malformed LaTeX string that SymPy cannot parse
        result = MathService.verify_expression("\\frac{x")
        assert result["valid"] is False
        assert result["error"] is not None

    def test_verify_equality_equivalent(self):
        result = MathService.verify_equality("x^2 + 2x + 1", "(x+1)^2")
        assert result["equivalent"] is True
        assert result["error"] is None

    def test_verify_equality_not_equivalent(self):
        result = MathService.verify_equality("x^2", "x^3")
        assert result["equivalent"] is False
        assert result["error"] is None

    def test_evaluate_simple_limit(self):
        result = MathService.evaluate_limit("\\frac{\\sin x}{x}", var="x", point="0")
        assert result["valid"] is True
        assert result["error"] is None
        # lim_{x->0} sin(x)/x = 1
        assert "1" in result["result"]
