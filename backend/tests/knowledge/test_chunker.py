import pytest
from app.knowledge.chunker import latex_aware_split


class TestLatexAwareSplit:
    def test_preserves_latex_formula(self):
        text = "设 $z = x + iy$，其中 $i^2 = -1$。复数的模定义为 $|z| = \\sqrt{x^2 + y^2}$。"
        chunks = latex_aware_split(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 1
        assert "$|z| = \\sqrt{x^2 + y^2}$" in "".join(chunks)

    def test_does_not_split_inside_dollar(self):
        text = "a " * 30 + "$\\frac{a}{b}$" + " b " * 30
        chunks = latex_aware_split(text, chunk_size=80, overlap=10)
        for chunk in chunks:
            if "$" in chunk:
                assert chunk.count("$") % 2 == 0, f"Unbalanced $ in chunk"

    def test_empty_input(self):
        assert latex_aware_split("", chunk_size=100) == []

    def test_chinese_math_mixed(self):
        text = "柯西积分公式 $\\oint_C \\frac{f(z)}{z-z_0}dz = 2\\pi i f(z_0)$"
        chunks = latex_aware_split(text, chunk_size=80, overlap=20)
        assert len(chunks) >= 1
