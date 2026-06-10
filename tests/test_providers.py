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
    def test_used_and_limit(self):
        snap = parse_claude_usage({"used": 120, "limit": 500})
        self.assertEqual(snap.state, UsageState.OK)
        self.assertEqual(snap.used, 120.0)
        self.assertEqual(snap.limit, 500.0)
        self.assertEqual(snap.percent, 24.0)  # derivado

    def test_explicit_percent_wins(self):
        snap = parse_claude_usage({"used": 1, "limit": 4, "percent": 30})
        self.assertEqual(snap.percent, 30.0)

    def test_alternate_field_names(self):
        snap = parse_claude_usage({"usage": 10, "quota": 100})
        self.assertEqual(snap.used, 10.0)
        self.assertEqual(snap.limit, 100.0)

    def test_unexpected_payload_is_parse_error(self):
        snap = parse_claude_usage({"unrelated": "data"})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)
        self.assertIsNotNone(snap.message)

    def test_reset_at_epoch(self):
        snap = parse_claude_usage({"used": 1, "limit": 2, "reset_at": 1893456000})
        self.assertIsNotNone(snap.reset_at)


class ParseCodexUsageTests(unittest.TestCase):
    def test_used_tokens_and_hard_limit(self):
        snap = parse_codex_usage({"used_tokens": 200, "hard_limit": 1000})
        self.assertEqual(snap.state, UsageState.OK)
        self.assertEqual(snap.used, 200.0)
        self.assertEqual(snap.limit, 1000.0)
        self.assertEqual(snap.percent, 20.0)

    def test_unexpected_payload_is_parse_error(self):
        snap = parse_codex_usage({})
        self.assertEqual(snap.state, UsageState.PARSE_ERROR)

    def test_bool_is_not_number(self):
        # Garante que True/False nao sejam confundidos com numeros.
        snap = parse_codex_usage({"used": True, "limit": 100})
        self.assertIsNone(snap.used)
        self.assertEqual(snap.limit, 100.0)


if __name__ == "__main__":
    unittest.main()
