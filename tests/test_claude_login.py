"""
Testes do login automatico do Claude (core/claude_login.py).

Nenhum processo real e aberto: o launcher e o detector de CLI sao fakes
nomeados injetados no ClaudeAutoLogin.
"""

import unittest

from core import config
from core.claude_login import (
    ClaudeAutoLogin,
    LoginAttempt,
    TerminalLaunch,
    build_terminal_launch,
    needs_claude_login,
)
from core.models import UsageSnapshot, UsageState


class _FakeLauncher:
    """Registra cada TerminalLaunch em vez de abrir um terminal."""

    def __init__(self, *, raises: bool = False):
        self.launches: list[TerminalLaunch] = []
        self._raises = raises

    def __call__(self, launch: TerminalLaunch) -> None:
        if self._raises:
            raise OSError("terminal indisponivel")
        self.launches.append(launch)


class _FakeCliDetector:
    def __init__(self, available: bool):
        self.available = available

    def __call__(self) -> bool:
        return self.available


def _snap(state: UsageState, provider: str = config.PROVIDER_CLAUDE) -> UsageSnapshot:
    return UsageSnapshot(provider=provider, state=state)


def _auto(launcher: _FakeLauncher, *, cli: bool = True, enabled: bool = True):
    return ClaudeAutoLogin(
        platform="win32",
        enabled=enabled,
        launcher=launcher,
        cli_available=_FakeCliDetector(cli),
        linux_terminal=None,
    )


class NeedsClaudeLoginTests(unittest.TestCase):
    def test_auth_error_on_claude_needs_login(self):
        self.assertTrue(needs_claude_login(_snap(UsageState.AUTH_ERROR)))

    def test_network_error_does_not_need_login(self):
        self.assertFalse(needs_claude_login(_snap(UsageState.NETWORK_ERROR)))

    def test_codex_auth_error_is_ignored(self):
        snap = _snap(UsageState.AUTH_ERROR, provider=config.PROVIDER_CODEX)
        self.assertFalse(needs_claude_login(snap))

    def test_none_is_ignored(self):
        self.assertFalse(needs_claude_login(None))


class BuildTerminalLaunchTests(unittest.TestCase):
    def test_windows_opens_new_console_with_cmd(self):
        launch = build_terminal_launch("win32")
        self.assertEqual(launch.argv, ["cmd", "/k", "claude auth login"])
        self.assertEqual(launch.creationflags, 0x10)

    def test_macos_uses_terminal_app(self):
        launch = build_terminal_launch("darwin")
        self.assertEqual(launch.argv[0], "osascript")
        self.assertIn('do script "claude auth login"', launch.argv[2])

    def test_linux_with_terminal_emulator(self):
        launch = build_terminal_launch("linux", linux_terminal="/usr/bin/xterm")
        self.assertEqual(launch.argv, ["/usr/bin/xterm", "-e", "claude", "auth", "login"])

    def test_linux_without_terminal_runs_cli_directly(self):
        launch = build_terminal_launch("linux", linux_terminal=None)
        self.assertEqual(launch.argv, ["claude", "auth", "login"])


class ClaudeAutoLoginTests(unittest.TestCase):
    def test_first_auth_error_triggers_login(self):
        launcher = _FakeLauncher()
        result = _auto(launcher).on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(result, LoginAttempt.TRIGGERED)
        self.assertEqual(len(launcher.launches), 1)

    def test_repeated_auth_error_opens_only_once_per_outage(self):
        launcher = _FakeLauncher()
        auto = _auto(launcher)
        auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        result = auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(result, LoginAttempt.ALREADY_HANDLED)
        self.assertEqual(len(launcher.launches), 1)

    def test_ok_rearms_for_next_outage(self):
        launcher = _FakeLauncher()
        auto = _auto(launcher)
        auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        auto.on_claude_snapshot(_snap(UsageState.OK))
        result = auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(result, LoginAttempt.TRIGGERED)
        self.assertEqual(len(launcher.launches), 2)

    def test_network_error_does_not_rearm(self):
        # Sem rede nao prova que a sessao voltou; nao deve reabrir o terminal.
        launcher = _FakeLauncher()
        auto = _auto(launcher)
        auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        auto.on_claude_snapshot(_snap(UsageState.NETWORK_ERROR))
        result = auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(result, LoginAttempt.ALREADY_HANDLED)

    def test_disabled_never_launches(self):
        launcher = _FakeLauncher()
        result = _auto(launcher, enabled=False).on_claude_snapshot(
            _snap(UsageState.AUTH_ERROR)
        )
        self.assertIs(result, LoginAttempt.NOT_NEEDED)
        self.assertEqual(launcher.launches, [])

    def test_missing_cli_reports_and_does_not_launch(self):
        launcher = _FakeLauncher()
        result = _auto(launcher, cli=False).on_claude_snapshot(
            _snap(UsageState.AUTH_ERROR)
        )
        self.assertIs(result, LoginAttempt.CLI_MISSING)
        self.assertEqual(launcher.launches, [])

    def test_launch_failure_is_reported_once_per_outage(self):
        # Sem trava, o aviso de falha repetiria a cada refresh de 10 min.
        auto = _auto(_FakeLauncher(raises=True))
        self.assertIs(auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR)), LoginAttempt.FAILED)
        self.assertIs(
            auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR)), LoginAttempt.ALREADY_HANDLED
        )

    def test_missing_cli_is_reported_once_per_outage(self):
        auto = _auto(_FakeLauncher(), cli=False)
        auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(
            auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR)), LoginAttempt.ALREADY_HANDLED
        )

    def test_manual_open_ignores_outage_lock(self):
        launcher = _FakeLauncher()
        auto = _auto(launcher)
        auto.on_claude_snapshot(_snap(UsageState.AUTH_ERROR))
        self.assertIs(auto.open_login(), LoginAttempt.TRIGGERED)
        self.assertEqual(len(launcher.launches), 2)

    def test_manual_open_works_even_when_session_ok(self):
        launcher = _FakeLauncher()
        self.assertIs(_auto(launcher).open_login(), LoginAttempt.TRIGGERED)
        self.assertEqual(len(launcher.launches), 1)


if __name__ == "__main__":
    unittest.main()
