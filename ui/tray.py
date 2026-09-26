"""
tray.py - Icone na bandeja: tooltip de uso + menu de contexto.

Objetivo Macro:
    Manter o uso de Claude/Codex visivel na bandeja, atualizando tooltip e
    itens de status, com acoes 'Atualizar agora', 'Entrar no Claude' e 'Sair'.
    Quando a sessao do Claude cai, abre o login oficial automaticamente
    (core/claude_login.py).

Fluxo Logico:
    1. Origem: RefreshScheduler dispara coleta de uso (credentials -> provider).
    2. Transformacao: formatters convertem snapshots em texto.
    3. Destino: tooltip + itens de menu do QSystemTrayIcon.

Mantem cache do ultimo snapshot valido para a UI nao 'piscar' vazia em falhas
temporarias.
"""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidgetAction

from core import config
from core.claude_login import ClaudeAutoLogin, LoginAttempt
from core.credentials import read_claude_credentials, read_codex_credentials
from core.models import UsageSnapshot, UsageState
from core.providers.claude_provider import ClaudeUsageProvider
from core.providers.codex_provider import CodexUsageProvider
from core.refresh_scheduler import RefreshScheduler
from core.usage_worker import UsageFetchTask
from ui.formatters import format_tooltip
from ui.usage_menu_item import UsageMenuItemWidget


