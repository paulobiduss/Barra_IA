"""
refresh_scheduler.py - QTimer periodico + 'atualizar agora' com debounce.

Encapsula a politica de atualizacao para a tray nao lidar com timers
diretamente. Dispara um callback fornecido pelo dono (a tray), que faz a coleta
de uso e atualiza a UI.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, QTimer

from core import config


class RefreshScheduler(QObject):
    def __init__(
        self,
        on_refresh: Callable[[], None],
        *,
        interval_ms: int = config.REFRESH_INTERVAL_MS,
        debounce_ms: int = config.MANUAL_REFRESH_DEBOUNCE_MS,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._on_refresh = on_refresh
        self._debounce_ms = debounce_ms

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._run)

        # Janela de debounce: enquanto ativa, novos pedidos manuais sao ignorados.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)

    def start(self, *, run_immediately: bool = True) -> None:
        self._timer.start()
        if run_immediately:
            self._run()

    def request_manual_refresh(self) -> bool:
        """Dispara um refresh manual, respeitando o debounce.
        Retorna True se executou, False se foi ignorado pelo debounce."""
        if self._debounce.isActive():
            return False
        self._debounce.start(self._debounce_ms)
        self._run()
        return True

    def stop(self) -> None:
        self._timer.stop()

    def _run(self) -> None:
        self._on_refresh()
