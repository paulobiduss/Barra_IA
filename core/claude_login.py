"""
claude_login.py - Login automatico do Claude quando a sessao cai.

Objetivo Macro:
    Quando o token do Claude some, expira ou e rejeitado (AUTH_ERROR), abrir
    automaticamente o fluxo oficial `claude auth login` em um terminal visivel.
    O proprio CLI abre o navegador para o OAuth e grava as credenciais; este app
    continua sem escrever, renovar ou apagar tokens (ver SECURITY.md).

Fluxo Logico:
    1. Origem: snapshot bruto do Claude (antes do cache da tray).
    2. Transformacao: ClaudeAutoLogin decide se dispara (uma vez por "queda").
    3. Destino: launcher injetado executa o comando do terminal da plataforma.

Por que um terminal visivel: `claude auth login` e interativo (navegador +
eventual confirmacao), entao rodar escondido deixaria o usuario sem saida.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Sequence

from core import config
from core.models import UsageSnapshot, UsageState


class LoginAttempt(str, Enum):
    """Resultado de uma avaliacao do auto-login."""

    NOT_NEEDED = "not_needed"      # sessao ok (ou provider nao e Claude)
    ALREADY_HANDLED = "already_handled"  # esta queda ja foi tratada
    TRIGGERED = "triggered"        # terminal com `claude auth login` aberto
    CLI_MISSING = "cli_missing"    # executavel `claude` nao encontrado no PATH
    FAILED = "failed"              # erro ao abrir o terminal


@dataclass(frozen=True)
class TerminalLaunch:
    """Comando pronto para subprocess.Popen (sem shell=True)."""

    argv: list[str]
    creationflags: int = 0


def needs_claude_login(snapshot: Optional[UsageSnapshot]) -> bool:
    """True quando o snapshot BRUTO do Claude indica sessao invalida.

    Deve receber o snapshot antes do fallback de cache da tray, que mascara o
    AUTH_ERROR como OK. Ex.: needs_claude_login(snaps_by_provider["Claude"]).
    """
    if snapshot is None or snapshot.provider != config.PROVIDER_CLAUDE:
        return False
    return snapshot.state is UsageState.AUTH_ERROR


def build_terminal_launch(
    platform: str,
    login_command: Sequence[str] = config.CLAUDE_LOGIN_COMMAND,
    linux_terminal: Optional[str] = None,
) -> TerminalLaunch:
    """Monta o comando que abre um terminal rodando o login, por plataforma.

    O comando de login e uma constante do app (sem entrada do usuario), entao
    nao ha risco de injecao ao interpola-lo no AppleScript/cmd.
    Ex.: build_terminal_launch("win32").argv -> ["cmd", "/k", "claude auth login"]
    """
    command_line = " ".join(login_command)
    if platform == "win32":
        # CREATE_NEW_CONSOLE: janela propria, mesmo com o app sem console (.exe).
        return TerminalLaunch(["cmd", "/k", command_line], _create_new_console_flag())
    if platform == "darwin":
        script = f'tell application "Terminal" to do script "{command_line}"'
        return TerminalLaunch(
            ["osascript", "-e", script, "-e", 'tell application "Terminal" to activate']
        )
    if linux_terminal:
        return TerminalLaunch([linux_terminal, "-e", *login_command])
    # Sem emulador conhecido: roda direto; o CLI ainda abre o navegador.
    return TerminalLaunch(list(login_command))


def _create_new_console_flag() -> int:
    # Constante so existe no Windows; 0x10 e o valor documentado da Win32 API.
    return getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)


def default_launcher(launch: TerminalLaunch) -> None:
    """Executa o terminal sem esperar (o login e interativo e demorado)."""
    subprocess.Popen(  # noqa: S603 - argv fixo, sem shell
        launch.argv,
        creationflags=launch.creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def default_cli_available() -> bool:
    """Checa se o CLI `claude` esta no PATH.

    No macOS o app (.app) herda um PATH minimo do launchd, mas o Terminal abre
    um shell de login com o PATH do usuario - por isso nao bloqueamos la.
    """
    if sys.platform == "darwin":
        return True
    return shutil.which(config.CLAUDE_LOGIN_COMMAND[0]) is not None


@dataclass
class ClaudeAutoLogin:
    """Dispara `claude auth login` uma unica vez por queda de sessao.

    Uma "queda" comeca no primeiro AUTH_ERROR e termina quando o Claude volta a
    responder OK; so entao o gatilho e rearmado. Isso evita abrir um terminal
    (ou repetir o aviso de CLI ausente/falha) a cada refresh de 10 min enquanto
    o usuario ainda nao concluiu o login.

    Ex.:
        auto = ClaudeAutoLogin()
        auto.on_claude_snapshot(snapshot)  # -> LoginAttempt.TRIGGERED
    """

    platform: str = sys.platform
    enabled: bool = config.CLAUDE_AUTO_LOGIN_ENABLED
    launcher: Callable[[TerminalLaunch], None] = default_launcher
    cli_available: Callable[[], bool] = default_cli_available
    linux_terminal: Optional[str] = field(
        default_factory=lambda: shutil.which("x-terminal-emulator")
    )
    _handled_current_outage: bool = False

    def on_claude_snapshot(self, snapshot: Optional[UsageSnapshot]) -> LoginAttempt:
        """Avalia o snapshot bruto do Claude e dispara o login se preciso."""
        if not needs_claude_login(snapshot):
            if snapshot is not None and snapshot.is_ok:
                self._handled_current_outage = False
            return LoginAttempt.NOT_NEEDED
        if not self.enabled:
            return LoginAttempt.NOT_NEEDED
        if self._handled_current_outage:
            return LoginAttempt.ALREADY_HANDLED
        self._handled_current_outage = True
        return self.open_login()

    def open_login(self) -> LoginAttempt:
        """Abre o login agora; a acao manual do menu chama direto, sem trava."""
        if not self.cli_available():
            return LoginAttempt.CLI_MISSING
        launch = build_terminal_launch(self.platform, linux_terminal=self.linux_terminal)
        try:
            self.launcher(launch)
        except OSError:
            return LoginAttempt.FAILED
        return LoginAttempt.TRIGGERED