class SystemTray(QSystemTrayIcon):
    def __init__(
        self,
        icon: QIcon,
        parent=None,
        auto_login: ClaudeAutoLogin | None = None,
    ):
        super().__init__(icon, parent)

        self._auto_login = auto_login or ClaudeAutoLogin()

        self._claude_provider = ClaudeUsageProvider()
        self._codex_provider = CodexUsageProvider()

        # Jobs de coleta (leitor de credencial adiado + provider), na ordem de
        # exibicao. Tanto a leitura de disco quanto a rede rodam no worker.
        self._jobs = [
            (read_claude_credentials, self._claude_provider),
            (read_codex_credentials, self._codex_provider),
        ]

        # Cache do ultimo snapshot OK por provider (para nao esvaziar a UI).
        self._last_ok: dict[str, UsageSnapshot] = {}

        # Coleta assincrona: evita congelar a bandeja durante o I/O de rede.
        self._pool = QThreadPool.globalInstance()
        self._busy = False
        self._active_task: UsageFetchTask | None = None

        self._build_menu()
        self.setToolTip("Barra de Uso de IA\nCarregando...")

        self._scheduler = RefreshScheduler(self.refresh_now_silent, parent=self)

    # --- ciclo de vida ----------------------------------------------------
    def start(self) -> None:
        self.show()
        self._scheduler.start(run_immediately=True)

    # --- construcao do menu ----------------------------------------------
    def _build_menu(self) -> None:
        menu = QMenu()

        self._widget_claude = UsageMenuItemWidget(config.PROVIDER_CLAUDE, menu)
        self._action_claude = QWidgetAction(menu)
        self._action_claude.setDefaultWidget(self._widget_claude)
        self._action_claude.setEnabled(False)

        self._widget_codex = UsageMenuItemWidget(config.PROVIDER_CODEX, menu)
        self._action_codex = QWidgetAction(menu)
        self._action_codex.setDefaultWidget(self._widget_codex)
        self._action_codex.setEnabled(False)

        self._action_refresh = QAction("Atualizar agora", menu)
        self._action_refresh.triggered.connect(self._on_manual_refresh)

        self._action_login = QAction("Entrar no Claude", menu)
        self._action_login.triggered.connect(self._on_manual_login)

        self._action_quit = QAction("Sair", menu)
        self._action_quit.triggered.connect(QApplication.quit)

        menu.addAction(self._action_claude)
        menu.addAction(self._action_codex)
        menu.addSeparator()
        menu.addAction(self._action_refresh)
        menu.addAction(self._action_login)
        menu.addSeparator()
        menu.addAction(self._action_quit)

        self.setContextMenu(menu)

    # --- acoes ------------------------------------------------------------
    def _on_manual_refresh(self) -> None:
        executed = self._scheduler.request_manual_refresh()
        if not executed:
            self.setToolTip(self.toolTip() + "\n(aguarde para atualizar de novo)")

    def _on_manual_login(self) -> None:
        self._report_login_attempt(self._auto_login.open_login())

    def _handle_claude_session(self, raw_claude: UsageSnapshot | None) -> None:
        """Recebe o snapshot BRUTO (antes do cache, que mascara AUTH_ERROR)."""
        self._report_login_attempt(self._auto_login.on_claude_snapshot(raw_claude))

    def _report_login_attempt(self, attempt: LoginAttempt) -> None:
        if attempt is LoginAttempt.TRIGGERED:
            self.showMessage(
                "Barra de Uso de IA",
                "Sessao do Claude encerrada - abrindo o login no terminal.",
            )
            QTimer.singleShot(config.POST_LOGIN_REFRESH_DELAY_MS, self.refresh_now_silent)
        elif attempt is LoginAttempt.CLI_MISSING:
            self.showMessage(
                "Barra de Uso de IA",
                "CLI 'claude' nao encontrado no PATH - instale o Claude Code para entrar.",
                QSystemTrayIcon.MessageIcon.Warning,
            )
        elif attempt is LoginAttempt.FAILED:
            self.showMessage(
                "Barra de Uso de IA",
                "Nao foi possivel abrir o terminal - rode 'claude auth login'.",
                QSystemTrayIcon.MessageIcon.Warning,
            )

    def refresh_now_silent(self) -> None:
        """Dispara a coleta em background. Retorna imediatamente; a UI e
        atualizada em `_apply_snapshots` quando o worker terminar. Coletas
        sobrepostas sao ignoradas enquanto uma estiver em andamento."""
        if self._busy:
            return
        self._busy = True
        task = UsageFetchTask(self._jobs)
        task.signals.done.connect(self._apply_snapshots)
        # Mantem referencia ao task ate o sinal (queued) ser entregue, para o
        # objeto de sinais nao ser coletado antes da hora.
        self._active_task = task
        self._pool.start(task)

    def _apply_snapshots(self, snapshots: list[UsageSnapshot]) -> None:
        """Roda no thread da UI (sinal queued). Aplica cache e atualiza textos."""
        self._busy = False
        self._active_task = None

        raw_claude = next(
            (s for s in snapshots if s.provider == config.PROVIDER_CLAUDE), None
        )
        self._handle_claude_session(raw_claude)

        by_provider = {s.provider: self._with_cache(s) for s in snapshots}
        ordered = list(by_provider.values())

        self.setToolTip(format_tooltip(ordered))
        claude = by_provider.get(config.PROVIDER_CLAUDE)
        codex = by_provider.get(config.PROVIDER_CODEX)
        if claude is not None:
            self._widget_claude.update_from_snapshot(claude)
        if codex is not None:
            self._widget_codex.update_from_snapshot(codex)

    # --- cache ------------------------------------------------------------
    def _with_cache(self, snapshot: UsageSnapshot) -> UsageSnapshot:
        """Em falha, reaproveita o ultimo snapshot OK (anexando aviso); em
        sucesso, atualiza o cache."""
        if snapshot.state is UsageState.OK:
            self._last_ok[snapshot.provider] = snapshot
            return snapshot

        cached = self._last_ok.get(snapshot.provider)
        if cached is not None:
            note = snapshot.message or snapshot.state.value
            return UsageSnapshot(
                provider=cached.provider,
                state=UsageState.OK,
                used=cached.used,
                limit=cached.limit,
                percent=cached.percent,
                reset_at=cached.reset_at,
                message=f"(cache - {note})",
                fetched_at=cached.fetched_at,
            )
        return snapshot
