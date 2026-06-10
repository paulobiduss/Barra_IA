"""
usage_worker.py - Coleta de uso fora do thread da UI (QThreadPool).

Objetivo Macro:
    Evitar que o I/O de rede/disco (ate ~2 endpoints com timeout) congele a
    bandeja. A coleta roda em um worker do QThreadPool e o resultado volta para
    o thread principal via sinal (conexao queued), onde a UI e atualizada.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from core.usage_service import UsageJob, collect_all


class _WorkerSignals(QObject):
    # list[UsageSnapshot]; o sinal e entregue no thread do receptor (UI).
    done = pyqtSignal(list)


class UsageFetchTask(QRunnable):
    def __init__(self, jobs: list[UsageJob]):
        super().__init__()
        self._jobs = jobs
        self.signals = _WorkerSignals()

    def run(self) -> None:
        snapshots = collect_all(self._jobs)
        self.signals.done.emit(snapshots)
