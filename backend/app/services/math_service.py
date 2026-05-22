import sympy as sp
from sympy.parsing.latex import parse_latex


class MathService:
    """SymPy-based math validation."""

    @staticmethod
    def verify_expression(latex_expr: str) -> dict:
        """Parse and simplify a LaTeX expression. Returns {valid, simplified, error}."""
        try:
            expr = parse_latex(latex_expr)
            simplified = sp.simplify(expr)
            return {"valid": True, "simplified": sp.latex(simplified), "error": None}
        except Exception as e:
            return {"valid": False, "simplified": None, "error": str(e)}

    @staticmethod
    def verify_equality(latex_a: str, latex_b: str) -> dict:
        """Check if two LaTeX expressions are equivalent."""
        try:
            a = parse_latex(latex_a)
            b = parse_latex(latex_b)
            eq = sp.simplify(a - b) == 0
            return {"equivalent": eq, "error": None}
        except Exception as e:
            return {"equivalent": False, "error": str(e)}

    @staticmethod
    def evaluate_limit(latex_expr: str, var: str = "x", point: str = "0") -> dict:
        """Evaluate a limit expression symbolically."""
        try:
            expr = parse_latex(latex_expr)
            x = sp.Symbol(var)
            result = sp.limit(expr, x, sp.sympify(point))
            return {"valid": True, "result": sp.latex(result), "error": None}
        except Exception as e:
            return {"valid": False, "result": None, "error": str(e)}
