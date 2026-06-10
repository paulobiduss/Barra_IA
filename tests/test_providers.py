"""
Testes de parsing dos payloads de uso (sem rede - apenas os parsers puros).

Os endpoints sao nao documentados; estes testes fixam o comportamento do
parser tolerante para os formatos que assumimos, incluindo o caso de payload
inesperado (-> PARSE_ERROR).
"""

import unittest

from core.models import UsageState
from core.providers.claude_provider import parse_claude_usage
from core.providers.codex_provider import parse_codex_usage


class ParseClaudeUsageTests(unittest.TestCase):
    def test_five_hour_utilization(self):
        snap = parse_claude_usage(
            {"five_hour": {"utilization": 65.0, "resets_at": "2026-06-10T16:50:00+00:00"}}
        )
        self.assertEqual(snap.state, UsageState.OK)
        self.assertEqual(snap.percent, 65.0)
        self.assertIsNotNone(snap.reset_at)

    def test_seven_day_becomes_message(self):
        snap = parse_claude_usage(
            {
                "five_hour": {"utilization": 65.0, "resets_at": "2026-06-10T16:50:00+00:00"},
                "seven_day": {"utilization": 7.0, "resets_at": "2026-06-12T15:00:00+00:00"},
            }
        )
        self.assertEqual(snap.message, "(semana: 7%)")

    def test_unexpected_payload_is_parse_error(self):
        snap = parse_claude_usage({"unrelated": "data"})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)
        self.assertIsNotNone(snap.message)

    def test_missing_utilization_is_parse_error(self):
        snap = parse_claude_usage({"five_hour": {"resets_at": "2026-06-10T16:50:00+00:00"}})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)

    def test_bool_is_not_number(self):
        snap = parse_claude_usage({"five_hour": {"utilization": True}})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)


class ParseCodexUsageTests(unittest.TestCase):
    def test_primary_window_used_percent(self):
        snap = parse_codex_usage(
            {"rate_limit": {"primary_window": {"used_percent": 12, "reset_at": 1781113799}}}
        )
        self.assertEqual(snap.state, UsageState.OK)
        self.assertEqual(snap.percent, 12.0)
        self.assertIsNotNone(snap.reset_at)

    def test_secondary_window_becomes_message(self):
        snap = parse_codex_usage(
            {
                "rate_limit": {
                    "primary_window": {"used_percent": 12, "reset_at": 1781113799},
                    "secondary_window": {"used_percent": 2, "reset_at": 1781264790},
                }
            }
        )
        self.assertEqual(snap.message, "(semana: 2%)")

    def test_unexpected_payload_is_parse_error(self):
        snap = parse_codex_usage({})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)

    def test_missing_used_percent_is_parse_error(self):
        snap = parse_codex_usage({"rate_limit": {"primary_window": {"reset_at": 1781113799}}})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)

    def test_bool_is_not_number(self):
        # Garante que True/False nao sejam confundidos com numeros.
        snap = parse_codex_usage(
            {"rate_limit": {"primary_window": {"used_percent": True}}}
        )
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)


if __name__ == "__main__":
    unittest.main()
