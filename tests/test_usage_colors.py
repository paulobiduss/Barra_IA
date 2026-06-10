"""
Testes do mapeamento percentual -> cor da barra (ui/usage_colors).

Camada pura: usa QColor sem QApplication. Cobre fronteiras de cada faixa e
clamps de valores fora de [0, 100].
"""

import unittest

from ui.usage_colors import (
    GREEN,
    ORANGE,
    RED,
    YELLOW,
    color_for_percent,
)


def _hex(name: str) -> str:
    """Compara cores via string hex em uppercase, ignorando alpha."""
    return name.upper()


class ColorForPercentTests(unittest.TestCase):
    def assertColor(self, pct, expected_hex):  # noqa: N802
        color = color_for_percent(pct)
        self.assertEqual(color.name().upper(), _hex(expected_hex))

    def test_none_falls_back_to_green(self):
        self.assertColor(None, GREEN)

    def test_zero_is_green(self):
        self.assertColor(0, GREEN)

    def test_just_below_yellow_is_green(self):
        self.assertColor(49.9, GREEN)

    def test_yellow_threshold(self):
        self.assertColor(50, YELLOW)

    def test_mid_yellow(self):
        self.assertColor(65, YELLOW)

    def test_just_below_orange_is_yellow(self):
        self.assertColor(79.9, YELLOW)

    def test_orange_threshold(self):
        self.assertColor(80, ORANGE)

    def test_just_below_red_is_orange(self):
        self.assertColor(94.9, ORANGE)

    def test_red_threshold(self):
        self.assertColor(95, RED)

    def test_one_hundred_is_red(self):
        self.assertColor(100, RED)

    def test_above_one_hundred_clamps_to_red(self):
        self.assertColor(150, RED)

    def test_negative_clamps_to_green(self):
        self.assertColor(-5, GREEN)


if __name__ == "__main__":
    unittest.main()
