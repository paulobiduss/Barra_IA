"""
Testes dos formatters (texto de tooltip/menu).
"""

import unittest
from datetime import datetime, timedelta, timezone

from core.models import UsageSnapshot, UsageState
from ui.formatters import _fmt_bar, format_tooltip, format_usage_line


def _ok(**kw) -> UsageSnapshot:
    base = dict(provider="Claude", state=UsageState.OK)
    base.update(kw)
    return UsageSnapshot(**base)


class FormatUsageLineTests(unittest.TestCase):
    def test_used_limit_percent(self):
        line = format_usage_line(_ok(used=120, limit=500, percent=24))
        # 24% em barra de 5 = 1 bloco cheio.
        self.assertEqual(line, "Claude: [█░░░░] 120/500 (24%)")

    def test_reset_in_hours(self):
        reset = datetime.now(tz=timezone.utc) + timedelta(hours=3, minutes=5)
        line = format_usage_line(_ok(used=1, limit=2, percent=50, reset_at=reset))
        self.assertIn("reset em 3h", line)

    def test_error_state_shows_message(self):
        snap = UsageSnapshot(
            provider="Codex",
            state=UsageState.NETWORK_ERROR,
            message="sem conexao",
        )
        self.assertEqual(format_usage_line(snap), "Codex: sem conexao")

    def test_ok_with_cache_note_appended(self):
        line = format_usage_line(_ok(used=10, limit=20, percent=50, message="(cache - sem conexao)"))
        self.assertIn("(cache - sem conexao)", line)
        self.assertIn("10/20", line)

    def test_float_formatting(self):
        line = format_usage_line(_ok(used=1.5, limit=3, percent=50))
        self.assertIn("1.5/3", line)


class FormatBarTests(unittest.TestCase):
    def test_zero_percent_all_empty(self):
        self.assertEqual(_fmt_bar(0), "[░░░░░]")

    def test_full_percent_all_filled(self):
        self.assertEqual(_fmt_bar(100), "[█████]")

    def test_half_percent(self):
        # 50% em barra de 5 = 2.5 blocos; banker's rounding do Python arredonda 2.5 -> 2.
        self.assertEqual(_fmt_bar(50), "[██░░░]")

    def test_clamps_above_100(self):
        self.assertEqual(_fmt_bar(150), "[█████]")

    def test_clamps_below_zero(self):
        self.assertEqual(_fmt_bar(-10), "[░░░░░]")

    def test_custom_width(self):
        self.assertEqual(_fmt_bar(50, width=4), "[██░░]")


class FormatTooltipTests(unittest.TestCase):
    def test_multiline_with_title(self):
        a = _ok(provider="Claude", used=1, limit=2, percent=50)
        b = _ok(provider="Codex", used=3, limit=4, percent=75)
        tooltip = format_tooltip([a, b])
        lines = tooltip.split("\n")
        self.assertEqual(lines[0], "Barra de Uso de IA")
        self.assertTrue(lines[1].startswith("Claude:"))
        self.assertTrue(lines[2].startswith("Codex:"))


if __name__ == "__main__":
    unittest.main()
