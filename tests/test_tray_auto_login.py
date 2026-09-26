"""
Integracao tray <-> auto-login: o gatilho deve ver o snapshot BRUTO do Claude,
mesmo quando o cache da tray mascara o AUTH_ERROR com o ultimo valor OK.
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QIcon  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from core import config  # noqa: E402
from core.claude_login import ClaudeAutoLogin, TerminalLaunch  # noqa: E402
from core.models import UsageSnapshot, UsageState  # noqa: E402
from ui.tray import SystemTray  # noqa: E402


class _FakeLauncher:
    def __init__(self):
        self.launches: list[TerminalLaunch] = []

    def __call__(self, launch: TerminalLaunch) -> None:
        self.launches.append(launch)


def _claude(state: UsageState, percent: float | None = None) -> UsageSnapshot:
    return UsageSnapshot(provider=config.PROVIDER_CLAUDE, state=state, percent=percent)


class TrayAutoLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.launcher = _FakeLauncher()
        auto = ClaudeAutoLogin(
            platform="linux",
            launcher=self.launcher,
            cli_available=lambda: True,
            linux_terminal=None,
        )
        self.tray = SystemTray(QIcon(), auto_login=auto)

    def test_auth_error_behind_cache_still_triggers_login(self):
        self.tray._apply_snapshots([_claude(UsageState.OK, percent=40)])
        self.tray._apply_snapshots([_claude(UsageState.AUTH_ERROR)])
        self.assertEqual(len(self.launcher.launches), 1)

    def test_ok_session_does_not_trigger_login(self):
        self.tray._apply_snapshots([_claude(UsageState.OK, percent=10)])
        self.assertEqual(self.launcher.launches, [])

    def test_menu_has_manual_login_action(self):
        texts = [a.text() for a in self.tray.contextMenu().actions()]
        self.assertIn("Entrar no Claude", texts)


if __name__ == "__main__":
    unittest.main()
