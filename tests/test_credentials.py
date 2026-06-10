"""
Testes de leitura defensiva de credenciais.

Escritos em unittest (stdlib) para rodarem sem dependencia extra
(`python -m unittest`); tambem sao coletaveis pelo pytest.

Nunca usam tokens reais - apenas fixtures fake gravadas em tmp dir.
"""

import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from core.credentials import read_claude_credentials, read_codex_credentials
from core.models import AuthState


class CredentialsTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> Path:
        path = self.tmp / name
        path.write_text(content, encoding="utf-8")
        return path


class ReadClaudeCredentialsTests(CredentialsTestBase):
    def test_missing_file(self):
        result = read_claude_credentials(self.tmp / "nope.json")
        self.assertEqual(result.state, AuthState.MISSING)
        self.assertIsNone(result.token)

    def test_invalid_json(self):
        path = self._write("c.json", "{not valid json")
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.INVALID_FILE)

    def test_missing_token_field(self):
        path = self._write("c.json", json.dumps({"foo": "bar"}))
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.INVALID_FILE)

    def test_token_at_root(self):
        path = self._write("c.json", json.dumps({"access_token": "abc123"}))
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.READY)
        self.assertEqual(result.token, "abc123")

    def test_token_nested_oauth_block(self):
        path = self._write(
            "c.json",
            json.dumps({"claudeAiOauth": {"accessToken": "xyz"}}),
        )
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.READY)
        self.assertEqual(result.token, "xyz")

    def test_expired_token(self):
        past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        path = self._write(
            "c.json",
            json.dumps({"access_token": "abc", "expires_at": past.isoformat()}),
        )
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.EXPIRED)
        self.assertIsNone(result.token)  # nao expoe token expirado

    def test_future_epoch_ms_is_ready(self):
        future_ms = int((time.time() + 3600) * 1000)
        path = self._write(
            "c.json",
            json.dumps({"access_token": "abc", "expires_at": future_ms}),
        )
        result = read_claude_credentials(path)
        self.assertEqual(result.state, AuthState.READY)


class ReadCodexCredentialsTests(CredentialsTestBase):
    def test_missing_file(self):
        result = read_codex_credentials(self.tmp / "nope.json")
        self.assertEqual(result.state, AuthState.MISSING)

    def test_token_nested_tokens_block(self):
        path = self._write(
            "a.json",
            json.dumps({"tokens": {"access_token": "tok"}}),
        )
        result = read_codex_credentials(path)
        self.assertEqual(result.state, AuthState.READY)
        self.assertEqual(result.token, "tok")

    def test_openai_api_key_is_not_accepted(self):
        # Regressao: OPENAI_API_KEY tem escopo diferente do token OAuth do Codex
        # e nao deve ser enviada como Bearer ao endpoint wham/usage.
        path = self._write("a.json", json.dumps({"OPENAI_API_KEY": "sk-fake"}))
        result = read_codex_credentials(path)
        self.assertEqual(result.state, AuthState.INVALID_FILE)
        self.assertIsNone(result.token)

    def test_non_object_json(self):
        path = self._write("a.json", json.dumps([1, 2, 3]))
        result = read_codex_credentials(path)
        self.assertEqual(result.state, AuthState.INVALID_FILE)


if __name__ == "__main__":
    unittest.main()
