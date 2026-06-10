"""
Testes de collect_usage / collect_all (orquestracao credencial + provider).

Cobre a parte bloqueante que passou a rodar em worker thread: traducao de
estados de auth e isolamento de falha entre jobs.
"""

import unittest

from core.models import AuthResult, AuthState, UsageSnapshot, UsageState
from core.usage_service import collect_all, collect_usage


class _FakeProvider:
    def __init__(self, name: str, *, raises: bool = False):
        self.name = name
        self._raises = raises

    def fetch(self, token: str) -> UsageSnapshot:
        if self._raises:
            raise RuntimeError("boom")
        return UsageSnapshot(provider=self.name, state=UsageState.OK, used=1, limit=2)


class CollectUsageTests(unittest.TestCase):
    def test_ready_calls_provider(self):
        auth = AuthResult("Claude", AuthState.READY, token="tok")
        snap = collect_usage(auth, _FakeProvider("Claude"))
        self.assertEqual(snap.state, UsageState.OK)

    def test_missing_becomes_auth_error_without_calling_provider(self):
        auth = AuthResult("Claude", AuthState.MISSING)
        snap = collect_usage(auth, _FakeProvider("Claude", raises=True))
        self.assertEqual(snap.state, UsageState.AUTH_ERROR)
        self.assertIn("claude login", snap.message)

    def test_expired_becomes_auth_error(self):
        auth = AuthResult("Codex", AuthState.EXPIRED)
        snap = collect_usage(auth, _FakeProvider("Codex"))
        self.assertEqual(snap.state, UsageState.AUTH_ERROR)
        self.assertIn("codex login", snap.message)


class CollectAllTests(unittest.TestCase):
    def test_preserves_order(self):
        jobs = [
            (lambda: AuthResult("Claude", AuthState.READY, token="t"), _FakeProvider("Claude")),
            (lambda: AuthResult("Codex", AuthState.READY, token="t"), _FakeProvider("Codex")),
        ]
        snaps = collect_all(jobs)
        self.assertEqual([s.provider for s in snaps], ["Claude", "Codex"])

    def test_one_failure_does_not_break_others(self):
        def boom():
            raise OSError("disco")

        jobs = [
            (boom, _FakeProvider("Claude")),
            (lambda: AuthResult("Codex", AuthState.READY, token="t"), _FakeProvider("Codex")),
        ]
        snaps = collect_all(jobs)
        self.assertEqual(snaps[0].state, UsageState.NETWORK_ERROR)
        self.assertEqual(snaps[1].state, UsageState.OK)


if __name__ == "__main__":
    unittest.main()
