"""
usage_menu_item.py - Widget grafico de cada provider no menu da bandeja.

Substitui a QAction de texto (`Claude: 120/500 (24%) ...`) por um QWidget custom
exibido via QWidgetAction. Layout em tres linhas:

    Provider               (bold, herda cor do tema)
    120/500 . 24% . reset em 3h
    [============-----]    (barra pintada com paintEvent)

A barra (UsageBar) e um QWidget separado com `paintEvent` proprio: track
arredondado em cinza escuro e fill arredondado colorido por threshold (verde
< 50%, amarelo 50-80%, laranja 80-95%, vermelho >= 95%). Em estados != OK ou
sem percentual, a barra esconde o fill e o detalhe mostra a mensagem do
snapshot.

Toda a parte de calculo de cor vive em `ui/usage_colors.py` (pura, testavel).
Helpers de formatacao (`fmt_number`, `fmt_reset`) sao reusados de
`ui/formatters.py`.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.models import UsageSnapshot, UsageState
from ui.formatters import fmt_number, fmt_reset
from ui.usage_colors import TRACK, color_for_percent


class UsageBar(QWidget):
    """Barra horizontal pintada (track + fill arredondados).

    `set_percent(None)` esconde o fill mantendo so o track (estado inativo /
    sem dado). O paintEvent clampa o percentual em [0, 100] para nunca pintar
    fora do retangulo.
    """

    _BAR_HEIGHT = 6  # px logico (Qt escala para DPI alto)
    _BAR_WIDTH = 160

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent: float | None = None
        self.setMinimumHeight(self._BAR_HEIGHT)
        self.setMinimumWidth(self._BAR_WIDTH)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(self._BAR_WIDTH, self._BAR_HEIGHT)

    def set_percent(self, pct: float | None) -> None:
        """Atualiza o percentual e dispara um repaint."""
        self._percent = pct
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)

            rect = QRectF(self.rect())
            radius = rect.height() / 2.0

            # Track sempre pintado, mesmo sem percentual.
            painter.setBrush(QColor(TRACK))
            painter.drawRoundedRect(rect, radius, radius)

            if self._percent is None:
                return

            pct = max(0.0, min(100.0, float(self._percent)))
            if pct <= 0:
                return

            fill_width = rect.width() * (pct / 100.0)
            fill_rect = QRectF(rect.x(), rect.y(), fill_width, rect.height())
            painter.setBrush(color_for_percent(pct))
            painter.drawRoundedRect(fill_rect, radius, radius)
        finally:
            painter.end()


class UsageMenuItemWidget(QWidget):
    """Item do menu para um provider: nome + detalhe + UsageBar."""

    def __init__(self, provider: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._provider = provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)

        self._label_provider = QLabel(provider, self)
        font = self._label_provider.font()
        font.setBold(True)
        self._label_provider.setFont(font)

        self._label_detail = QLabel("...", self)
        detail_font = self._label_detail.font()
        # Detalhe menor que o nome do provider, para hierarquia visual.
        detail_font.setPointSizeF(max(detail_font.pointSizeF() - 1.0, 7.0))
        self._label_detail.setFont(detail_font)

        self._bar = UsageBar(self)

        layout.addWidget(self._label_provider)
        layout.addWidget(self._label_detail)
        layout.addWidget(self._bar)

    def update_from_snapshot(self, snapshot: UsageSnapshot) -> None:
        """Atualiza nome (constante), texto de detalhe e barra com base no snapshot."""
        if snapshot.state is not UsageState.OK:
            self._label_detail.setText(snapshot.message or snapshot.state.value)
            self._bar.set_percent(None)
            return

        self._label_detail.setText(_format_detail(snapshot))
        self._bar.set_percent(snapshot.percent)


def _format_detail(snapshot: UsageSnapshot) -> str:
    """Linha de detalhe do widget. Reusa os formatters de texto puros.

    Ex.: '120/500 . 24% . reset em 3h' ou '24% . reset em 3h' (sem used/limit).
    """
    parts: list[str] = []
    if snapshot.used is not None and snapshot.limit is not None:
        parts.append(f"{fmt_number(snapshot.used)}/{fmt_number(snapshot.limit)}")
    elif snapshot.used is not None:
        parts.append(fmt_number(snapshot.used))

    if snapshot.percent is not None:
        parts.append(f"{fmt_number(snapshot.percent)}%")

    if snapshot.reset_at is not None:
        parts.append(fmt_reset(snapshot.reset_at))

    detail = " · ".join(parts) if parts else "uso indisponivel"

    # Snapshots OK com message vem do cache (fallback em falha temporaria).
    if snapshot.message:
        detail = f"{detail} {snapshot.message}"
    return detail
